"""consultar.py: la terminal muestra los 5 fragmentos con su fuente."""
import pytest

import consultar
from errores import FiltroSinResultadosError
from rag_system import RAGSystem
from tests.fakes import VectorStoreFijo, documento

CORPUS = [
    documento("El procedimiento GD-PRO-003 regula el alta de articulos", doc="proc", categoria="procedimiento", n=0),
    documento("El plazo de un incidente critico es de cuatro horas", doc="pol", categoria="politica", n=1, pagina=2),
    # Con muy pocos fragmentos BM25 puntua 0 los terminos que estan justo en la mitad (idf = 0): se agrega relleno.
    *[documento(f"texto de relleno numero {i}", doc=f"otro{i}", categoria="glosario", n=10 + i) for i in range(6)],
]


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("PINECONE_API_KEY", "x")
    monkeypatch.setenv("INDEX_NAME", "idx")
    monkeypatch.setenv("GOOGLE_API_KEY", "y")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    rag = RAGSystem(VectorStoreFijo([CORPUS[1]]), CORPUS)
    monkeypatch.setattr(consultar.RAGSystem, "desde_configuracion", classmethod(lambda cls, cfg, **o: rag))


def test_muestra_cada_resultado_con_archivo_pagina_seccion_y_categoria(capsys):
    assert consultar.main(["GD-PRO-003"]) == 0
    salida = capsys.readouterr().out
    assert "[1] proc.md, pagina 1, seccion: 1. Objetivo" in salida
    assert "procedimiento" in salida and "GD-PRO-003" in salida


def test_texto_muestra_el_fragmento_completo(capsys):
    consultar.main(["GD-PRO-003", "--modo", "bm25", "--texto"])
    assert "regula el alta de articulos" in capsys.readouterr().out


def test_sin_resultados_lo_dice(capsys):
    assert consultar.main(["zzz qqq", "--modo", "bm25"]) == 0
    assert "Sin resultados" in capsys.readouterr().out


def test_el_filtro_de_categoria_aparece_en_el_encabezado(capsys):
    consultar.main(["incidente", "--categoria", "politica"])
    assert "categoria=politica" in capsys.readouterr().out


def test_una_categoria_inexistente_da_un_error_claro(capsys):
    assert consultar.main(["algo", "--categoria", "inventada"]) == 1
    assert "politica" in capsys.readouterr().err


def test_una_consulta_vacia_da_un_error_claro(capsys):
    assert consultar.main(["  "]) == 1
    assert "vacia" in capsys.readouterr().err


def test_sin_variables_de_entorno_explica_que_falta(monkeypatch, capsys):
    monkeypatch.undo()                       # saca el RAGSystem falso y las variables
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    for nombre in ("PINECONE_API_KEY", "INDEX_NAME", "GOOGLE_API_KEY"):
        monkeypatch.delenv(nombre, raising=False)
    assert consultar.main(["algo"]) == 1
    assert "PINECONE_API_KEY" in capsys.readouterr().err


def test_el_error_de_categoria_es_un_error_del_proyecto():
    assert issubclass(FiltroSinResultadosError, Exception)
