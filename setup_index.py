"""Inicializacion del indice de Pinecone Serverless (idempotente).

Uso:
    python setup_index.py

Verifica si el indice (INDEX_NAME) existe:
* Si NO existe, lo crea en modo Serverless (AWS us-east-1, el unico que permite el plan gratis)
  con la dimension de los embeddings (1536) y metrica coseno, y espera a que quede listo.
* Si YA existe, no lo toca: solo comprueba que su dimension y su metrica sean compatibles.
  Si la dimension no coincide, falla con un mensaje claro (error comun #1 de la consigna).

Correrlo dos veces es seguro: la segunda vez dice que el indice ya existe.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable

import config
from almacen import leer_campo, crear_cliente, explicar_error_pinecone, verificar_indice_compatible
from errores import IndiceError, RagError

logger = logging.getLogger("rag.setup")


@dataclass(frozen=True)
class EstadoIndice:
    nombre: str
    dimension: int
    metrica: str
    cloud: str
    region: str
    creado: bool  # True: lo creo este script; False: ya existia


def _esta_listo(descripcion: Any) -> bool:
    return bool(leer_campo(leer_campo(descripcion, "status"), "ready", False))


def esperar_indice_listo(
    pc: Any,
    nombre: str,
    *,
    max_espera_s: float = 300.0,
    intervalo_s: float = 3.0,
    dormir: Callable[[float], None] = time.sleep,
    reloj: Callable[[], float] = time.monotonic,
) -> None:
    """Un indice recien creado tarda unos segundos en estar listo; hasta entonces rechaza operaciones."""
    limite = reloj() + max_espera_s
    while not _esta_listo(pc.describe_index(nombre)):
        if reloj() >= limite:
            raise IndiceError(
                f"El indice '{nombre}' no quedo listo en {max_espera_s:.0f} s. Mira su estado en la consola de "
                "Pinecone y volve a correr python setup_index.py."
            )
        dormir(intervalo_s)


def asegurar_indice(
    pc: Any,
    nombre: str,
    *,
    dimension: int = config.EMBEDDING_DIMENSION,
    metrica: str = config.METRICA,
    cloud: str = config.PINECONE_CLOUD,
    region: str = config.PINECONE_REGION,
    max_espera_s: float = 300.0,
    dormir: Callable[[float], None] = time.sleep,
    reloj: Callable[[], float] = time.monotonic,
) -> EstadoIndice:
    """Crea el indice si no existe; si existe, verifica que sea compatible. Devuelve el estado final."""
    if pc.has_index(nombre):
        descripcion = pc.describe_index(nombre)
        verificar_indice_compatible(descripcion, nombre, dimension, metrica)
        esperar_indice_listo(pc, nombre, max_espera_s=max_espera_s, dormir=dormir, reloj=reloj)
        return EstadoIndice(nombre, dimension, metrica, cloud, region, creado=False)

    from pinecone import ServerlessSpec

    logger.info("Creando indice serverless '%s' (%s, %s, dimension %s)...", nombre, cloud, region, dimension)
    pc.create_index(
        name=nombre,
        dimension=dimension,
        metric=metrica,
        spec=ServerlessSpec(cloud=cloud, region=region),
        timeout=-1,  # no esperar aca: se espera abajo con un limite de tiempo propio
    )
    esperar_indice_listo(pc, nombre, max_espera_s=max_espera_s, dormir=dormir, reloj=reloj)
    return EstadoIndice(nombre, dimension, metrica, cloud, region, creado=True)


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Crea el indice de Pinecone Serverless si no existe.").parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    try:
        cfg = config.cargar_configuracion(requiere_embeddings=False)
        estado = asegurar_indice(crear_cliente(cfg), cfg.index_name)
    except RagError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        mensaje = explicar_error_pinecone(exc)
        if mensaje is None:
            raise
        print(f"ERROR: {mensaje}", file=sys.stderr)
        return 1

    accion = "creado y listo" if estado.creado else "ya existia (no se modifico)"
    print(f"\nIndice '{estado.nombre}': {accion}")
    print(f"  Tipo ........ Serverless ({estado.cloud}, {estado.region})")
    print(f"  Dimension ... {estado.dimension}  (= dimension de {config.EMBEDDING_MODEL})")
    print(f"  Metrica ..... {estado.metrica}")
    print("Siguiente paso: python ingest.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
