"""Configuracion segura: variables de entorno validadas, sin filtrar claves."""
import pytest

import config
from errores import ConfiguracionError

ENV_OK = {
    "PINECONE_API_KEY": "pcsk_clave-secreta-de-prueba",
    "INDEX_NAME": "mi-indice",
    "GOOGLE_API_KEY": "AIza-clave-secreta-de-prueba",
}


def test_lee_las_variables_y_usa_el_namespace_por_defecto():
    cfg = config.cargar_configuracion(env=ENV_OK)
    assert cfg.index_name == "mi-indice"
    assert cfg.namespace == config.NAMESPACE_POR_DEFECTO
    assert cfg.pinecone_api_key == ENV_OK["PINECONE_API_KEY"]


def test_el_namespace_se_puede_elegir():
    cfg = config.cargar_configuracion(env={**ENV_OK, "PINECONE_NAMESPACE": "produccion"})
    assert cfg.namespace == "produccion"


def test_informa_todas_las_variables_que_faltan_de_una_vez():
    with pytest.raises(ConfiguracionError) as error:
        config.cargar_configuracion(env={})
    mensaje = str(error.value)
    for nombre in ("PINECONE_API_KEY", "INDEX_NAME", "GOOGLE_API_KEY"):
        assert nombre in mensaje
    assert ".env.example" in mensaje


def test_un_valor_en_blanco_cuenta_como_faltante():
    with pytest.raises(ConfiguracionError, match="PINECONE_API_KEY"):
        config.cargar_configuracion(env={**ENV_OK, "PINECONE_API_KEY": "   "})


def test_setup_no_necesita_la_clave_de_embeddings():
    sin_google = {k: v for k, v in ENV_OK.items() if k != "GOOGLE_API_KEY"}
    cfg = config.cargar_configuracion(requiere_embeddings=False, env=sin_google)
    assert cfg.google_api_key is None
    with pytest.raises(ConfiguracionError, match="GOOGLE_API_KEY"):
        config.cargar_configuracion(env=sin_google)


@pytest.mark.parametrize("nombre", ["Mi_Indice", "-empieza", "termina-", "con espacio", "a" * 46, "ñandu"])
def test_rechaza_nombres_de_indice_que_pinecone_no_acepta(nombre):
    with pytest.raises(ConfiguracionError, match="INDEX_NAME"):
        config.cargar_configuracion(env={**ENV_OK, "INDEX_NAME": nombre})


@pytest.mark.parametrize("nombre", ["a", "rag-gobierno-de-datos", "x" * 45, "indice-01"])
def test_acepta_nombres_validos(nombre):
    assert config.cargar_configuracion(env={**ENV_OK, "INDEX_NAME": nombre}).index_name == nombre


def test_las_claves_no_aparecen_en_el_repr_ni_en_los_errores():
    cfg = config.cargar_configuracion(env=ENV_OK)
    texto = repr(cfg) + str(cfg)
    assert ENV_OK["PINECONE_API_KEY"] not in texto
    assert ENV_OK["GOOGLE_API_KEY"] not in texto
    with pytest.raises(ConfiguracionError) as error:
        config.cargar_configuracion(env={**ENV_OK, "INDEX_NAME": "MAL NOMBRE"})
    assert ENV_OK["PINECONE_API_KEY"] not in str(error.value)


def test_los_valores_de_diseno_son_los_de_la_consigna():
    assert config.EMBEDDING_DIMENSION == 1536
    assert config.METRICA == "cosine"
    assert config.TOP_K == 5
    assert 500 <= config.CHUNK_SIZE_TOKENS <= 800          # "punto medio (~500-800 tokens)"
    assert 100 <= config.UPSERT_BATCH_SIZE <= 200          # "batches de entre 100 y 200 vectores"
    assert (config.PINECONE_CLOUD, config.PINECONE_REGION) == ("aws", "us-east-1")  # unica region del plan gratis
