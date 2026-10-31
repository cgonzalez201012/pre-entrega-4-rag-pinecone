"""Acceso a Pinecone: indice, listado paginado, corpus para BM25, espera de visibilidad y errores."""
from types import SimpleNamespace

import pytest

import almacen
import config
from errores import DimensionNoCoincideError, IndiceError
from tests.fakes import ErrorHTTP, FakeIndex, FakePinecone, documento


def _cargar(index: FakeIndex, namespace: str, cantidad: int) -> None:
    index.upsert(
        [
            {
                "id": f"doc#{i:02d}",
                "values": [1.0, 0.0],
                "metadata": {"text": f"texto {i}", "documento_id": "doc", "chunk_index": i, "categoria": "politica"},
            }
            for i in range(cantidad)
        ],
        namespace=namespace,
    )


# --------------------------------------------------------------------------- leer_campo
def test_leer_campo_acepta_dicts_y_objetos():
    assert almacen.leer_campo({"a": 1}, "a") == 1
    assert almacen.leer_campo(SimpleNamespace(a=2), "a") == 2
    assert almacen.leer_campo(None, "a", "defecto") == "defecto"
    assert almacen.leer_campo({}, "a", 7) == 7
    assert almacen.leer_campo(SimpleNamespace(), "a", 9) == 9


# --------------------------------------------------------------------------- compatibilidad del indice
def test_un_indice_compatible_pasa():
    pc = FakePinecone()
    pc.agregar_indice("idx", dimension=1536, metric="cosine")
    almacen.verificar_indice_compatible(pc.describe_index("idx"), "idx")


def test_dimension_distinta_da_un_error_que_muestra_las_dos_dimensiones():
    pc = FakePinecone()
    pc.agregar_indice("idx", dimension=768)
    with pytest.raises(DimensionNoCoincideError) as error:
        almacen.verificar_indice_compatible(pc.describe_index("idx"), "idx")
    mensaje = str(error.value)
    assert "768" in mensaje and "1536" in mensaje and "setup_index.py" in mensaje


def test_un_indice_sin_dimension_no_es_compatible():
    pc = FakePinecone()
    pc.agregar_indice("idx", dimension=None)   # por ejemplo un indice sparse
    with pytest.raises(DimensionNoCoincideError):
        almacen.verificar_indice_compatible(pc.describe_index("idx"), "idx")


def test_metrica_distinta_a_coseno_se_rechaza():
    pc = FakePinecone()
    pc.agregar_indice("idx", metric="euclidean")
    with pytest.raises(IndiceError, match="euclidean"):
        almacen.verificar_indice_compatible(pc.describe_index("idx"), "idx")


def test_abrir_indice_inexistente_indica_como_crearlo():
    with pytest.raises(IndiceError, match="python setup_index.py"):
        almacen.abrir_indice(FakePinecone(), "no-existe")


def test_abrir_indice_devuelve_el_indice_y_verifica_la_dimension():
    pc = FakePinecone()
    esperado = pc.agregar_indice("idx")
    assert almacen.abrir_indice(pc, "idx") is esperado
    pc.agregar_indice("viejo", dimension=768)
    with pytest.raises(DimensionNoCoincideError):
        almacen.abrir_indice(pc, "viejo")


# --------------------------------------------------------------------------- IDs y corpus
def test_listar_ids_junta_todas_las_paginas():
    index = FakeIndex(tamano_pagina=2)
    _cargar(index, "ns", 5)
    assert almacen.listar_ids(index, "ns") == [f"doc#{i:02d}" for i in range(5)]


def test_listar_ids_de_un_namespace_que_no_existe_devuelve_vacio():
    assert almacen.listar_ids(FakeIndex(), "no-existe") == []


def test_listar_ids_de_un_namespace_inexistente_tolera_el_404_del_servicio():
    class IndexQue404(FakeIndex):
        def list(self, namespace=None, **_):
            raise ErrorHTTP(404)
            yield  # pragma: no cover

    assert almacen.listar_ids(IndexQue404(), "ns") == []


def test_otros_errores_de_listado_se_propagan():
    class IndexQue500(FakeIndex):
        def list(self, namespace=None, **_):
            raise ErrorHTTP(500)
            yield  # pragma: no cover

    with pytest.raises(ErrorHTTP):
        almacen.listar_ids(IndexQue500(), "ns")


def test_cargar_corpus_reconstruye_los_documentos_con_el_texto_de_la_metadata(monkeypatch):
    monkeypatch.setattr(config, "FETCH_BATCH_SIZE", 2)
    index = FakeIndex(tamano_pagina=2)
    _cargar(index, "ns", 5)
    corpus = almacen.cargar_corpus(index, "ns")

    assert [d.page_content for d in corpus] == [f"texto {i}" for i in range(5)]
    assert all(config.TEXT_KEY not in d.metadata for d in corpus)       # el texto sale de la metadata
    assert corpus[0].metadata["categoria"] == "politica"
    assert index.llamadas_fetch == [2, 2, 1]                            # fetch por lotes, no uno por uno


def test_cargar_corpus_de_un_namespace_vacio_devuelve_lista_vacia():
    assert almacen.cargar_corpus(FakeIndex(), "ns") == []


def test_cargar_corpus_ignora_vectores_sin_texto():
    index = FakeIndex()
    index.upsert([{"id": "a#1", "values": [1.0], "metadata": {"documento_id": "a"}}], namespace="ns")
    assert almacen.cargar_corpus(index, "ns") == []


# --------------------------------------------------------------------------- visibilidad
def test_contar_vectores_lee_las_estadisticas_del_namespace():
    index = FakeIndex()
    _cargar(index, "ns", 4)
    assert almacen.contar_vectores(index, "ns") == 4
    assert almacen.contar_vectores(index, "otro") == 0


def test_esperar_visibilidad_espera_a_que_pinecone_refleje_los_cambios():
    index = FakeIndex(retraso_visibilidad=3)
    _cargar(index, "ns", 4)
    esperas: list[float] = []
    assert almacen.esperar_visibilidad(index, "ns", 4, dormir=esperas.append) is True
    assert len(esperas) == 3


def test_esperar_visibilidad_se_rinde_al_agotar_el_tiempo():
    index = FakeIndex(retraso_visibilidad=10**6)
    _cargar(index, "ns", 4)
    reloj = iter(range(0, 1000, 10))   # cada lectura del reloj avanza 10 s
    visible = almacen.esperar_visibilidad(
        index, "ns", 4, max_espera_s=25, dormir=lambda s: None, reloj=lambda: next(reloj)
    )
    assert visible is False


# --------------------------------------------------------------------------- borrar y traducir errores
def test_borrar_un_namespace_que_no_existe_no_es_un_error():
    almacen.borrar_namespace(FakeIndex(), "no-existe")


def test_borrar_namespace_borra_todo_lo_que_tenia():
    index = FakeIndex()
    _cargar(index, "ns", 3)
    almacen.borrar_namespace(index, "ns")
    assert index.cantidad("ns") == 0


def test_borrar_namespace_propaga_los_errores_que_no_son_404():
    class IndexQue500(FakeIndex):
        def delete(self, **_):
            raise ErrorHTTP(500)

    with pytest.raises(ErrorHTTP):
        almacen.borrar_namespace(IndexQue500(), "ns")


@pytest.mark.parametrize(
    ("estado", "fragmento"),
    [(401, "PINECONE_API_KEY"), (403, "us-east-1"), (404, "setup_index.py"), (429, "Espera")],
)
def test_traduce_los_errores_http_de_pinecone(estado, fragmento):
    assert fragmento in almacen.explicar_error_pinecone(ErrorHTTP(estado))


def test_no_traduce_errores_que_no_son_de_pinecone():
    assert almacen.explicar_error_pinecone(ValueError("x")) is None
    assert almacen.explicar_error_pinecone(ErrorHTTP(500)) is None


def test_documento_de_ayuda_tiene_el_esquema_completo():
    # Cuida a la propia ayuda de tests: si cambia el esquema, estos campos tienen que seguir iguales.
    assert set(documento("x").metadata) == {
        "chunk_id", "documento_id", "fuente", "pagina", "categoria", "codigo", "seccion", "chunk_index", "tokens"
    }
