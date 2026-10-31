"""Errores propios del proyecto: cada uno dice QUE fallo y COMO arreglarlo."""


class RagError(Exception):
    """Base de todos los errores del proyecto (los scripts la capturan y muestran un mensaje claro)."""


class ConfiguracionError(RagError):
    """Falta una variable de entorno o tiene un valor invalido (por ejemplo PINECONE_API_KEY)."""


class IngestaError(RagError):
    """No se pudieron leer, fragmentar o validar los documentos de origen."""


class IndiceError(RagError):
    """Problema con el indice de Pinecone: no existe, no quedo listo o no es compatible."""


class DimensionNoCoincideError(IndiceError):
    """La dimension de los vectores no coincide con la del indice (error comun #1 de la consigna).

    Pinecone rechaza el upsert; aca se detecta ANTES de gastar llamadas a la API de embeddings.
    """


class EmbeddingsError(RagError):
    """El proveedor de embeddings siguio fallando (cuota agotada) despues de reintentar."""


class NamespaceVacioError(RagError):
    """El namespace no tiene fragmentos: hay que indexar los documentos primero (python ingest.py)."""


class FiltroSinResultadosError(RagError):
    """El filtro por metadatos (por ejemplo una categoria) no coincide con ningun documento."""


class GoldenSetError(RagError):
    """El archivo del golden set no existe o no tiene el formato esperado."""
