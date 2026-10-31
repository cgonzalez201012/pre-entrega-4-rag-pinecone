"""Piezas falsas para probar el sistema SIN claves ni red.

- `EmbeddingsSimulados`: vectores deterministas basados en palabras (no entienden significado, solo
  prueban la logica). Tienen la dimension real del proyecto (config.EMBEDDING_DIMENSION).
- `EmbeddingsConFallas` / `EmbeddingsQueSeRompe`: fallan a proposito (cuota agotada / error fatal).
- `FakeIndex` / `FakePinecone`: un Pinecone en memoria con la misma interfaz que usa el proyecto
  (upsert, fetch, list, delete, query, describe_index_stats, create_index, describe_index...).
- `VectorStoreFijo`: un vector store cuyo ranking se fija a mano (para probar la fusion hibrida).
- `crear_pdf`: escribe un PDF minimo con una linea de texto por pagina.
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever

import config


class ErrorHTTP(Exception):
    """Imita las excepciones del SDK de Pinecone: tienen un atributo `status` con el codigo HTTP."""

    def __init__(self, status: int, mensaje: str = "") -> None:
        super().__init__(mensaje or f"HTTP {status}")
        self.status = status


def contar_palabras(texto: str) -> int:
    """Contador de 'tokens' para los tests: una palabra = un token (no usa tiktoken ni red)."""
    return len(texto.split())


# --------------------------------------------------------------------------- embeddings
class EmbeddingsSimulados(Embeddings):
    def __init__(self, dimension: int = config.EMBEDDING_DIMENSION) -> None:
        self.dimension = dimension
        self.llamadas_documentos = 0   # cuantos textos se embebieron
        self.llamadas_consultas = 0
        self.lotes: list[int] = []     # tamano de cada llamada a embed_documents

    @staticmethod
    def _palabras(texto: str) -> list[str]:
        sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
        return re.findall(r"[a-z0-9]+", sin_tildes)

    def _vector(self, texto: str) -> list[float]:
        v = [0.0] * self.dimension
        for palabra in self._palabras(texto):
            v[int(hashlib.sha256(palabra.encode()).hexdigest(), 16) % self.dimension] += 1.0
        norma = math.sqrt(sum(x * x for x in v))
        return [x / norma for x in v] if norma else v

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.llamadas_documentos += len(texts)
        self.lotes.append(len(texts))
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        self.llamadas_consultas += 1
        return self._vector(text)


class EmbeddingsConFallas(EmbeddingsSimulados):
    """Falla con un error de cuota (429) las primeras `fallas` llamadas a embed_documents."""

    def __init__(self, fallas: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fallas = fallas
        self.intentos = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.intentos += 1
        if self.intentos <= self.fallas:
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")
        return super().embed_documents(texts)


class EmbeddingsQueSeRompe(EmbeddingsSimulados):
    """Funciona para los primeros `despues_de` textos y luego falla con un error NO reintentable."""

    def __init__(self, despues_de: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.despues_de = despues_de

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.llamadas_documentos + len(texts) > self.despues_de:
            raise ValueError("clave invalida")
        return super().embed_documents(texts)


# --------------------------------------------------------------------------- Pinecone en memoria
def _cumple(metadata: dict[str, Any], filtro: dict[str, Any] | None) -> bool:
    """Filtros al estilo Pinecone: {"campo": valor} o {"campo": {"$eq": v}} / {"$in": [..]}."""
    for campo, condicion in (filtro or {}).items():
        valor = metadata.get(campo)
        if isinstance(condicion, dict):
            for operador, esperado in condicion.items():
                if operador == "$eq" and valor != esperado:
                    return False
                if operador == "$in" and valor not in esperado:
                    return False
        elif valor != condicion:
            return False
    return True


class FakeIndex:
    def __init__(self, tamano_pagina: int = 3, retraso_visibilidad: int = 0) -> None:
        self.namespaces: dict[str, dict[str, dict[str, Any]]] = {}
        self.tamano_pagina = tamano_pagina
        self.retraso_visibilidad = retraso_visibilidad  # lecturas de stats que muestran 0 (consistencia eventual)
        self.config = SimpleNamespace(host="fake.svc.pinecone.io", api_key="clave-falsa")
        self.llamadas_upsert: list[tuple[str | None, int]] = []
        self.llamadas_delete: list[dict[str, Any]] = []
        self.llamadas_fetch: list[int] = []
        self.llamadas_query: list[dict[str, Any]] = []
        self._lecturas_stats = 0

    def _ns(self, nombre: str | None) -> dict[str, dict[str, Any]]:
        return self.namespaces.get(nombre or "", {})

    def upsert(self, vectors: list[dict[str, Any]], namespace: str | None = None, **_: Any) -> dict[str, int]:
        destino = self.namespaces.setdefault(namespace or "", {})
        for v in vectors:
            destino[v["id"]] = {"values": list(v["values"]), "metadata": dict(v["metadata"])}
        self.llamadas_upsert.append((namespace, len(vectors)))
        return {"upserted_count": len(vectors)}

    def list(self, namespace: str | None = None, **_: Any):
        ids = sorted(self._ns(namespace))
        for i in range(0, len(ids), self.tamano_pagina):
            yield ids[i : i + self.tamano_pagina]

    def fetch(self, ids: list[str], namespace: str | None = None, **_: Any) -> SimpleNamespace:
        self.llamadas_fetch.append(len(ids))
        origen = self._ns(namespace)
        return SimpleNamespace(
            vectors={
                i: SimpleNamespace(id=i, values=origen[i]["values"], metadata=dict(origen[i]["metadata"]))
                for i in ids
                if i in origen
            }
        )

    def delete(
        self, ids: list[str] | None = None, delete_all: bool | None = None, namespace: str | None = None, **_: Any
    ) -> dict[str, Any]:
        self.llamadas_delete.append({"ids": list(ids or []), "delete_all": delete_all, "namespace": namespace})
        if delete_all:
            if (namespace or "") not in self.namespaces:
                raise ErrorHTTP(404, "Namespace not found")
            del self.namespaces[namespace or ""]
        else:
            for i in ids or []:
                self._ns(namespace).pop(i, None)
        return {}

    def query(
        self,
        vector: list[float],
        top_k: int,
        include_metadata: bool = False,
        namespace: str | None = None,
        filter: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        self.llamadas_query.append({"namespace": namespace, "filter": filter, "top_k": top_k})
        candidatos = []
        for id_, registro in self._ns(namespace).items():
            if not _cumple(registro["metadata"], filter):
                continue
            puntaje = sum(a * b for a, b in zip(vector, registro["values"]))  # vectores normalizados: coseno
            candidatos.append((puntaje, id_, registro["metadata"]))
        candidatos.sort(key=lambda c: (-c[0], c[1]))
        return {
            "matches": [
                {"id": id_, "score": puntaje, "metadata": dict(metadata)}
                for puntaje, id_, metadata in candidatos[:top_k]
            ]
        }

    def describe_index_stats(self) -> SimpleNamespace:
        self._lecturas_stats += 1
        mostrar = self._lecturas_stats > self.retraso_visibilidad
        return SimpleNamespace(
            namespaces={
                nombre: SimpleNamespace(vector_count=len(vectores) if mostrar else 0)
                for nombre, vectores in self.namespaces.items()
            }
        )

    def cantidad(self, namespace: str) -> int:
        return len(self._ns(namespace))


class FakePinecone:
    def __init__(self, listo_tras: int = 0) -> None:
        self.listo_tras = listo_tras   # cuantas veces describe_index dice "no listo" tras crear un indice
        self._indices: dict[str, dict[str, Any]] = {}
        self.creados: list[dict[str, Any]] = []

    def agregar_indice(self, nombre: str, dimension: int | None = config.EMBEDDING_DIMENSION, metric: str = "cosine") -> FakeIndex:
        indice = FakeIndex()
        self._indices[nombre] = {"dimension": dimension, "metric": metric, "index": indice, "consultas": 10**6}
        return indice

    def has_index(self, name: str) -> bool:
        return name in self._indices

    def create_index(self, name: str, spec: Any, dimension: int | None = None, metric: str = "cosine", timeout: Any = None, **_: Any) -> None:
        self.creados.append({"name": name, "spec": spec, "dimension": dimension, "metric": metric, "timeout": timeout})
        self._indices[name] = {"dimension": dimension, "metric": metric, "index": FakeIndex(), "consultas": 0}

    def describe_index(self, name: str) -> SimpleNamespace:
        info = self._indices[name]
        info["consultas"] += 1
        return SimpleNamespace(
            name=name,
            dimension=info["dimension"],
            metric=info["metric"],
            host=f"{name}.svc.fake.pinecone.io",
            status=SimpleNamespace(ready=info["consultas"] > self.listo_tras),
        )

    def Index(self, name: str) -> FakeIndex:  # noqa: N802 - mismo nombre que el SDK
        return self._indices[name]["index"]


# --------------------------------------------------------------------------- ranking fijo
class RetrieverFijo(BaseRetriever):
    docs: list[Document]
    search_kwargs: dict[str, Any] = {}

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        # Como Pinecone: devuelve como maximo `k` resultados (por defecto, todos los que tiene).
        return list(self.docs)[: self.search_kwargs.get("k", len(self.docs))]


class VectorStoreFijo:
    """Devuelve SIEMPRE los mismos documentos, en el mismo orden (la 'busqueda semantica' queda fija)."""

    def __init__(self, docs: list[Document], **_: Any) -> None:
        self.docs = docs
        self.pedidos: list[dict[str, Any]] = []   # search_kwargs con los que se pidio cada retriever

    def as_retriever(self, search_kwargs: dict[str, Any] | None = None) -> RetrieverFijo:
        self.pedidos.append(dict(search_kwargs or {}))
        return RetrieverFijo(docs=self.docs, search_kwargs=dict(search_kwargs or {}))


def documento(texto: str, *, doc: str = "doc", categoria: str = "politica", n: int = 0, pagina: int = 1) -> Document:
    """Un fragmento con el esquema de metadatos completo (para armar corpus chicos a mano)."""
    return Document(
        page_content=texto,
        metadata={
            "chunk_id": f"{doc}#{n}",
            "documento_id": doc,
            "fuente": f"{doc}.md",
            "pagina": pagina,
            "categoria": categoria,
            "codigo": "GD-POL-001",
            "seccion": "1. Objetivo",
            "chunk_index": n,
            "tokens": len(texto.split()),
        },
    )


# --------------------------------------------------------------------------- PDF
def crear_pdf(ruta: Path, paginas: list[str]) -> None:
    """Escribe un PDF minimo (texto ASCII, una linea por pagina). Sirve para probar la lectura por pagina."""
    cantidad = len(paginas)
    hijos = " ".join(f"{4 + 2 * i} 0 R" for i in range(cantidad))
    objetos = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{hijos}] /Count {cantidad} >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for i, texto in enumerate(paginas):
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {5 + 2 * i} 0 R "
            "/Resources << /Font << /F1 3 0 R >> >> >>"
        )
        escapado = texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        flujo = f"BT /F1 12 Tf 72 720 Td ({escapado}) Tj ET" if texto else ""
        objetos.append(f"<< /Length {len(flujo)} >>\nstream\n{flujo}\nendstream")

    salida = b"%PDF-1.4\n"
    desplazamientos = []
    for numero, objeto in enumerate(objetos, start=1):
        desplazamientos.append(len(salida))
        salida += f"{numero} 0 obj\n{objeto}\nendobj\n".encode("latin-1")
    inicio_xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for desplazamiento in desplazamientos:
        salida += f"{desplazamiento:010d} 00000 n \n".encode()
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode()
    ruta.write_bytes(salida)
