"""Vector store abstraction -- Qdrant (MVP) / InMemory fallback.

Provides a consistent interface for vector similarity search.
Qdrant for production, InMemory for testing and when Qdrant unavailable.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result from vector store."""

    id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    async def upsert(self, id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        """Insert or update a vector with metadata."""

    @abstractmethod
    async def query(
        self, vector: list[float], top_k: int = 3, filter_dict: Optional[dict] = None
    ) -> list[SearchResult]:
        """Find top_k most similar vectors."""

    @abstractmethod
    async def delete(self, id: str) -> None:
        """Delete a vector by ID."""

    @abstractmethod
    async def count(self) -> int:
        """Return total number of stored vectors."""


class InMemoryVectorStore(VectorStore):
    """In-memory vector store using numpy cosine similarity.

    Good for testing and small datasets (<10K vectors).
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[list[float], dict[str, Any]]] = {}

    async def upsert(self, id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        self._store[id] = (vector, metadata)

    async def query(
        self, vector: list[float], top_k: int = 3, filter_dict: Optional[dict] = None
    ) -> list[SearchResult]:
        if not self._store:
            return []

        query_vec = np.array(vector)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        results: list[SearchResult] = []
        for id, (stored_vec, metadata) in self._store.items():
            # Apply optional metadata filter
            if filter_dict:
                if not all(metadata.get(k) == v for k, v in filter_dict.items()):
                    continue

            stored_arr = np.array(stored_vec)
            stored_norm = np.linalg.norm(stored_arr)
            if stored_norm == 0:
                continue

            score = float(np.dot(query_vec, stored_arr) / (query_norm * stored_norm))
            results.append(SearchResult(id=id, score=score, metadata=metadata))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    async def delete(self, id: str) -> None:
        self._store.pop(id, None)

    async def count(self) -> int:
        return len(self._store)


class QdrantVectorStore(VectorStore):
    """Qdrant-backed vector store for production use.

    Requires qdrant-client package and running Qdrant instance.
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection: str = "commentaries",
        dimensions: int = 1536,
    ) -> None:
        self._url = url
        self._collection = collection
        self._dimensions = dimensions
        self._client = None
        self._initialized = False

    async def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from qdrant_client import AsyncQdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._client = AsyncQdrantClient(url=self._url)

            # Create collection if not exists
            collections = await self._client.get_collections()
            names = [c.name for c in collections.collections]
            if self._collection not in names:
                await self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(size=self._dimensions, distance=Distance.COSINE),
                )
            self._initialized = True
        except Exception as exc:
            logger.warning("Failed to connect to Qdrant: %s", exc)
            self._client = None
            raise

    async def upsert(self, id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        await self._ensure_client()
        from qdrant_client.models import PointStruct

        await self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=hash(id) % (2**63), vector=vector, payload={**metadata, "_id": id}
                )
            ],
        )

    async def query(
        self, vector: list[float], top_k: int = 3, filter_dict: Optional[dict] = None
    ) -> list[SearchResult]:
        await self._ensure_client()
        results = await self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=top_k,
        )
        return [
            SearchResult(
                id=r.payload.get("_id", str(r.id)),
                score=r.score,
                metadata={k: v for k, v in r.payload.items() if k != "_id"},
            )
            for r in results
        ]

    async def delete(self, id: str) -> None:
        await self._ensure_client()
        from qdrant_client.models import PointIdsList

        await self._client.delete(
            collection_name=self._collection,
            points_selector=PointIdsList(points=[hash(id) % (2**63)]),
        )

    async def count(self) -> int:
        await self._ensure_client()
        info = await self._client.get_collection(self._collection)
        return info.points_count


def create_vector_store(qdrant_url: Optional[str] = None, dimensions: int = 1536) -> VectorStore:
    """Factory: tries Qdrant, falls back to InMemory."""
    if qdrant_url:
        try:
            # Quick health check
            import httpx

            resp = httpx.get(f"{qdrant_url}/healthz", timeout=2.0)
            if resp.status_code == 200:
                logger.info("Qdrant available at %s", qdrant_url)
                return QdrantVectorStore(url=qdrant_url, dimensions=dimensions)
        except Exception:
            pass
    logger.info("Using in-memory vector store (Qdrant unavailable)")
    return InMemoryVectorStore()
