"""Evaluacion: Recall@5, Precision@5, golden set, reporte y CLI."""
import json

import pytest

import config
import evaluate
from errores import GoldenSetError
from evaluate import CasoPrueba, calcular_metricas
from rag_system import ResultadoBusqueda
from tests.fakes import documento


# --------------------------------------------------------------------------- metricas de UNA pregunta
def test_acierto_en_primera_posicion():
    assert calcular_metricas("A", ["A", "B", "C", "D", "E"]) == (True, pytest.approx(0.2), 1)


def test_precision_cuenta_cuantos_de_los_5_son_del_documento_correcto():
    acierto, precision, posicion = calcular_metricas("A", ["A", "A", "B", "A", "C"])
    assert acierto and precision == pytest.approx(3 / 5) and posicion == 1


def test_el_recall_es_cero_si_el_documento_correcto_no_esta_entre_los_5():
    assert calcular_metricas("A", ["B", "C", "D", "E", "F"]) == (False, 0.0, None)


def test_un_acierto_fuera_del_top_k_no_cuenta():
    assert calcular_metricas("A", ["B", "C", "D", "E", "F", "A"], k=5) == (False, 0.0, None)
    assert calcular_metricas("A", ["B", "C", "D", "E", "F", "A"], k=6) == (True, pytest.approx(1 / 6), 6)


def test_si_se_recuperan_menos_de_k_la_precision_se_divide_igual_por_k():
    assert calcular_metricas("A", ["A", "A"], k=5) == (True, pytest.approx(2 / 5), 1)


def test_sin_resultados_todo_es_cero():
    assert calcular_metricas("A", []) == (False, 0.0, None)


def test_k_debe_ser_positivo():
    with pytest.raises(ValueError):
        calcular_metricas("A", ["A"], k=0)


# --------------------------------------------------------------------------- golden set
def _escribir(tmp_path, contenido):
    ruta = tmp_path / "golden.json"
    ruta.write_text(contenido if isinstance(contenido, str) else json.dumps(contenido), encoding="utf-8")
    return ruta


def test_carga_el_formato_de_la_consigna(tmp_path):
    ruta = _escribir(tmp_path, [{"pregunta": " ¿Algo? ", "documento_id_esperado": "doc-1"}])
    assert evaluate.cargar_golden_set(ruta) == [CasoPrueba("¿Algo?", "doc-1", "")]


def test_el_tipo_es_opcional_pero_se_conserva(tmp_path):
    ruta = _escribir(tmp_path, [{"pregunta": "p", "documento_id_esperado": "d", "tipo": "exacta"}])
    assert evaluate.cargar_golden_set(ruta)[0].tipo == "exacta"


@pytest.mark.parametrize(
    ("contenido", "mensaje"),
    [
        ("no es json", "JSON valido"),
        ({"pregunta": "x"}, "lista no vacia"),
        ([], "lista no vacia"),
        (["texto"], "objeto JSON"),
        ([{"documento_id_esperado": "d"}], "pregunta"),
        ([{"pregunta": "p"}], "documento_id_esperado"),
        ([{"pregunta": "  ", "documento_id_esperado": "d"}], "pregunta"),
        ([{"pregunta": "p", "documento_id_esperado": 5}], "documento_id_esperado"),
    ],
)
def test_un_golden_set_mal_formado_da_un_error_que_dice_donde(tmp_path, contenido, mensaje):
    with pytest.raises(GoldenSetError, match=mensaje):
        evaluate.cargar_golden_set(_escribir(tmp_path, contenido))


def test_un_golden_set_inexistente_da_un_error_claro(tmp_path):
    with pytest.raises(GoldenSetError, match="No existe"):
        evaluate.cargar_golden_set(tmp_path / "nada.json")


# --------------------------------------------------------------------------- evaluacion por modo
class RAGGuionado:
    """Un RAGSystem de mentira: devuelve los documentos que se le indican para cada modo y pregunta."""

    k = 5
    pesos = (0.5, 0.5)
    candidatos = 5

    def __init__(self, respuestas):
        self.respuestas = respuestas          # {modo: {pregunta: [documento_id, ...]}}
        self.llamadas = []

    def buscar(self, consulta, *, categoria=None, modo="hibrido"):
        self.llamadas.append((consulta, modo))
        ids = self.respuestas[modo].get(consulta, [])
        return [ResultadoBusqueda.desde_documento(i, documento("t", doc=d, n=i)) for i, d in enumerate(ids, start=1)]


CASOS = [CasoPrueba("p1", "A", "exacta"), CasoPrueba("p2", "B", "parafraseada")]


def test_promedia_recall_y_precision_sobre_todas_las_preguntas():
    rag = RAGGuionado({"hibrido": {"p1": ["A", "A", "X", "X", "X"], "p2": ["X", "B", "X", "X", "X"]}})
    resumen = evaluate.evaluar_modo(rag, CASOS, "hibrido")
    assert resumen.recall == 1.0
    assert resumen.precision == pytest.approx((2 / 5 + 1 / 5) / 2)
    assert [p.posicion_primer_acierto for p in resumen.preguntas] == [1, 2]
    assert resumen.preguntas[0].tipo == "exacta"


def test_una_pregunta_fallida_baja_el_recall_promedio():
    rag = RAGGuionado({"hibrido": {"p1": ["A", "X", "X", "X", "X"], "p2": ["X", "X", "X", "X", "X"]}})
    resumen = evaluate.evaluar_modo(rag, CASOS, "hibrido")
    assert resumen.recall == 0.5
    assert resumen.preguntas[1].acierto is False


def test_evaluar_corre_los_tres_modos_con_las_mismas_preguntas():
    rag = RAGGuionado({m: {"p1": ["A"] * 5, "p2": ["B"] * 5} for m in ("bm25", "vectorial", "hibrido")})
    resumenes = evaluate.evaluar(rag, CASOS)
    assert [r.modo for r in resumenes] == ["bm25", "vectorial", "hibrido"]
    assert {modo for _, modo in rag.llamadas} == {"bm25", "vectorial", "hibrido"}
    assert all(r.recall == r.precision == 1.0 for r in resumenes)


# --------------------------------------------------------------------------- reporte
def _resumenes():
    rag = RAGGuionado(
        {
            "bm25": {"p1": ["A"] * 5, "p2": []},
            "vectorial": {"p1": ["X"] * 5, "p2": ["B"] * 5},
            "hibrido": {"p1": ["A", "A", "A", "X", "X"], "p2": ["B", "B", "X", "X", "X"]},
        }
    )
    return evaluate.evaluar(rag, CASOS)


def test_el_reporte_muestra_una_tabla_con_las_dos_metricas_por_modo():
    reporte = evaluate.formatear_reporte(_resumenes())
    assert "2 preguntas, k = 5" in reporte
    assert "Recall@5" in reporte and "Precision@5" in reporte
    linea_hibrido = next(l for l in reporte.splitlines() if l.startswith("hibrido"))
    assert "1.00" in linea_hibrido and "0.50" in linea_hibrido
    assert "Mejor modo en esta corrida: hibrido" in reporte


def test_el_reporte_con_detalle_muestra_cada_pregunta():
    reporte = evaluate.formatear_reporte(_resumenes(), detalle=True)
    assert "esperado: A -> OK" in reporte and "FALLA" in reporte and "[exacta]" in reporte
    assert "(ninguno)" in reporte        # bm25 sin coincidencias en p2


def test_el_diccionario_para_json_tiene_k_cantidad_y_modos():
    datos = evaluate.a_diccionario(_resumenes())
    assert datos["k"] == 5 and datos["preguntas"] == 2 and len(datos["modos"]) == 3
    assert datos["modos"][2]["modo"] == "hibrido"
    json.dumps(datos)                    # tiene que ser serializable


def test_mrr_premia_poner_el_documento_correcto_mas_arriba():
    # bm25: p1 acierta en 1, p2 no aparece -> (1 + 0) / 2. vectorial: p1 falla, p2 acierta en 1 -> (0 + 1) / 2.
    bm25, vectorial, hibrido = _resumenes()
    assert bm25.mrr == pytest.approx(0.5) and vectorial.mrr == pytest.approx(0.5) and hibrido.mrr == pytest.approx(1.0)
    rag = RAGGuionado({"hibrido": {"p1": ["X", "X", "X", "X", "A"], "p2": ["X", "B", "X", "X", "X"]}})
    assert evaluate.evaluar_modo(rag, CASOS, "hibrido").mrr == pytest.approx((1 / 5 + 1 / 2) / 2)   # mismo Recall, peor posicion


def test_el_reporte_muestra_mrr_y_la_configuracion_del_hibrido():
    reporte = evaluate.formatear_reporte(_resumenes(), configuracion={"pesos": [0.3, 0.7], "candidatos": 10})
    assert "MRR" in reporte
    assert "pesos BM25/vectorial = 0.3/0.7, candidatos por recuperador = 10" in reporte
    linea_hibrido = next(l for l in reporte.splitlines() if l.startswith("hibrido"))
    assert linea_hibrido.split()[-1] == "1.00"                       # MRR del hibrido


def test_el_json_guarda_la_configuracion_y_el_mrr_de_cada_modo():
    datos = evaluate.a_diccionario(_resumenes(), {"pesos": [0.5, 0.5], "candidatos": 5})
    assert datos["configuracion_hibrido"] == {"pesos": [0.5, 0.5], "candidatos": 5}
    assert [m["mrr"] for m in datos["modos"]] == [0.5, 0.5, 1.0]


# --------------------------------------------------------------------------- CLI
@pytest.fixture
def entorno(monkeypatch):
    monkeypatch.setenv("PINECONE_API_KEY", "x")
    monkeypatch.setenv("INDEX_NAME", "idx")
    monkeypatch.setenv("GOOGLE_API_KEY", "y")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)


def _rag_falso(documentos_indexados=("A", "B")):
    rag = RAGGuionado({m: {"p1": ["A"] * 5, "p2": ["B"] * 5} for m in ("bm25", "vectorial", "hibrido")})
    rag.documentos_indexados = list(documentos_indexados)
    return rag


def test_main_imprime_el_reporte_y_guarda_el_json(entorno, monkeypatch, tmp_path, capsys):
    ruta = _escribir(tmp_path, [{"pregunta": "p1", "documento_id_esperado": "A"}, {"pregunta": "p2", "documento_id_esperado": "B"}])
    monkeypatch.setattr(evaluate.RAGSystem, "desde_configuracion", classmethod(lambda cls, cfg, **o: _rag_falso()))
    salida_json = tmp_path / "evidencia" / "eval.json"

    assert evaluate.main(["--golden", str(ruta), "--json", str(salida_json)]) == 0
    assert "EVALUACION DEL RECUPERADOR" in capsys.readouterr().out
    assert json.loads(salida_json.read_text(encoding="utf-8"))["preguntas"] == 2


def test_main_puede_evaluar_un_solo_modo(entorno, monkeypatch, tmp_path, capsys):
    ruta = _escribir(tmp_path, [{"pregunta": "p1", "documento_id_esperado": "A"}])
    rag = _rag_falso()
    monkeypatch.setattr(evaluate.RAGSystem, "desde_configuracion", classmethod(lambda cls, cfg, **o: rag))
    assert evaluate.main(["--golden", str(ruta), "--modo", "hibrido"]) == 0
    assert {modo for _, modo in rag.llamadas} == {"hibrido"}


def test_main_pasa_los_pesos_y_los_candidatos_al_recuperador_y_los_informa(entorno, monkeypatch, tmp_path, capsys):
    ruta = _escribir(tmp_path, [{"pregunta": "p1", "documento_id_esperado": "A"}])
    recibido = {}
    rag = _rag_falso()

    def fabrica(cls, cfg, **opciones):
        recibido.update(opciones)
        rag.pesos, rag.candidatos = opciones["pesos"], opciones["candidatos"]
        return rag

    monkeypatch.setattr(evaluate.RAGSystem, "desde_configuracion", classmethod(fabrica))
    assert evaluate.main(["--golden", str(ruta), "--pesos", "0.3", "0.7", "--candidatos", "10"]) == 0
    assert recibido == {"pesos": (0.3, 0.7), "candidatos": 10}
    assert "pesos BM25/vectorial = 0.3/0.7, candidatos por recuperador = 10" in capsys.readouterr().out


def test_main_avisa_si_el_golden_set_espera_documentos_que_no_estan_indexados(entorno, monkeypatch, tmp_path, capsys):
    ruta = _escribir(tmp_path, [{"pregunta": "p1", "documento_id_esperado": "NO-EXISTE"}])
    monkeypatch.setattr(evaluate.RAGSystem, "desde_configuracion", classmethod(lambda cls, cfg, **o: _rag_falso()))
    assert evaluate.main(["--golden", str(ruta)]) == 1
    assert "NO-EXISTE" in capsys.readouterr().err


def test_main_con_un_golden_set_roto_falla_con_codigo_1(entorno, tmp_path, capsys):
    assert evaluate.main(["--golden", str(_escribir(tmp_path, "{roto"))]) == 1
    assert "JSON" in capsys.readouterr().err


def test_main_sin_variables_de_entorno_explica_que_falta(monkeypatch, capsys):
    for nombre in ("PINECONE_API_KEY", "INDEX_NAME", "GOOGLE_API_KEY"):
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    assert evaluate.main([]) == 1
    assert "PINECONE_API_KEY" in capsys.readouterr().err


def test_el_golden_set_por_defecto_es_el_del_repo():
    assert evaluate.cargar_golden_set()[0].documento_id_esperado
    assert config.GOLDEN_SET_PATH.name == "golden_set.json"
