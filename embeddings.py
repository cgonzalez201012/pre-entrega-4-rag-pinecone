"""Embeddings con Gemini: fabrica del modelo y llamadas por lotes con reintentos ante cuota agotada."""
from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

from langchain_core.embeddings import Embeddings

import config
from errores import ConfiguracionError, EmbeddingsError

logger = logging.getLogger("rag.embeddings")

T = TypeVar("T")


def crear_embeddings(cfg: config.Configuracion) -> Embeddings:
    """Devuelve gemini-embedding-001 con la dimension fijada en config.EMBEDDING_DIMENSION.

    La libreria usa por defecto RETRIEVAL_DOCUMENT al indexar y RETRIEVAL_QUERY al consultar:
    son dos "modos" del MISMO modelo, pensados para busqueda (no es mezclar modelos).
    """
    if not cfg.google_api_key:
        raise ConfiguracionError(
            "Falta GOOGLE_API_KEY. Crea una clave gratis en https://aistudio.google.com/apikey "
            "y agregala al archivo .env."
        )

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        google_api_key=cfg.google_api_key,
        output_dimensionality=config.EMBEDDING_DIMENSION,
    )


def es_error_de_cuota(exc: BaseException) -> bool:
    """True si el error parece un limite de uso (HTTP 429 / RESOURCE_EXHAUSTED): vale la pena esperar y reintentar."""
    texto = f"{type(exc).__name__} {exc}".lower()
    return any(marca in texto for marca in ("429", "resource_exhausted", "quota", "rate limit", "rate_limit"))


def _con_reintentos(
    operacion: Callable[[], T],
    *,
    intentos: int,
    espera_inicial_s: float,
    dormir: Callable[[float], None],
) -> T:
    espera = espera_inicial_s
    for intento in range(1, intentos + 1):
        try:
            return operacion()
        except Exception as exc:  # noqa: BLE001 - se re-lanza todo lo que no sea cuota agotada
            if not es_error_de_cuota(exc):
                raise
            if intento == intentos:
                raise EmbeddingsError(
                    f"Gemini siguio rechazando las llamadas por limite de uso tras {intentos} intentos. "
                    "Es la cuota gratis (por minuto o por dia). Espera un rato y volve a correr el script: "
                    "lo ya indexado no se repite."
                ) from exc
            logger.warning("Limite de uso de Gemini (intento %s/%s). Espero %.0f s...", intento, intentos, espera)
            dormir(espera)
            espera *= 2
    raise AssertionError("inalcanzable")  # pragma: no cover


def embeber_en_lotes(
    embeddings: Embeddings,
    textos: list[str],
    *,
    tamano_lote: int = config.EMBED_BATCH_SIZE,
    intentos: int = config.EMBED_MAX_INTENTOS,
    espera_inicial_s: float = config.EMBED_ESPERA_INICIAL_S,
    dormir: Callable[[float], None] = time.sleep,
) -> list[list[float]]:
    """Convierte textos en vectores de a `tamano_lote`, reintentando con espera creciente si la cuota se agota.

    Los lotes chicos evitan superar el limite de tokens por minuto del plan gratis de Gemini.
    """
    if tamano_lote < 1:
        raise ValueError("tamano_lote debe ser >= 1")
    vectores: list[list[float]] = []
    for inicio in range(0, len(textos), tamano_lote):
        lote = textos[inicio : inicio + tamano_lote]
        vectores.extend(
            _con_reintentos(
                lambda lote=lote: embeddings.embed_documents(lote),
                intentos=intentos,
                espera_inicial_s=espera_inicial_s,
                dormir=dormir,
            )
        )
    return vectores
