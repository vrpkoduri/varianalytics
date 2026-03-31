"""Knowledge store -- coordinates embedding + vector store for approved commentaries.

Facade pattern: simplifies the embed -> store -> retrieve flow.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from shared.knowledge.embedding import EmbeddingService
from shared.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """Stores and retrieves approved commentaries with embeddings."""

    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore) -> None:
        self._embedding = embedding_service
        self._store = vector_store

    async def add_approved_commentary(
        self,
        variance_id: str,
        narrative_text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Embed and store an approved commentary.

        Returns True on success, False on failure.
        """
        try:
            embedding = await self._embedding.embed(narrative_text)
            if embedding is None:
                logger.warning("Failed to embed commentary for %s", variance_id)
                return False

            store_metadata = {
                "variance_id": variance_id,
                "narrative_text": narrative_text,
                **(metadata or {}),
            }
            await self._store.upsert(
                id=variance_id,
                vector=embedding,
                metadata=store_metadata,
            )
            logger.info("Stored commentary for %s", variance_id)
            return True
        except Exception as exc:
            logger.warning("Failed to store commentary for %s: %s", variance_id, exc)
            return False

    async def remove_commentary(self, variance_id: str) -> None:
        """Remove a commentary from the store."""
        try:
            await self._store.delete(variance_id)
        except Exception as exc:
            logger.warning("Failed to remove commentary %s: %s", variance_id, exc)

    async def count(self) -> int:
        """Return number of stored commentaries."""
        return await self._store.count()
