"""Consulta el recuperador desde la terminal: muestra los 5 fragmentos mejor rankeados con su fuente.

Uso:
    python consultar.py "plazo de resolucion de un incidente critico"
    python consultar.py "GD-PRO-003" --modo bm25
    python consultar.py "quien aprueba el alta de una marca propia" --categoria procedimiento
    python consultar.py "..." --texto        # muestra el fragmento completo
"""
from __future__ import annotations

import argparse
import sys

import config
from almacen import explicar_error_pinecone
from errores import RagError
from rag_system import MODOS, RAGSystem


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Busca en el indice con el recuperador hibrido.")
    parser.add_argument("consulta", help="la pregunta o los terminos a buscar")
    parser.add_argument("--modo", choices=MODOS, default="hibrido")
    parser.add_argument("--categoria", help="filtra por la metadata 'categoria' (politica, roles, procedimiento, glosario)")
    parser.add_argument("--texto", action="store_true", help="muestra el texto completo de cada fragmento")
    args = parser.parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv()

    try:
        rag = RAGSystem.desde_configuracion(config.cargar_configuracion())
        resultados = rag.buscar(args.consulta, categoria=args.categoria, modo=args.modo)
    except (RagError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        mensaje = explicar_error_pinecone(exc)
        if mensaje is None:
            raise
        print(f"ERROR: {mensaje}", file=sys.stderr)
        return 1

    filtro = f", categoria={args.categoria}" if args.categoria else ""
    print(f"\nConsulta: {args.consulta!r}  (modo {args.modo}{filtro})")
    if not resultados:
        print("  Sin resultados.")
    for r in resultados:
        donde = f"{r.fuente}, pagina {r.pagina}" + (f", seccion: {r.seccion}" if r.seccion else "")
        print(f"\n[{r.posicion}] {donde}  ({r.categoria}, {r.codigo})")
        print("    " + (r.texto if args.texto else r.texto[:200].replace("\n", " ") + "..."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
