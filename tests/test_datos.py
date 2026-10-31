"""Consistencia del repo: el golden set apunta a documentos reales y no hay secretos en los archivos."""
import json
import re
from pathlib import Path

import config
import evaluate
import ingest

RAIZ = Path(__file__).resolve().parent.parent


def test_el_golden_set_tiene_al_menos_5_preguntas_con_el_formato_de_la_consigna():
    crudo = json.loads(config.GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    assert len(crudo) >= 5
    assert all({"pregunta", "documento_id_esperado"} <= set(item) for item in crudo)


def test_cada_documento_esperado_existe_en_data():
    existentes = {p.stem for p in config.DATA_DIR.iterdir() if p.suffix in config.EXTENSIONES_VALIDAS}
    esperados = {c.documento_id_esperado for c in evaluate.cargar_golden_set()}
    assert esperados <= existentes, f"documentos inexistentes en el golden set: {esperados - existentes}"


def test_las_preguntas_del_golden_set_no_se_repiten():
    preguntas = [c.pregunta for c in evaluate.cargar_golden_set()]
    assert len(set(preguntas)) == len(preguntas)


def test_el_golden_set_mezcla_preguntas_exactas_y_parafraseadas():
    tipos = {c.tipo for c in evaluate.cargar_golden_set()}
    assert "exacta" in tipos and "parafraseada" in tipos   # para que se vea el aporte de BM25 y del vectorial


def test_todos_los_documentos_de_data_tienen_codigo_y_categoria():
    for doc in ingest.cargar_documentos(config.DATA_DIR):
        assert doc.codigo != config.CODIGO_SIN_DEFINIR, doc.fuente
        assert doc.categoria != config.CATEGORIA_POR_DEFECTO, doc.fuente


def test_los_codigos_de_los_documentos_son_unicos():
    codigos = [d.codigo for d in ingest.cargar_documentos(config.DATA_DIR)]
    assert len(set(codigos)) == len(codigos)


# --------------------------------------------------------------------------- el dataset
def _texto(doc) -> str:
    return "\n".join(p.texto for p in doc.paginas)


def test_el_dataset_es_lo_bastante_grande_para_que_el_top_5_no_sea_trivial():
    # Con 14 fragmentos el top-5 cubria un tercio del corpus y Recall@5 daba 1.0 en cualquier modo.
    documentos = ingest.cargar_documentos(config.DATA_DIR)
    contar, _ = ingest.crear_contador_de_tokens()
    fragmentos = ingest.fragmentar(documentos, contar)
    assert len(documentos) >= 10
    assert len(fragmentos) >= 25


def test_el_dataset_cubre_las_cuatro_categorias():
    categorias = {d.categoria for d in ingest.cargar_documentos(config.DATA_DIR)}
    assert categorias == {"politica", "roles", "procedimiento", "glosario"}


def test_hay_pdf_de_varias_paginas_para_que_la_metadata_pagina_sea_real():
    documentos = [d for d in ingest.cargar_documentos(config.DATA_DIR) if d.extension == ".pdf"]
    assert documentos, "la consigna habla de PDF y de pagina: el dataset debe incluir al menos uno"
    assert all(len(d.paginas) >= 2 for d in documentos)
    contar, _ = ingest.crear_contador_de_tokens()
    paginas = {f.metadata["pagina"] for f in ingest.fragmentar(documentos, contar)}
    assert {1, 2} <= paginas


def test_cada_pdf_de_data_tiene_su_fuente_para_poder_regenerarlo():
    for pdf in config.DATA_DIR.glob("*.pdf"):
        assert (RAIZ / "scripts" / "fuentes_pdf" / f"{pdf.stem}.md").is_file(), pdf.name


# Termino que identifica a UN solo documento. Garantiza que la respuesta esperada de una pregunta "exacta"
# no es ambigua: si el termino apareciera en otro documento, el golden set premiaria o castigaria sin motivo.
TERMINOS_EXACTOS = {
    "¿Qué es Depo360?": "Depo360",
    "¿Para qué se usa el formulario FA-07?": "FA-07",
    "¿Qué función cumple Calidata?": "Calidata",
    "¿Qué establece el procedimiento GD-PRO-006?": "GD-PRO-006",
}


def test_las_preguntas_exactas_tienen_un_termino_que_solo_esta_en_su_documento():
    documentos = {d.documento_id: _texto(d) for d in ingest.cargar_documentos(config.DATA_DIR)}
    exactas = [c for c in evaluate.cargar_golden_set() if c.tipo == "exacta"]
    assert exactas
    for caso in exactas:
        assert caso.pregunta in TERMINOS_EXACTOS, f"agrega el termino clave de: {caso.pregunta}"
        termino = TERMINOS_EXACTOS[caso.pregunta]
        con_el_termino = {doc_id for doc_id, texto in documentos.items() if termino.lower() in texto.lower()}
        assert con_el_termino == {caso.documento_id_esperado}, f"'{termino}' aparece en {sorted(con_el_termino)}"


def test_el_golden_set_cubre_los_tres_tipos_de_pregunta_con_varias_de_cada_una():
    tipos = [c.tipo for c in evaluate.cargar_golden_set()]
    for tipo in ("exacta", "mixta", "parafraseada"):
        assert tipos.count(tipo) >= 3, tipo


# --------------------------------------------------------------------------- seguridad
PATRONES_DE_CLAVES = [
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),        # claves de Google
    re.compile(r"pcsk_[0-9A-Za-z_]{20,}"),         # claves de Pinecone
    re.compile(r"sk-[0-9A-Za-z_\-]{30,}"),         # claves de OpenAI / Anthropic
    re.compile(r"ghp_[0-9A-Za-z]{30,}"),           # tokens de GitHub
]


EXTENSIONES_A_REVISAR = {".py", ".md", ".json", ".txt", ".ini", ".example", ".sh", ""}   # "" = .gitignore y similares
CARPETAS_A_IGNORAR = {".git", "__pycache__", ".pytest_cache", "site-packages", "node_modules"}


def _archivos_de_texto(raiz: Path = RAIZ):
    """Archivos de texto del repo. Salta los entornos virtuales con CUALQUIER nombre (los reconoce por su pyvenv.cfg)."""
    entornos = {cfg.parent for cfg in raiz.rglob("pyvenv.cfg")}
    for ruta in raiz.rglob("*"):
        if not ruta.is_file() or ruta.name == ".env" or ruta.suffix not in EXTENSIONES_A_REVISAR:
            continue
        if set(ruta.relative_to(raiz).parts) & CARPETAS_A_IGNORAR or entornos & set(ruta.parents):
            continue
        yield ruta


def _archivos_con_claves(raiz: Path = RAIZ) -> list[str]:
    encontrados = []
    for ruta in _archivos_de_texto(raiz):
        try:
            texto = ruta.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(patron.search(texto) for patron in PATRONES_DE_CLAVES):
            encontrados.append(str(ruta.relative_to(raiz)))
    return encontrados


def test_ningun_archivo_del_repo_contiene_claves_de_api():
    assert _archivos_con_claves() == []


def test_el_escaneo_de_claves_detecta_una_clave_en_un_archivo_comun(tmp_path):
    # Cuida al propio escaneo: que no pase "en verde" porque dejo de mirar.
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "filtrada.py").write_text('KEY = "AIza' + "a" * 35 + '"\n', encoding="utf-8")
    assert _archivos_con_claves(tmp_path) == ["filtrada.py"]


def test_el_escaneo_de_claves_ignora_entornos_virtuales_con_cualquier_nombre(tmp_path):
    entorno = tmp_path / "mi_entorno_raro"
    (entorno / "lib").mkdir(parents=True)
    (entorno / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    (entorno / "lib" / "terceros.py").write_text('TEST = "AIza' + "b" * 35 + '"\n', encoding="utf-8")
    assert _archivos_con_claves(tmp_path) == []


def test_env_example_lista_las_variables_sin_valores_secretos():
    lineas = (RAIZ / ".env.example").read_text(encoding="utf-8").splitlines()
    asignaciones = dict(l.split("=", 1) for l in lineas if "=" in l and not l.startswith("#"))
    assert {"PINECONE_API_KEY", "INDEX_NAME", "GOOGLE_API_KEY"} <= set(asignaciones)
    assert asignaciones["PINECONE_API_KEY"] == "" and asignaciones["GOOGLE_API_KEY"] == ""


def test_el_env_real_esta_en_gitignore():
    ignorados = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignorados


def test_el_codigo_no_trae_claves_escritas_a_mano():
    # Las claves solo se leen de variables de entorno, en config.py.
    for ruta in RAIZ.glob("*.py"):
        if ruta.name == "config.py":
            continue
        assert "os.environ" not in ruta.read_text(encoding="utf-8"), f"{ruta.name} lee variables de entorno por su cuenta"
