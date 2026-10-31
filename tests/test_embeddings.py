"""Embeddings: lotes, reintentos ante cuota agotada y dimension fijada."""
import pytest

import config
import embeddings
from errores import ConfiguracionError, EmbeddingsError
from tests.fakes import EmbeddingsConFallas, EmbeddingsQueSeRompe, EmbeddingsSimulados


@pytest.mark.parametrize(
    "mensaje", ["429 Too Many Requests", "RESOURCE_EXHAUSTED", "You exceeded your current quota", "rate limit reached"]
)
def test_reconoce_los_errores_de_cuota(mensaje):
    assert embeddings.es_error_de_cuota(RuntimeError(mensaje))


@pytest.mark.parametrize("mensaje", ["401 API key not valid", "connection refused", "timeout"])
def test_no_confunde_otros_errores_con_cuota(mensaje):
    assert not embeddings.es_error_de_cuota(RuntimeError(mensaje))


def test_parte_los_textos_en_lotes():
    modelo = EmbeddingsSimulados(dimension=8)
    vectores = embeddings.embeber_en_lotes(modelo, [f"texto {i}" for i in range(45)], tamano_lote=20)
    assert len(vectores) == 45
    assert modelo.lotes == [20, 20, 5]


def test_sin_textos_no_llama_a_la_api():
    modelo = EmbeddingsSimulados(dimension=8)
    assert embeddings.embeber_en_lotes(modelo, []) == []
    assert modelo.lotes == []


def test_reintenta_con_espera_creciente_cuando_se_agota_la_cuota():
    modelo = EmbeddingsConFallas(fallas=2, dimension=8)
    esperas: list[float] = []
    vectores = embeddings.embeber_en_lotes(modelo, ["a", "b"], espera_inicial_s=10, dormir=esperas.append)
    assert len(vectores) == 2
    assert esperas == [10, 20]   # se duplica en cada reintento
    assert modelo.intentos == 3


def test_si_la_cuota_no_se_recupera_falla_con_un_mensaje_claro():
    modelo = EmbeddingsConFallas(fallas=99, dimension=8)
    esperas: list[float] = []
    with pytest.raises(EmbeddingsError, match="cuota"):
        embeddings.embeber_en_lotes(modelo, ["a"], intentos=3, dormir=esperas.append)
    assert modelo.intentos == 3
    assert len(esperas) == 2     # no duerme despues del ultimo intento


def test_un_error_que_no_es_de_cuota_no_se_reintenta():
    modelo = EmbeddingsQueSeRompe(despues_de=0, dimension=8)
    esperas: list[float] = []
    with pytest.raises(ValueError, match="clave invalida"):
        embeddings.embeber_en_lotes(modelo, ["a"], dormir=esperas.append)
    assert esperas == []


def test_el_tamano_de_lote_debe_ser_positivo():
    with pytest.raises(ValueError):
        embeddings.embeber_en_lotes(EmbeddingsSimulados(dimension=8), ["a"], tamano_lote=0)


def test_crear_embeddings_exige_la_clave_de_google():
    cfg = config.Configuracion(pinecone_api_key="x", index_name="i", namespace="n", google_api_key=None)
    with pytest.raises(ConfiguracionError, match="GOOGLE_API_KEY"):
        embeddings.crear_embeddings(cfg)


def test_crear_embeddings_fija_modelo_y_dimension_sin_usar_la_red():
    cfg = config.Configuracion(pinecone_api_key="x", index_name="i", namespace="n", google_api_key="clave-falsa")
    modelo = embeddings.crear_embeddings(cfg)
    assert modelo.model.endswith(config.EMBEDDING_MODEL)
    assert modelo.output_dimensionality == config.EMBEDDING_DIMENSION == 1536
