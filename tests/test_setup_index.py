"""Setup del indice serverless: crea si falta, no toca si existe, falla claro si no es compatible."""
import pytest

import setup_index
from errores import DimensionNoCoincideError, IndiceError
from tests.fakes import ErrorHTTP, FakePinecone

ENV = {"PINECONE_API_KEY": "pcsk_falsa", "INDEX_NAME": "mi-indice"}


def test_crea_el_indice_serverless_con_la_dimension_y_la_metrica_del_proyecto():
    pc = FakePinecone()
    estado = setup_index.asegurar_indice(pc, "mi-indice", dormir=lambda s: None)

    assert estado.creado is True
    (creado,) = pc.creados
    assert creado["name"] == "mi-indice"
    assert creado["dimension"] == 1536
    assert creado["metric"] == "cosine"
    assert creado["spec"].cloud == "aws"
    assert creado["spec"].region == "us-east-1"


def test_espera_a_que_el_indice_este_listo():
    pc = FakePinecone(listo_tras=3)
    esperas: list[float] = []
    setup_index.asegurar_indice(pc, "mi-indice", dormir=esperas.append)
    assert len(esperas) == 3


def test_es_idempotente_si_el_indice_ya_existe_no_lo_vuelve_a_crear():
    pc = FakePinecone()
    pc.agregar_indice("mi-indice")
    estado = setup_index.asegurar_indice(pc, "mi-indice", dormir=lambda s: None)
    assert estado.creado is False
    assert pc.creados == []


def test_correrlo_dos_veces_crea_una_sola_vez():
    pc = FakePinecone()
    primero = setup_index.asegurar_indice(pc, "mi-indice", dormir=lambda s: None)
    segundo = setup_index.asegurar_indice(pc, "mi-indice", dormir=lambda s: None)
    assert (primero.creado, segundo.creado) == (True, False)
    assert len(pc.creados) == 1


def test_un_indice_existente_con_otra_dimension_falla_y_no_se_modifica():
    pc = FakePinecone()
    pc.agregar_indice("mi-indice", dimension=768)
    with pytest.raises(DimensionNoCoincideError, match="768"):
        setup_index.asegurar_indice(pc, "mi-indice", dormir=lambda s: None)
    assert pc.creados == []


def test_si_el_indice_nunca_queda_listo_falla_con_un_mensaje_claro():
    pc = FakePinecone(listo_tras=10**6)
    reloj = iter(range(0, 10_000, 100))
    with pytest.raises(IndiceError, match="no quedo listo"):
        setup_index.asegurar_indice(
            pc, "mi-indice", max_espera_s=250, dormir=lambda s: None, reloj=lambda: next(reloj)
        )


# --------------------------------------------------------------------------- CLI
def _entorno(monkeypatch, env):
    for nombre in ("PINECONE_API_KEY", "INDEX_NAME", "GOOGLE_API_KEY", "PINECONE_NAMESPACE"):
        monkeypatch.delenv(nombre, raising=False)
    for nombre, valor in env.items():
        monkeypatch.setenv(nombre, valor)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)   # que un .env real no contamine el test


def test_main_crea_el_indice_y_lo_informa(monkeypatch, capsys):
    _entorno(monkeypatch, ENV)
    pc = FakePinecone()
    monkeypatch.setattr(setup_index, "crear_cliente", lambda cfg: pc)
    monkeypatch.setattr(setup_index.time, "sleep", lambda s: None)

    assert setup_index.main([]) == 0
    salida = capsys.readouterr().out
    assert "creado y listo" in salida and "1536" in salida and "cosine" in salida


def test_main_sin_variables_de_entorno_explica_que_falta(monkeypatch, capsys):
    _entorno(monkeypatch, {})
    assert setup_index.main([]) == 1
    assert "PINECONE_API_KEY" in capsys.readouterr().err


def test_main_traduce_el_error_de_clave_invalida(monkeypatch, capsys):
    _entorno(monkeypatch, ENV)

    class PineconeConClaveMala:
        def has_index(self, nombre):
            raise ErrorHTTP(401)

    monkeypatch.setattr(setup_index, "crear_cliente", lambda cfg: PineconeConClaveMala())
    assert setup_index.main([]) == 1
    assert "PINECONE_API_KEY" in capsys.readouterr().err


def test_main_no_pide_la_clave_de_google(monkeypatch):
    _entorno(monkeypatch, ENV)   # sin GOOGLE_API_KEY
    monkeypatch.setattr(setup_index, "crear_cliente", lambda cfg: FakePinecone())
    monkeypatch.setattr(setup_index.time, "sleep", lambda s: None)
    assert setup_index.main([]) == 0
