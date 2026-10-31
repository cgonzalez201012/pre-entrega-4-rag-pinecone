"""Ingesta de documentos a Pinecone: /data -> limpieza -> chunking por TOKENS -> embeddings -> upsert por lotes.

Uso:
    python ingest.py                 # sincroniza /data con el namespace (si ya esta al dia, no hace nada)
    python ingest.py --reset         # vacia el namespace y lo reconstruye desde cero
    python ingest.py --dry-run       # solo muestra los fragmentos y sus metadatos (no usa claves ni red)

Decisiones de diseno (para defenderlas):
* Cada fragmento se guarda con su TEXTO ORIGINAL dentro de la metadata (campo "text"): asi la
  recuperacion lexica (BM25) se reconstruye desde Pinecone sin una segunda base de datos.
* Esquema de metadatos estricto y IGUAL para todos los fragmentos (evita el "schema drift"):
  chunk_id, documento_id, fuente, pagina, categoria, codigo, seccion, chunk_index, tokens, text.
* El ID de cada vector es "<documento_id>#<hash del contenido>". Es determinista: reindexar el mismo
  contenido produce los mismos IDs, asi que NO se vuelve a llamar a la API de embeddings. Si un
  archivo cambia, solo cambian sus fragmentos. El namespace es un espejo exacto de /data.
* Los embeddings se piden de a 20 textos (con reintentos ante cuota agotada) y los upserts van de a
  100 vectores: ingesta por lotes, no vector por vector.
* Se verifica la dimension de los vectores ANTES de subirlos (error comun #1 de la consigna).
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import math
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

import config
from almacen import (
    abrir_indice,
    borrar_namespace,
    crear_cliente,
    esperar_visibilidad,
    explicar_error_pinecone,
    listar_ids,
)
from embeddings import crear_embeddings, embeber_en_lotes
from errores import DimensionNoCoincideError, IngestaError, RagError

logger = logging.getLogger("rag.ingesta")

ContadorDeTokens = Callable[[str], int]

_ENCABEZADO_MD = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_CODIGO_DOCUMENTO = re.compile(r"\b(GD-([A-Z]{3})-\d{3})\b")

# Esquema de metadatos: campo -> tipo. Pinecone acepta str, int, float, bool y listas de str.
ESQUEMA_METADATA: dict[str, type] = {
    "chunk_id": str,
    "documento_id": str,
    "fuente": str,
    "pagina": int,
    "categoria": str,
    "codigo": str,
    "seccion": str,
    "chunk_index": int,
    "tokens": int,
}
LIMITE_METADATA_BYTES = 40_000  # limite de Pinecone por vector (se deja un margen)


# --------------------------------------------------------------------------- modelos
@dataclass(frozen=True)
class Pagina:
    numero: int
    texto: str


@dataclass(frozen=True)
class Documento:
    documento_id: str   # nombre del archivo sin extension: es el "documento_id_esperado" del golden set
    fuente: str         # nombre del archivo
    extension: str
    paginas: tuple[Pagina, ...]
    codigo: str
    categoria: str


@dataclass(frozen=True)
class ReporteIngesta:
    archivos: int
    fragmentos: int
    nuevos: int
    sin_cambios: int
    eliminados: int
    lotes_upsert: int
    tokens_min: int
    tokens_max: int
    tokens_promedio: float
    por_categoria: dict[str, int] = field(default_factory=dict)
    medicion_tokens: str = ""
    indice: str = ""
    namespace: str = ""
    visible: bool = True  # False si Pinecone tardo en reflejar los cambios (consistencia eventual)

    @property
    def base_al_dia(self) -> bool:
        return self.nuevos == 0 and self.eliminados == 0


# --------------------------------------------------------------------------- tokens
def contar_tokens_aproximado(texto: str) -> int:
    """Estimacion gruesa (caracteres / CARACTERES_POR_TOKEN_APROX). Solo es el plan B."""
    return math.ceil(len(texto) / config.CARACTERES_POR_TOKEN_APROX)


def crear_contador_de_tokens() -> tuple[ContadorDeTokens, str]:
    """Devuelve (funcion que cuenta tokens, descripcion de como se mide).

    Usa tiktoken. tiktoken baja su vocabulario de internet la primera vez; si no hay red,
    se usa una aproximacion y se avisa en el log.
    """
    try:
        import tiktoken

        encoding = tiktoken.get_encoding(config.TOKEN_ENCODING)
    except Exception as exc:  # noqa: BLE001 - ImportError o errores de red al bajar el vocabulario
        logger.warning(
            "tiktoken no pudo cargar '%s' (%s). Se usa una aproximacion de %s caracteres por token.",
            config.TOKEN_ENCODING, type(exc).__name__, config.CARACTERES_POR_TOKEN_APROX,
        )
        return contar_tokens_aproximado, f"aproximado ({config.CARACTERES_POR_TOKEN_APROX} caracteres por token)"

    def contar(texto: str) -> int:
        return len(encoding.encode(texto, disallowed_special=()))

    return contar, f"tiktoken/{config.TOKEN_ENCODING}"


# --------------------------------------------------------------------------- carga
def limpiar_texto(texto: str) -> str:
    """Preprocesamiento minimo: saltos de linea uniformes, sin espacios al final, sin bloques en blanco."""
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = "\n".join(linea.rstrip() for linea in texto.split("\n"))
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def derivar_codigo_y_categoria(texto: str) -> tuple[str, str]:
    """Busca el codigo del documento (GD-POL-001) y deduce la categoria de su tipo (POL -> politica)."""
    coincidencia = _CODIGO_DOCUMENTO.search(texto)
    if not coincidencia:
        return config.CODIGO_SIN_DEFINIR, config.CATEGORIA_POR_DEFECTO
    return coincidencia.group(1), config.CATEGORIAS_POR_TIPO.get(coincidencia.group(2), config.CATEGORIA_POR_DEFECTO)


def _leer_paginas(ruta: Path) -> list[Pagina]:
    """Markdown y texto plano no tienen paginas: se tratan como una sola pagina (1). En PDF, la pagina real."""
    if ruta.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader

            lector = PdfReader(str(ruta))
            textos = [(pagina.extract_text() or "") for pagina in lector.pages]
        except Exception as exc:  # noqa: BLE001 - PDF corrupto, protegido con clave, etc.
            raise IngestaError(f"No se pudo leer el PDF {ruta.name}: {type(exc).__name__}: {exc}") from exc
        paginas = [Pagina(i, limpiar_texto(t)) for i, t in enumerate(textos, start=1)]
        paginas = [p for p in paginas if p.texto]
        if not paginas:
            raise IngestaError(f"{ruta.name} no tiene texto extraible (puede ser un PDF escaneado).")
        return paginas

    try:
        crudo = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise IngestaError(f"{ruta.name} no esta codificado en UTF-8: guardalo como UTF-8.") from exc
    texto = limpiar_texto(crudo)
    return [Pagina(1, texto)] if texto else []


def cargar_documentos(data_dir: Path | str = config.DATA_DIR) -> list[Documento]:
    """Lee los .md / .txt / .pdf de la carpeta (orden alfabetico) y devuelve un Documento por archivo."""
    carpeta = Path(data_dir)
    if not carpeta.is_dir():
        raise IngestaError(f"No existe la carpeta de documentos: {carpeta}")

    archivos = sorted(
        p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in config.EXTENSIONES_VALIDAS
    )
    if not archivos:
        raise IngestaError(
            f"No hay archivos {', '.join(config.EXTENSIONES_VALIDAS)} en {carpeta}. Agrega al menos uno para poder indexar."
        )

    documentos: list[Documento] = []
    for ruta in archivos:
        paginas = _leer_paginas(ruta)
        if not paginas:
            logger.warning("%s esta vacio: se omite.", ruta.name)
            continue
        codigo, categoria = derivar_codigo_y_categoria("\n".join(p.texto for p in paginas))
        documentos.append(
            Documento(
                documento_id=ruta.stem,
                fuente=ruta.name,
                extension=ruta.suffix.lower(),
                paginas=tuple(paginas),
                codigo=codigo,
                categoria=categoria,
            )
        )
    if not documentos:
        raise IngestaError(f"Todos los archivos de {carpeta} estan vacios.")
    return documentos


# --------------------------------------------------------------------------- chunking
def crear_splitter(
    contador: ContadorDeTokens,
    chunk_size: int = config.CHUNK_SIZE_TOKENS,
    chunk_overlap: int = config.CHUNK_OVERLAP_TOKENS,
    extension: str = ".md",
) -> RecursiveCharacterTextSplitter:
    """RecursiveCharacterTextSplitter que MIDE en tokens (length_function).

    Para .md usa los separadores de Markdown (titulos, parrafos, lineas) en ese orden de
    prioridad, asi un fragmento intenta no cortar una seccion a la mitad.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap debe ser menor que chunk_size")
    opciones = dict(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=contador,
        add_start_index=True,
    )
    if extension.lower() == ".md":
        return RecursiveCharacterTextSplitter.from_language(Language.MARKDOWN, **opciones)
    return RecursiveCharacterTextSplitter(**opciones)


def id_de_fragmento(documento_id: str, pagina: int, texto: str) -> str:
    """ID determinista: '<documento_id>#<hash>'. Mismo contenido => mismo ID. El prefijo permite listar por documento."""
    huella = hashlib.sha256(f"{documento_id}\n{pagina}\n{texto}".encode("utf-8")).hexdigest()[:16]
    return f"{documento_id}#{huella}"


MAX_TITULOS_EN_LA_CITA = 3
SEPARADOR_DE_TITULOS = " / "


def _seccion_del_fragmento(texto: str, inicio: int, fin: int) -> str:
    """Titulos de Markdown que cubre el fragmento [inicio, fin), para poder citarlo con precision.

    Un fragmento de ~600 tokens suele cruzar secciones. Se listan todos los titulos que toca, en
    orden ("3. Medicion y reporte / 4. Clasificacion y resolucion de incidentes"), hasta 3.
    El titulo del documento (nivel 1) se omite si el fragmento tiene subtitulos propios.
    """
    previo, nivel_previo, dentro = "", 0, []
    for m in _ENCABEZADO_MD.finditer(texto):
        if m.start() >= fin:
            break
        nivel = len(m.group(1))
        if m.start() <= inicio:
            previo, nivel_previo = m.group(2), nivel
        elif nivel > 1:
            dentro.append(m.group(2))
    titulos = ([previo] if previo and not (nivel_previo == 1 and dentro) else []) + dentro
    if len(titulos) > MAX_TITULOS_EN_LA_CITA:
        titulos = titulos[:MAX_TITULOS_EN_LA_CITA] + ["..."]
    return SEPARADOR_DE_TITULOS.join(titulos)


def validar_metadata(metadata: dict[str, Any]) -> None:
    """Exige que TODOS los fragmentos tengan exactamente el mismo esquema (evita el schema drift)."""
    if set(metadata) != set(ESQUEMA_METADATA):
        sobran = sorted(set(metadata) - set(ESQUEMA_METADATA))
        faltan = sorted(set(ESQUEMA_METADATA) - set(metadata))
        raise IngestaError(f"Metadata fuera del esquema. Faltan: {faltan}. Sobran: {sobran}.")
    for campo, tipo in ESQUEMA_METADATA.items():
        valor = metadata[campo]
        if not isinstance(valor, tipo) or isinstance(valor, bool):
            raise IngestaError(f"Metadata '{campo}' debe ser {tipo.__name__}, no {type(valor).__name__}.")


def fragmentar(
    documentos: list[Documento],
    contador: ContadorDeTokens,
    chunk_size: int = config.CHUNK_SIZE_TOKENS,
    chunk_overlap: int = config.CHUNK_OVERLAP_TOKENS,
) -> list[Document]:
    """Parte cada pagina de cada documento en fragmentos y les agrega los metadatos del esquema."""
    fragmentos: list[Document] = []
    vistos: set[str] = set()
    for doc in documentos:
        splitter = crear_splitter(contador, chunk_size, chunk_overlap, doc.extension)
        indice = 0
        for pagina in doc.paginas:
            for pieza in splitter.split_documents([Document(page_content=pagina.texto)]):
                texto = pieza.page_content
                chunk_id = id_de_fragmento(doc.documento_id, pagina.numero, texto)
                if chunk_id in vistos:  # fragmento identico dentro de la misma pagina
                    continue
                vistos.add(chunk_id)
                inicio = pieza.metadata["start_index"]
                seccion = (
                    _seccion_del_fragmento(pagina.texto, inicio, inicio + len(texto)) if doc.extension == ".md" else ""
                )
                metadata = {
                    "chunk_id": chunk_id,
                    "documento_id": doc.documento_id,
                    "fuente": doc.fuente,
                    "pagina": pagina.numero,
                    "categoria": doc.categoria,
                    "codigo": doc.codigo,
                    "seccion": seccion,
                    "chunk_index": indice,
                    "tokens": contador(texto),
                }
                validar_metadata(metadata)
                fragmentos.append(Document(page_content=texto, metadata=metadata))
                indice += 1
    return fragmentos


# --------------------------------------------------------------------------- Pinecone
def verificar_dimension(vectores: list[list[float]], esperada: int = config.EMBEDDING_DIMENSION) -> None:
    for vector in vectores:
        if len(vector) != esperada:
            raise DimensionNoCoincideError(
                f"El modelo de embeddings devolvio vectores de {len(vector)} dimensiones y el indice espera "
                f"{esperada}. Revisa EMBEDDING_DIMENSION en config.py (no se subio nada a Pinecone)."
            )


def _registro(fragmento: Document, vector: list[float]) -> dict[str, Any]:
    """Formato de un vector para index.upsert: id + valores + metadata (con el texto original)."""
    metadata = {**fragmento.metadata, config.TEXT_KEY: fragmento.page_content}
    if len(str(metadata).encode("utf-8")) > LIMITE_METADATA_BYTES:
        raise IngestaError(
            f"El fragmento {fragmento.metadata['chunk_id']} supera el limite de metadata de Pinecone. "
            "Reduci CHUNK_SIZE_TOKENS en config.py."
        )
    return {"id": fragmento.metadata["chunk_id"], "values": vector, "metadata": metadata}


def sincronizar(
    index: Any,
    embeddings: Embeddings,
    fragmentos: list[Document],
    namespace: str,
    *,
    reset: bool = False,
    tamano_lote_upsert: int = config.UPSERT_BATCH_SIZE,
    tamano_lote_embeddings: int = config.EMBED_BATCH_SIZE,
    dormir: Callable[[float], None] = time.sleep,
) -> tuple[int, int, int]:
    """Deja el namespace igual a `fragmentos`. Devuelve (nuevos, eliminados, lotes de upsert)."""
    if reset:
        borrar_namespace(index, namespace)

    existentes = set(listar_ids(index, namespace))
    vigentes = {f.metadata["chunk_id"] for f in fragmentos}
    nuevos = [f for f in fragmentos if f.metadata["chunk_id"] not in existentes]
    obsoletos = sorted(existentes - vigentes)

    lotes = 0
    for inicio in range(0, len(nuevos), tamano_lote_upsert):
        lote = nuevos[inicio : inicio + tamano_lote_upsert]
        vectores = embeber_en_lotes(
            embeddings, [f.page_content for f in lote], tamano_lote=tamano_lote_embeddings, dormir=dormir
        )
        verificar_dimension(vectores)
        index.upsert(vectors=[_registro(f, v) for f, v in zip(lote, vectores)], namespace=namespace)
        lotes += 1
        logger.info("Upsert del lote %s: %s vectores", lotes, len(lote))

    # Se borra DESPUES de subir lo nuevo: si algo falla a mitad de camino, no se pierde lo que ya estaba.
    for inicio in range(0, len(obsoletos), config.DELETE_BATCH_SIZE):
        index.delete(ids=obsoletos[inicio : inicio + config.DELETE_BATCH_SIZE], namespace=namespace)

    return len(nuevos), len(obsoletos), lotes


def ingestar(
    cfg: config.Configuracion,
    *,
    data_dir: Path | str = config.DATA_DIR,
    reset: bool = False,
    embeddings: Embeddings | None = None,
    pc: Any | None = None,
    contador: ContadorDeTokens | None = None,
    dormir: Callable[[float], None] = time.sleep,
    max_espera_visibilidad_s: float = 60.0,
) -> ReporteIngesta:
    """Sincroniza la carpeta de documentos con el namespace de Pinecone y devuelve un reporte."""
    if contador is None:
        contador, medicion = crear_contador_de_tokens()
    else:
        medicion = "contador inyectado"

    documentos = cargar_documentos(data_dir)
    fragmentos = fragmentar(documentos, contador)
    if not fragmentos:
        raise IngestaError("Los documentos no produjeron ningun fragmento.")

    pc = pc or crear_cliente(cfg)
    index = abrir_indice(pc, cfg.index_name)  # verifica que exista y que la dimension coincida
    embeddings = embeddings or crear_embeddings(cfg)

    nuevos, eliminados, lotes = sincronizar(
        index, embeddings, fragmentos, cfg.namespace, reset=reset, dormir=dormir
    )

    visible = True
    if nuevos or eliminados or reset:
        visible = esperar_visibilidad(
            index, cfg.namespace, len(fragmentos), max_espera_s=max_espera_visibilidad_s, dormir=dormir
        )

    tokens = [f.metadata["tokens"] for f in fragmentos]
    por_categoria: dict[str, int] = {}
    for f in fragmentos:
        por_categoria[f.metadata["categoria"]] = por_categoria.get(f.metadata["categoria"], 0) + 1
    return ReporteIngesta(
        archivos=len(documentos),
        fragmentos=len(fragmentos),
        nuevos=nuevos,
        sin_cambios=len(fragmentos) - nuevos,
        eliminados=eliminados,
        lotes_upsert=lotes,
        tokens_min=min(tokens),
        tokens_max=max(tokens),
        tokens_promedio=round(sum(tokens) / len(tokens), 1),
        por_categoria=por_categoria,
        medicion_tokens=medicion,
        indice=cfg.index_name,
        namespace=cfg.namespace,
        visible=visible,
    )


# --------------------------------------------------------------------------- CLI
def _imprimir_dry_run(documentos: list[Documento], fragmentos: list[Document], medicion: str) -> None:
    tokens = [f.metadata["tokens"] for f in fragmentos]
    print("\nDRY RUN: no se uso ninguna clave ni se subio nada a Pinecone.")
    print(f"  Archivos .............. {len(documentos)}")
    print(f"  Fragmentos ............ {len(fragmentos)}")
    print(f"  Tokens por fragmento .. min {min(tokens)} / prom {round(sum(tokens) / len(tokens), 1)} / max {max(tokens)}")
    print(f"  Medicion de tokens .... {medicion}")
    for doc in documentos:
        cantidad = sum(1 for f in fragmentos if f.metadata["documento_id"] == doc.documento_id)
        print(f"    - {doc.fuente}: {cantidad} fragmentos, categoria '{doc.categoria}', codigo {doc.codigo}")
    ejemplo = {**fragmentos[0].metadata, config.TEXT_KEY: fragmentos[0].page_content[:80] + "..."}
    print("  Metadata del primer fragmento (lo que se guarda junto al vector):")
    for clave, valor in ejemplo.items():
        print(f"      {clave}: {valor!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Indexa los documentos de /data en Pinecone.")
    parser.add_argument("--data", default=str(config.DATA_DIR), help="carpeta con los .md/.txt/.pdf")
    parser.add_argument("--reset", action="store_true", help="vacia el namespace y lo reconstruye desde cero")
    parser.add_argument("--dry-run", action="store_true", help="muestra los fragmentos sin usar claves ni red")
    args = parser.parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)   # sin una linea por cada llamada HTTP a Gemini/Pinecone

    try:
        if args.dry_run:
            contador, medicion = crear_contador_de_tokens()
            documentos = cargar_documentos(args.data)
            _imprimir_dry_run(documentos, fragmentar(documentos, contador), medicion)
            return 0

        cfg = config.cargar_configuracion()
        reporte = ingestar(cfg, data_dir=args.data, reset=args.reset)
    except RagError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        mensaje = explicar_error_pinecone(exc)
        if mensaje is None:
            raise
        print(f"ERROR: {mensaje}", file=sys.stderr)
        return 1

    estado = "el namespace ya estaba al dia (no se escribio nada)" if reporte.base_al_dia else "namespace actualizado"
    print(f"\nIngesta completa: {estado}")
    print(f"  Archivos leidos ....... {reporte.archivos}")
    print(f"  Fragmentos vigentes ... {reporte.fragmentos}")
    print(f"  Nuevos (embebidos) .... {reporte.nuevos}  en {reporte.lotes_upsert} lote(s) de upsert")
    print(f"  Sin cambios ........... {reporte.sin_cambios}")
    print(f"  Eliminados ............ {reporte.eliminados}")
    print(f"  Por categoria ......... {reporte.por_categoria}")
    print(f"  Tokens por fragmento .. min {reporte.tokens_min} / prom {reporte.tokens_promedio} / max {reporte.tokens_max}")
    print(f"  Medicion de tokens .... {reporte.medicion_tokens}")
    print(f"  Destino ............... indice '{reporte.indice}', namespace '{reporte.namespace}'")
    if not reporte.visible:
        print("  AVISO: Pinecone todavia no refleja todos los vectores (consistencia eventual). Espera unos segundos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
