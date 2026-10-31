"""Configuracion central del sistema RAG en la nube (Pinecone Serverless + Gemini).

Las decisiones de diseno (modelo y dimension de embeddings, chunking, top-k, pesos del
hibrido) viven aca, en un solo lugar, para poder defenderlas y cambiarlas sin buscar por
el codigo. Los SECRETOS (claves de API) NO viven aca: se leen de variables de entorno
(archivo .env, que esta en .gitignore y nunca se sube al repo).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from errores import ConfiguracionError

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"                      # documentos de origen
GOLDEN_SET_PATH = BASE_DIR / "golden_set.json"    # preguntas de evaluacion
EXTENSIONES_VALIDAS = (".md", ".txt", ".pdf")

# --- Embeddings ------------------------------------------------------------------------
# El MISMO modelo y la MISMA dimension se usan para indexar y para consultar. La dimension
# del indice de Pinecone TIENE que ser EXACTAMENTE esta (error comun #1 de la consigna).
# 1536 es la dimension que la consigna usa de ejemplo; gemini-embedding-001 permite fijarla
# (por defecto devuelve 3072) con el parametro output_dimensionality.
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 1536
METRICA = "cosine"                 # la misma metrica con la que se entrenan estos embeddings

# --- Pinecone ----------------------------------------------------------------------------
# El plan gratis (Starter) solo permite indices serverless en AWS us-east-1.
PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"
NAMESPACE_POR_DEFECTO = "mercado-austral"   # un namespace por conjunto de datos / inquilino
TEXT_KEY = "text"                           # clave de la metadata donde se guarda el texto original
UPSERT_BATCH_SIZE = 100                     # vectores por upsert (la guia sugiere 100-200)
FETCH_BATCH_SIZE = 100                      # IDs por fetch al reconstruir el corpus de BM25
DELETE_BATCH_SIZE = 1000                    # maximo de IDs por llamada de borrado

# --- Embeddings: lotes y reintentos (cuota gratis de Gemini) -----------------------------
EMBED_BATCH_SIZE = 20              # textos por llamada a la API de embeddings
EMBED_MAX_INTENTOS = 4             # el primero + 3 reintentos ante cuota agotada (429)
EMBED_ESPERA_INICIAL_S = 10.0      # se duplica en cada reintento: 10 s, 20 s, 40 s

# --- Chunking (consigna: punto medio de ~500-800 tokens) ---------------------------------
CHUNK_SIZE_TOKENS = 600
CHUNK_OVERLAP_TOKENS = 60
TOKEN_ENCODING = "cl100k_base"     # solo para MEDIR fragmentos (aproximacion para Gemini)
CARACTERES_POR_TOKEN_APROX = 3.5   # plan B si tiktoken no puede bajar su vocabulario

# --- Recuperacion hibrida ----------------------------------------------------------------
TOP_K = 5                          # la consigna pide los 5 mejores
PESOS_HIBRIDO = (0.5, 0.5)         # (BM25, vectorial): igual peso a lo lexico y a lo semantico
# Cuantos fragmentos aporta CADA recuperador a la fusion antes de recortar a TOP_K (debe ser >= TOP_K).
# Con mas candidatos, un fragmento que ambos recuperadores ven (aunque sea en el puesto 7) llega a sumar los dos
# aportes y sube. Elegido con la grilla de docs/evidencia/ajuste-hibrido.txt (5 vs 10 candidatos; ver README).
CANDIDATOS_POR_RECUPERADOR = 10
CAMPO_ID_FUSION = "chunk_id"       # con que clave el EnsembleRetriever reconoce el mismo fragmento

# --- Metadatos ----------------------------------------------------------------------------
# El codigo de un documento (GD-POL-001) dice de que tipo es; de ahi sale la categoria.
CATEGORIAS_POR_TIPO = {
    "POL": "politica",
    "ROL": "roles",
    "PRO": "procedimiento",
    "GLO": "glosario",
}
CATEGORIA_POR_DEFECTO = "general"
CODIGO_SIN_DEFINIR = "sin-codigo"

_NOMBRE_INDICE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,43}[a-z0-9])?$")


@dataclass(frozen=True)
class Configuracion:
    """Variables de entorno ya validadas. Las claves no aparecen en el repr (no se filtran a logs)."""

    pinecone_api_key: str = field(repr=False)
    index_name: str
    namespace: str
    google_api_key: str | None = field(default=None, repr=False)


def cargar_configuracion(
    *, requiere_embeddings: bool = True, env: Mapping[str, str] | None = None
) -> Configuracion:
    """Lee y valida las variables de entorno. Informa TODAS las que faltan de una vez.

    `env` permite pasar un diccionario en los tests; por defecto se usa os.environ (los
    scripts llaman antes a load_dotenv() para cargar el archivo .env).
    """
    origen = os.environ if env is None else env

    def leer(nombre: str) -> str:
        return (origen.get(nombre) or "").strip()

    obligatorias = ["PINECONE_API_KEY", "INDEX_NAME"]
    if requiere_embeddings:
        obligatorias.append("GOOGLE_API_KEY")
    faltan = [nombre for nombre in obligatorias if not leer(nombre)]
    if faltan:
        raise ConfiguracionError(
            f"Faltan variables de entorno: {', '.join(faltan)}. "
            "Copia .env.example como .env y completalo (el .env nunca se sube al repo). "
            "PINECONE_API_KEY se crea en https://app.pinecone.io y GOOGLE_API_KEY en "
            "https://aistudio.google.com/apikey"
        )

    nombre_indice = leer("INDEX_NAME")
    if not _NOMBRE_INDICE.match(nombre_indice):
        raise ConfiguracionError(
            f"INDEX_NAME '{nombre_indice}' no es valido: Pinecone solo acepta minusculas, numeros y "
            "guiones (sin empezar ni terminar con guion), hasta 45 caracteres."
        )

    return Configuracion(
        pinecone_api_key=leer("PINECONE_API_KEY"),
        index_name=nombre_indice,
        namespace=leer("PINECONE_NAMESPACE") or NAMESPACE_POR_DEFECTO,
        google_api_key=leer("GOOGLE_API_KEY") or None,
    )
