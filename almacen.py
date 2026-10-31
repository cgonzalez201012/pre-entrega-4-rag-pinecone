"""Acceso a Pinecone: cliente, indice, listado de IDs, corpus y espera de visibilidad.

Pinecone Serverless es "eventualmente consistente": un upsert tarda unos segundos en verse en
las lecturas. Por eso hay una espera explicita (`esperar_visibilidad`) antes de dar la ingesta
por terminada.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from langchain_core.documents import Document

import config
from errores import DimensionNoCoincideError, IndiceError

logger = logging.getLogger("rag.almacen")


def leer_campo(objeto: Any, nombre: str, defecto: Any = None) -> Any:
    """Lee un campo de un dict o de un objeto (las respuestas del SDK aceptan ambas formas)."""
    if objeto is None:
        return defecto
    if isinstance(objeto, dict):
        return objeto.get(nombre, defecto)
    try:
        return getattr(objeto, nombre)
    except AttributeError:
        pass
    try:
        return objeto[nombre]
    except (KeyError, TypeError, AttributeError):
        return defecto


def es_no_encontrado(exc: BaseException) -> bool:
    return getattr(exc, "status", None) == 404


def explicar_error_pinecone(exc: BaseException) -> str | None:
    """Traduce los errores HTTP mas comunes de Pinecone a un mensaje accionable. None si no es de Pinecone."""
    estado = getattr(exc, "status", None)
    if estado == 401:
        return "Pinecone rechazo la clave. Revisa PINECONE_API_KEY en el .env (sin comillas ni espacios)."
    if estado == 403:
        return (
            "Pinecone nego la operacion (403). Con el plan gratis el limite es de 5 indices y 2 GB, y solo se "
            "pueden crear indices en AWS us-east-1. Borra un indice que no uses desde la consola de Pinecone."
        )
    if estado == 404:
        return "Pinecone no encontro el recurso (404). Verifica INDEX_NAME y que hayas corrido python setup_index.py."
    if estado == 429:
        return "Pinecone limito el uso (429). Espera un minuto y volve a correr el script."
    return None


def crear_cliente(cfg: config.Configuracion) -> Any:
    from pinecone import Pinecone

    return Pinecone(api_key=cfg.pinecone_api_key)


# --------------------------------------------------------------------------- indice
def verificar_indice_compatible(
    descripcion: Any,
    nombre: str,
    dimension: int = config.EMBEDDING_DIMENSION,
    metrica: str = config.METRICA,
) -> None:
    """Falla con un mensaje claro si el indice existente no sirve para estos embeddings."""
    dim_indice = leer_campo(descripcion, "dimension")
    if dim_indice != dimension:
        raise DimensionNoCoincideError(
            f"El indice '{nombre}' tiene dimension {dim_indice} y los embeddings ({config.EMBEDDING_MODEL}) "
            f"producen vectores de {dimension}. Pinecone no acepta vectores de otro tamano. "
            "Usa otro INDEX_NAME, o borra ese indice desde la consola de Pinecone y volve a correr "
            "python setup_index.py."
        )
    valor = leer_campo(descripcion, "metric", "")
    metrica_indice = str(getattr(valor, "value", valor)).lower()
    if metrica not in metrica_indice:
        raise IndiceError(
            f"El indice '{nombre}' usa la metrica '{metrica_indice}' y el proyecto usa '{metrica}'. "
            "Los embeddings de este modelo estan pensados para similitud coseno: usa otro INDEX_NAME "
            "o recrea el indice."
        )


def abrir_indice(pc: Any, nombre: str) -> Any:
    """Devuelve el indice, verificando antes que exista y sea compatible. NO lo crea (eso es setup_index.py)."""
    if not pc.has_index(nombre):
        raise IndiceError(
            f"El indice '{nombre}' no existe en Pinecone. Crealo con: python setup_index.py"
        )
    verificar_indice_compatible(pc.describe_index(nombre), nombre)
    return pc.Index(nombre)


# --------------------------------------------------------------------------- lecturas
def listar_ids(index: Any, namespace: str) -> list[str]:
    """Todos los IDs de un namespace (el SDK los entrega paginados)."""
    ids: list[str] = []
    try:
        for pagina in index.list(namespace=namespace):
            ids.extend(pagina)
    except Exception as exc:  # noqa: BLE001
        if es_no_encontrado(exc):
            return []  # el namespace todavia no existe: no hay nada indexado
        raise
    return ids


def cargar_corpus(index: Any, namespace: str) -> list[Document]:
    """Reconstruye los Document de un namespace leyendo el texto guardado en la metadata.

    Esta es la razon de guardar el texto original dentro de la metadata (paso 2 de la consigna):
    BM25 necesita el texto y asi se obtiene de Pinecone, sin una segunda base de datos.
    """
    ids = listar_ids(index, namespace)
    documentos: list[Document] = []
    for inicio in range(0, len(ids), config.FETCH_BATCH_SIZE):
        respuesta = index.fetch(ids=ids[inicio : inicio + config.FETCH_BATCH_SIZE], namespace=namespace)
        for vector in (leer_campo(respuesta, "vectors", {}) or {}).values():
            metadata = dict(leer_campo(vector, "metadata", {}) or {})
            texto = metadata.pop(config.TEXT_KEY, None)
            if texto:
                documentos.append(Document(page_content=texto, metadata=metadata))
    documentos.sort(key=lambda d: (str(d.metadata.get("documento_id", "")), d.metadata.get("chunk_index", 0)))
    return documentos


def contar_vectores(index: Any, namespace: str) -> int:
    estadisticas = index.describe_index_stats()
    resumen = (leer_campo(estadisticas, "namespaces", {}) or {}).get(namespace)
    return int(leer_campo(resumen, "vector_count", 0) or 0)


def esperar_visibilidad(
    index: Any,
    namespace: str,
    esperados: int,
    *,
    max_espera_s: float = 60.0,
    intervalo_s: float = 2.0,
    dormir: Callable[[float], None] = time.sleep,
    reloj: Callable[[], float] = time.monotonic,
) -> bool:
    """Espera a que el namespace muestre exactamente `esperados` vectores. False si se agota el tiempo."""
    limite = reloj() + max_espera_s
    while True:
        if contar_vectores(index, namespace) == esperados:
            return True
        if reloj() >= limite:
            return False
        dormir(intervalo_s)


def borrar_namespace(index: Any, namespace: str) -> None:
    try:
        index.delete(delete_all=True, namespace=namespace)
    except Exception as exc:  # noqa: BLE001
        if not es_no_encontrado(exc):  # un namespace inexistente no hay que borrarlo
            raise
