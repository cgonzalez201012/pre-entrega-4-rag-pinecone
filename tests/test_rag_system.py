"""Recuperador hibrido: fusion BM25 + vectorial, filtros por metadatos, y la integracion real con LangChain."""
import pytest
from langchain_classic.retrievers import EnsembleRetriever
from langchain_pinecone import PineconeVectorStore

import config
import ingest
import rag_system
from errores import FiltroSinResultadosError, NamespaceVacioError
from rag_system import BM25SoloCoincidencias, RAGSystem, ResultadoBusqueda, normalizar_para_bm25
from tests.fakes import EmbeddingsSimulados, FakePinecone, VectorStoreFijo, contar_palabras, documento

# Un corpus chico: el codigo exacto solo aparece en un fragmento; la "parafrasis" no comparte palabras con el texto.
LEXICO = documento("El procedimiento GD-PRO-003 regula el alta de articulos nuevos", doc="proc", categoria="procedimiento", n=0)
SEMANTICO = documento("Cuando una caja no puede cobrar se escala al responsable en pocas horas", doc="pol", categoria="politica", n=1)
RUIDO = [documento(f"texto de relleno numero {i} sin relacion", doc=f"otro{i}", categoria="glosario", n=10 + i) for i in range(8)]
CORPUS = [LEXICO, SEMANTICO, *RUIDO]


def _ids(resultados):
    return [r.chunk_id for r in resultados]


# --------------------------------------------------------------------------- tokenizador
def test_el_tokenizador_normaliza_tildes_y_mayusculas_y_conserva_los_codigos():
    assert normalizar_para_bm25("¿Qué dice GD-PRO-003, Artículos?") == ["dice", "gd-pro-003", "articulos"]
    assert normalizar_para_bm25("") == []


def test_el_tokenizador_descarta_las_palabras_vacias_pero_conserva_las_de_contenido_y_los_numeros():
    assert normalizar_para_bm25("¿Qué es Depo360?") == ["depo360"]
    assert normalizar_para_bm25("el plazo de 10 días hábiles para la baja") == ["plazo", "10", "dias", "habiles", "baja"]
    assert normalizar_para_bm25("¿Cuál es el de la que?") == []      # solo palabras vacias


def test_una_consulta_de_solo_palabras_vacias_no_trae_ningun_fragmento_de_bm25():
    # Antes del filtro, "que es" traia fragmentos al azar solo porque contenian esas palabras.
    corpus = [documento("lo que es un dato maestro", doc="a", n=0), *[documento(f"otro texto {i}", doc=f"b{i}", n=i + 1) for i in range(6)]]
    bm25 = BM25SoloCoincidencias.from_documents(corpus, k=5, preprocess_func=normalizar_para_bm25)
    assert bm25.invoke("¿Qué es?") == []


def test_bm25_descarta_los_fragmentos_sin_ninguna_palabra_en_comun():
    bm25 = BM25SoloCoincidencias.from_documents(CORPUS, k=5, preprocess_func=normalizar_para_bm25)
    assert [d.metadata["chunk_id"] for d in bm25.invoke("GD-PRO-003")] == ["proc#0"]
    assert bm25.invoke("zzz qqq") == []


def test_bm25_con_el_tokenizador_por_defecto_no_encontraria_el_codigo_con_puntuacion():
    # Por eso el proyecto trae su propio tokenizador: 'GD-PRO-003.' != 'GD-PRO-003' si solo se parte por espacios.
    from langchain_community.retrievers import BM25Retriever

    ingenuo = BM25Retriever.from_documents([documento("ver GD-PRO-003.")], k=1)
    assert ingenuo.preprocess_func("GD-PRO-003")[0] != ingenuo.preprocess_func("ver GD-PRO-003.")[1]


# --------------------------------------------------------------------------- construccion
def test_el_sistema_encapsula_un_ensemble_retriever_con_los_pesos_y_la_clave_de_fusion():
    rag = RAGSystem(VectorStoreFijo([SEMANTICO]), CORPUS)
    assert isinstance(rag.ensemble, EnsembleRetriever)
    assert rag.ensemble.weights == [0.5, 0.5]
    assert rag.ensemble.id_key == config.CAMPO_ID_FUSION
    assert rag.k == 5


def test_un_corpus_vacio_da_un_error_que_indica_como_indexar():
    with pytest.raises(NamespaceVacioError, match="python ingest.py"):
        RAGSystem(VectorStoreFijo([]), [])


@pytest.mark.parametrize(
    "opciones", [{"k": 0}, {"pesos": (1.0,)}, {"pesos": (-1.0, 1.0)}, {"pesos": (0.0, 0.0)}, {"candidatos": 3}]
)
def test_rechaza_parametros_invalidos(opciones):
    with pytest.raises(ValueError):
        RAGSystem(VectorStoreFijo([]), CORPUS, **opciones)


def test_cada_recuperador_aporta_los_candidatos_pedidos_y_el_sistema_recorta_a_k():
    almacen = VectorStoreFijo([RUIDO[i] for i in range(8)])
    rag = RAGSystem(almacen, CORPUS, candidatos=8)
    assert rag.candidatos == 8 and rag.k == 5
    assert almacen.pedidos[0]["k"] == 8                               # Pinecone devuelve 8, no 5
    assert len(rag.ensemble.invoke("texto relleno")) > 5              # la fusion junta mas de 5...
    assert len(rag.buscar("texto relleno")) == 5                      # ...y el sistema entrega solo los top-5


def test_bm25_tambien_aporta_tantos_candidatos_como_se_piden():
    coincidencias = [documento(f"consulta unica {i}", doc=f"d{i}", n=i) for i in range(10)]
    relleno = [documento(f"relleno distinto {i}", doc=f"r{i}", n=50 + i) for i in range(14)]
    solo_bm25 = VectorStoreFijo([])                                   # el vectorial no aporta nada
    assert len(RAGSystem(solo_bm25, coincidencias + relleno, candidatos=8).ensemble.invoke("consulta unica")) == 8
    por_defecto = RAGSystem(solo_bm25, coincidencias + relleno)
    assert len(por_defecto.ensemble.invoke("consulta unica")) == config.CANDIDATOS_POR_RECUPERADOR == 10


def test_por_defecto_los_candidatos_salen_de_la_configuracion():
    almacen = VectorStoreFijo([])
    rag = RAGSystem(almacen, CORPUS)
    assert rag.candidatos == config.CANDIDATOS_POR_RECUPERADOR >= config.TOP_K
    assert almacen.pedidos[0]["k"] == rag.candidatos


def test_con_mas_candidatos_la_fusion_ve_un_fragmento_que_el_vectorial_dejaba_fuera_del_top_5():
    # El vectorial pone LEXICO en el puesto 7 y BM25 lo pone primero. Con 5 candidatos solo BM25 lo trae y, como el
    # peso vectorial es mayor, queda fuera del top-5. Con 10 aparece en las DOS listas, suma ambos aportes y sube al
    # primer puesto.
    vectorial = [RUIDO[i] for i in range(6)] + [LEXICO]
    pocos = RAGSystem(VectorStoreFijo(vectorial), CORPUS, candidatos=5, pesos=(0.4, 0.6))
    muchos = RAGSystem(VectorStoreFijo(vectorial), CORPUS, candidatos=10, pesos=(0.4, 0.6))
    assert "proc#0" not in _ids(pocos.buscar("GD-PRO-003"))
    assert _ids(muchos.buscar("GD-PRO-003"))[0] == "proc#0"


# --------------------------------------------------------------------------- fusion hibrida
def test_el_hibrido_encuentra_lo_que_solo_ve_bm25_aunque_el_vectorial_lo_pase_por_alto():
    vectorial_ciego = [RUIDO[0], RUIDO[1], RUIDO[2]]                  # la busqueda semantica no ve el codigo
    rag = RAGSystem(VectorStoreFijo(vectorial_ciego), CORPUS)
    assert "proc#0" not in _ids(rag.buscar("GD-PRO-003", modo="vectorial"))
    assert "proc#0" in _ids(rag.buscar("GD-PRO-003", modo="hibrido"))


def test_el_hibrido_encuentra_lo_que_solo_ve_el_vectorial_cuando_la_pregunta_esta_parafraseada():
    rag = RAGSystem(VectorStoreFijo([SEMANTICO, RUIDO[0]]), CORPUS)
    consulta = "inconveniente grave durante la facturacion"    # no comparte ninguna palabra con el corpus
    assert rag.buscar(consulta, modo="bm25") == []                 # lo lexico no ve nada...
    assert _ids(rag.buscar(consulta, modo="hibrido"))[0] == "pol#1"


def test_un_fragmento_que_ven_los_dos_rankings_queda_primero():
    # BM25 pone LEXICO primero; el vectorial lo pone segundo. Al aparecer en AMBAS listas suma mas que cualquier otro.
    rag = RAGSystem(VectorStoreFijo([SEMANTICO, LEXICO, RUIDO[0]]), CORPUS)
    assert _ids(rag.buscar("GD-PRO-003", modo="hibrido"))[0] == "proc#0"


def test_sin_coincidencia_lexica_bm25_no_mete_ruido_y_manda_el_ranking_vectorial():
    vectorial = [SEMANTICO, RUIDO[0], RUIDO[1]]
    rag = RAGSystem(VectorStoreFijo(vectorial), CORPUS)
    assert _ids(rag.buscar("zzz qqq", modo="hibrido")) == _ids(rag.buscar("zzz qqq", modo="vectorial"))


def test_devuelve_como_maximo_k_fragmentos_aunque_la_fusion_junte_mas():
    corpus = [documento(f"consulta unica {i}", doc=f"d{i}", n=i) for i in range(6)]
    otros = [documento(f"texto distinto {i}", doc=f"v{i}", n=100 + i) for i in range(6)]
    rag = RAGSystem(VectorStoreFijo(otros), corpus + otros + RUIDO, k=5)   # el relleno evita que BM25 puntue 0 (idf)
    assert len(rag.ensemble.invoke("consulta unica")) > 5          # el EnsembleRetriever junta las dos listas...
    assert len(rag.buscar("consulta unica")) == 5                  # ...y el sistema entrega solo los top-5


def test_las_posiciones_van_de_1_a_k():
    rag = RAGSystem(VectorStoreFijo([SEMANTICO, LEXICO, RUIDO[0]]), CORPUS)
    resultados = rag.buscar("GD-PRO-003")
    assert [r.posicion for r in resultados] == list(range(1, len(resultados) + 1))


def test_cada_modo_devuelve_su_propio_ranking():
    rag = RAGSystem(VectorStoreFijo([SEMANTICO, RUIDO[0]]), CORPUS)
    assert _ids(rag.buscar("GD-PRO-003", modo="bm25")) == ["proc#0"]
    assert _ids(rag.buscar("GD-PRO-003", modo="vectorial")) == ["pol#1", "otro0#10"]


def test_el_resultado_lleva_la_fuente_la_pagina_la_seccion_y_el_texto():
    (resultado,) = RAGSystem(VectorStoreFijo([]), CORPUS).buscar("GD-PRO-003", modo="bm25")
    assert isinstance(resultado, ResultadoBusqueda)
    assert (resultado.documento_id, resultado.fuente, resultado.pagina) == ("proc", "proc.md", 1)
    assert (resultado.seccion, resultado.categoria, resultado.codigo) == ("1. Objetivo", "procedimiento", "GD-POL-001")
    assert "alta de articulos" in resultado.texto


def test_consulta_vacia_o_modo_desconocido_se_rechazan():
    rag = RAGSystem(VectorStoreFijo([]), CORPUS)
    with pytest.raises(ValueError, match="vacia"):
        rag.buscar("   ")
    with pytest.raises(ValueError, match="modo"):
        rag.buscar("algo", modo="magico")


# --------------------------------------------------------------------------- filtro por metadatos
def test_el_filtro_por_categoria_se_aplica_a_los_dos_buscadores():
    almacen_vectorial = VectorStoreFijo([SEMANTICO, LEXICO])
    rag = RAGSystem(almacen_vectorial, CORPUS)
    rag.buscar("articulos", categoria="procedimiento")

    # Pinecone recibe el filtro (descarta antes de comparar vectores)...
    candidatos = config.CANDIDATOS_POR_RECUPERADOR
    assert {"k": candidatos, "filter": {"categoria": {"$eq": "procedimiento"}}} in almacen_vectorial.pedidos
    # ...y BM25 solo ve los fragmentos de esa categoria.
    solo_proc = rag._recuperadores("procedimiento").bm25
    assert {d.metadata["categoria"] for d in solo_proc.docs} == {"procedimiento"}


def test_el_buscador_sin_filtro_no_manda_ningun_filtro():
    almacen_vectorial = VectorStoreFijo([])
    RAGSystem(almacen_vectorial, CORPUS)
    assert almacen_vectorial.pedidos == [{"k": config.CANDIDATOS_POR_RECUPERADOR}]


def test_una_categoria_inexistente_lista_las_disponibles():
    with pytest.raises(FiltroSinResultadosError) as error:
        RAGSystem(VectorStoreFijo([]), CORPUS).buscar("algo", categoria="inventada")
    assert "politica" in str(error.value) and "glosario" in str(error.value)


def test_los_recuperadores_por_categoria_se_arman_una_sola_vez():
    almacen_vectorial = VectorStoreFijo([])
    rag = RAGSystem(almacen_vectorial, CORPUS)
    rag.buscar("algo", categoria="politica")
    rag.buscar("otra cosa", categoria="politica")
    assert len(almacen_vectorial.pedidos) == 2    # el general (en __init__) + el de 'politica'


# --------------------------------------------------------------------------- integracion real: LangChain + SDK simulado
@pytest.fixture
def sistema_real(tmp_path):
    """Indexa el dataset REAL del repo en un Pinecone en memoria y arma el RAGSystem con PineconeVectorStore de verdad."""
    nube = FakePinecone()
    index = nube.agregar_indice("idx")
    embeddings = EmbeddingsSimulados()
    cfg = config.Configuracion(pinecone_api_key="x", index_name="idx", namespace="ns", google_api_key="y")
    ingest.ingestar(cfg, pc=nube, embeddings=embeddings, contador=contar_palabras, dormir=lambda s: None)
    rag = RAGSystem.desde_indice(index, embeddings, "ns")
    return rag, index


def test_integracion_con_pinecone_vector_store_y_el_corpus_leido_de_la_metadata(sistema_real):
    rag, index = sistema_real
    assert isinstance(rag._vectorstore, PineconeVectorStore)
    assert len(rag._documentos) == index.cantidad("ns")      # BM25 se armo con TODO el namespace
    assert all(config.TEXT_KEY not in d.metadata for d in rag._documentos)


def test_integracion_busca_por_codigo_exacto_y_por_pregunta(sistema_real):
    rag, _ = sistema_real
    por_codigo = rag.buscar("GD-PRO-003", modo="bm25")
    assert por_codigo and all("GD-PRO-003" in r.texto for r in por_codigo)     # BM25 trae exactamente lo que nombra el codigo
    hibrido = rag.buscar("GD-PRO-003")
    assert len(hibrido) == 5
    assert "03-procedimiento-maestro-de-articulos" in [r.documento_id for r in hibrido]
    por_pregunta = rag.buscar("¿Cuántos años se conservan los datos transaccionales de ventas?", modo="vectorial")
    assert "04-glosario-catalogo-y-clasificacion" in [r.documento_id for r in por_pregunta[:3]]


def test_integracion_el_filtro_llega_a_pinecone_y_solo_trae_esa_categoria(sistema_real):
    rag, index = sistema_real
    resultados = rag.buscar("calidad de datos", categoria="roles", modo="vectorial")
    assert resultados and {r.categoria for r in resultados} == {"roles"}
    assert index.llamadas_query[-1]["filter"] == {"categoria": {"$eq": "roles"}}
    assert index.llamadas_query[-1]["namespace"] == "ns"


def test_integracion_un_namespace_vacio_indica_como_indexar(sistema_real):
    _, index = sistema_real
    with pytest.raises(NamespaceVacioError, match="ingest.py"):
        RAGSystem.desde_indice(index, EmbeddingsSimulados(), "namespace-vacio")


def test_desde_configuracion_abre_el_indice_y_arma_el_sistema(sistema_real, monkeypatch):
    _, index = sistema_real
    nube = FakePinecone()
    nube._indices["idx"] = {"dimension": 1536, "metric": "cosine", "index": index, "consultas": 10**6}
    cfg = config.Configuracion(pinecone_api_key="x", index_name="idx", namespace="ns", google_api_key="y")
    monkeypatch.setattr(rag_system, "crear_cliente", lambda c: nube)
    monkeypatch.setattr(rag_system, "crear_embeddings", lambda c: EmbeddingsSimulados())

    rag = RAGSystem.desde_configuracion(cfg, k=3)
    assert rag.k == 3 and len(rag.buscar("GD-POL-001")) == 3
    assert "03-procedimiento-maestro-de-articulos" in rag.documentos_indexados
    assert set(rag.categorias) == {"politica", "roles", "procedimiento", "glosario"}
