"""Evaluacion cuantitativa del recuperador: Recall@5 y Precision@5 sobre un golden set.

Uso:
    python evaluate.py                    # compara los 3 modos: bm25, vectorial e hibrido
    python evaluate.py --modo hibrido     # solo el sistema final
    python evaluate.py -v                 # detalle pregunta por pregunta
    python evaluate.py --json docs/evidencia/evaluacion.json

El golden set (golden_set.json) es una lista de pares {"pregunta": ..., "documento_id_esperado": ...}
donde el documento correcto se conoce de antemano. "documento_id" es el nombre del archivo sin
extension (el mismo que se guarda en la metadata al indexar).

Metricas (k = 5, los 5 fragmentos que devuelve el sistema):
* Recall@5    = 1 si el documento correcto aparece entre los 5 recuperados, 0 si no. El promedio de todas
                las preguntas es la proporcion de preguntas en las que el sistema "entrega el contexto
                necesario".
* Precision@5 = (fragmentos de los 5 recuperados que pertenecen al documento correcto) / 5.
                Mide cuanto ruido hay en el contexto. El denominador es siempre k: si el sistema devuelve
                menos de 5, la precision baja.
Como cada documento se parte en varios fragmentos, la Precision@5 maxima de una pregunta esta acotada por la
cantidad de fragmentos del documento correcto: 1.0 solo es alcanzable si ese documento tiene 5 o mas.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import config
from almacen import explicar_error_pinecone
from errores import GoldenSetError, RagError
from rag_system import MODOS, RAGSystem


# --------------------------------------------------------------------------- golden set
@dataclass(frozen=True)
class CasoPrueba:
    pregunta: str
    documento_id_esperado: str
    tipo: str = ""  # opcional: "exacta" (codigos, siglas), "parafraseada" o "mixta"


def cargar_golden_set(ruta: Path | str = config.GOLDEN_SET_PATH) -> list[CasoPrueba]:
    ruta = Path(ruta)
    if not ruta.is_file():
        raise GoldenSetError(f"No existe el golden set: {ruta}")
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GoldenSetError(f"{ruta.name} no es un JSON valido: {exc}") from exc
    if not isinstance(crudo, list) or not crudo:
        raise GoldenSetError(f"{ruta.name} debe ser una lista no vacia de objetos con 'pregunta' y 'documento_id_esperado'.")

    casos: list[CasoPrueba] = []
    for numero, item in enumerate(crudo, start=1):
        if not isinstance(item, dict):
            raise GoldenSetError(f"Caso {numero} de {ruta.name}: debe ser un objeto JSON.")
        for clave in ("pregunta", "documento_id_esperado"):
            if not isinstance(item.get(clave), str) or not item[clave].strip():
                raise GoldenSetError(f"Caso {numero} de {ruta.name}: falta '{clave}' (texto no vacio).")
        casos.append(
            CasoPrueba(item["pregunta"].strip(), item["documento_id_esperado"].strip(), str(item.get("tipo", "")))
        )
    return casos


# --------------------------------------------------------------------------- metricas
@dataclass(frozen=True)
class MetricasPregunta:
    pregunta: str
    tipo: str
    esperado: str
    recuperados: tuple[str, ...]     # documento_id de cada fragmento recuperado, en orden
    acierto: bool                    # Recall@k de esta pregunta
    precision: float                 # Precision@k de esta pregunta
    posicion_primer_acierto: int | None


def calcular_metricas(esperado: str, recuperados: list[str], k: int = config.TOP_K) -> tuple[bool, float, int | None]:
    """Devuelve (recall@k, precision@k, posicion del primer fragmento correcto) para UNA pregunta."""
    if k < 1:
        raise ValueError("k debe ser >= 1")
    top = recuperados[:k]
    aciertos = sum(1 for documento in top if documento == esperado)
    posicion = next((i for i, documento in enumerate(top, start=1) if documento == esperado), None)
    return aciertos > 0, aciertos / k, posicion


@dataclass(frozen=True)
class ResumenModo:
    modo: str
    k: int
    recall: float
    precision: float
    preguntas: tuple[MetricasPregunta, ...] = field(default_factory=tuple)

    @property
    def mrr(self) -> float:
        """Mean Reciprocal Rank: promedio de 1 / (posicion del primer fragmento correcto); 0 si no aparece.

        Complementa a Recall y Precision: dos modos con el mismo Recall@5 pueden diferir en QUE TAN ARRIBA
        ponen el documento correcto (posicion 1 vale 1.0; posicion 5 vale 0.2).
        """
        if not self.preguntas:
            return 0.0
        return sum(1 / p.posicion_primer_acierto for p in self.preguntas if p.posicion_primer_acierto) / len(self.preguntas)


def evaluar_modo(rag: RAGSystem, casos: list[CasoPrueba], modo: str) -> ResumenModo:
    """Ejecuta todas las preguntas con un modo de busqueda y promedia las metricas."""
    detalle: list[MetricasPregunta] = []
    for caso in casos:
        recuperados = tuple(r.documento_id for r in rag.buscar(caso.pregunta, modo=modo))
        acierto, precision, posicion = calcular_metricas(caso.documento_id_esperado, list(recuperados), rag.k)
        detalle.append(
            MetricasPregunta(caso.pregunta, caso.tipo, caso.documento_id_esperado, recuperados, acierto, precision, posicion)
        )
    return ResumenModo(
        modo=modo,
        k=rag.k,
        recall=sum(1 for d in detalle if d.acierto) / len(detalle),
        precision=sum(d.precision for d in detalle) / len(detalle),
        preguntas=tuple(detalle),
    )


def evaluar(rag: RAGSystem, casos: list[CasoPrueba], modos: tuple[str, ...] = MODOS) -> list[ResumenModo]:
    return [evaluar_modo(rag, casos, modo) for modo in modos]


# --------------------------------------------------------------------------- reporte
def formatear_reporte(
    resumenes: list[ResumenModo], *, detalle: bool = False, configuracion: dict[str, Any] | None = None
) -> str:
    k = resumenes[0].k
    n = len(resumenes[0].preguntas)
    lineas = ["", f"EVALUACION DEL RECUPERADOR ({n} preguntas, k = {k})"]
    if configuracion:
        pesos = configuracion["pesos"]
        lineas.append(
            f"Hibrido: pesos BM25/vectorial = {pesos[0]:g}/{pesos[1]:g}, "
            f"candidatos por recuperador = {configuracion['candidatos']}"
        )
    lineas += ["-" * 64, f"{'Modo':<12}{f'Recall@{k}':>12}{f'Precision@{k}':>16}{'MRR':>10}"]
    for r in resumenes:
        lineas.append(f"{r.modo:<12}{r.recall:>12.2f}{r.precision:>16.2f}{r.mrr:>10.2f}")
    lineas.append("-" * 64)

    if detalle:
        for r in resumenes:
            lineas.append(f"\n[{r.modo}]")
            for i, p in enumerate(r.preguntas, start=1):
                marca = f"OK  (primer acierto en la posicion {p.posicion_primer_acierto})" if p.acierto else "FALLA"
                etiqueta = f" [{p.tipo}]" if p.tipo else ""
                lineas.append(f"  {i}. {p.pregunta}{etiqueta}")
                lineas.append(f"     esperado: {p.esperado} -> {marca}  precision {p.precision:.2f}")
                lineas.append(f"     recuperados: {', '.join(p.recuperados) or '(ninguno)'}")

    mejor = max(resumenes, key=lambda r: (r.recall, r.precision))
    lineas.append(f"\nMejor modo en esta corrida: {mejor.modo} (Recall@{k} {mejor.recall:.2f}, Precision@{k} {mejor.precision:.2f})")
    return "\n".join(lineas)


def a_diccionario(resumenes: list[ResumenModo], configuracion: dict[str, Any] | None = None) -> dict[str, Any]:
    resultado: dict[str, Any] = {"k": resumenes[0].k, "preguntas": len(resumenes[0].preguntas)}
    if configuracion:
        resultado["configuracion_hibrido"] = configuracion
    resultado["modos"] = [{**asdict(r), "mrr": r.mrr} for r in resumenes]
    return resultado


# --------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calcula Recall@5 y Precision@5 del recuperador.")
    parser.add_argument("--golden", default=str(config.GOLDEN_SET_PATH), help="archivo JSON con las preguntas")
    parser.add_argument("--modo", choices=("todos",) + MODOS, default="todos")
    parser.add_argument("-v", "--detalle", action="store_true", help="detalle pregunta por pregunta")
    parser.add_argument("--json", metavar="RUTA", help="guarda los resultados en un archivo JSON")
    parser.add_argument(
        "--pesos", nargs=2, type=float, metavar=("BM25", "VECTORIAL"), default=list(config.PESOS_HIBRIDO),
        help="pesos del EnsembleRetriever (por defecto: %(default)s)",
    )
    parser.add_argument(
        "--candidatos", type=int, default=config.CANDIDATOS_POR_RECUPERADOR, metavar="N",
        help="fragmentos que aporta cada recuperador a la fusion antes de recortar a 5 (por defecto: %(default)s)",
    )
    args = parser.parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv()

    try:
        casos = cargar_golden_set(args.golden)
        rag = RAGSystem.desde_configuracion(
            config.cargar_configuracion(), pesos=tuple(args.pesos), candidatos=args.candidatos
        )
        desconocidos = sorted({c.documento_id_esperado for c in casos} - set(rag.documentos_indexados))
        if desconocidos:
            raise GoldenSetError(
                f"El golden set espera documentos que no estan indexados: {desconocidos}. "
                f"Documentos indexados: {rag.documentos_indexados}."
            )
        modos = MODOS if args.modo == "todos" else (args.modo,)
        resumenes = evaluar(rag, casos, modos)
    except RagError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        mensaje = explicar_error_pinecone(exc)
        if mensaje is None:
            raise
        print(f"ERROR: {mensaje}", file=sys.stderr)
        return 1

    configuracion = {"pesos": list(rag.pesos), "candidatos": rag.candidatos}
    print(formatear_reporte(resumenes, detalle=args.detalle, configuracion=configuracion))
    if args.json:
        destino = Path(args.json)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(a_diccionario(resumenes, configuracion), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nResultados guardados en {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
