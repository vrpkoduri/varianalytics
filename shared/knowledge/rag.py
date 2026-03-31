"""RAG retrieval for commentary few-shot examples.

Retrieves top 2-3 similar approved commentaries from knowledge base
using weighted similarity: 70% semantic + 15% account match + 15% magnitude.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Optional

from shared.knowledge.embedding import EmbeddingService
from shared.knowledge.vector_store import SearchResult, VectorStore

logger = logging.getLogger(__name__)


@dataclass
class Commentary:
    """A retrieved commentary example for few-shot prompting."""

    commentary_id: str
    narrative_text: str
    account_id: str
    variance_amount: float
    score: float
    metadata: dict[str, Any]


class RAGRetriever:
    """Retrieves similar approved commentaries for RAG few-shot prompting.

    Weighted blend:
    - 70% semantic similarity (cosine from vector store)
    - 15% account match (1.0 if same account, 0.0 otherwise)
    - 15% magnitude proximity (log-ratio similarity)
    """

    SEMANTIC_WEIGHT = 0.70
    ACCOUNT_WEIGHT = 0.15
    MAGNITUDE_WEIGHT = 0.15

    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore) -> None:
        self._embedding = embedding_service
        self._store = vector_store

    async def retrieve_similar(
        self,
        variance_context: dict[str, Any],
        top_k: int = 3,
    ) -> list[Commentary]:
        """Retrieve top_k similar commentaries for a variance.

        Args:
            variance_context: Dict with account_id, variance_amount,
                            account_name, direction, etc.
            top_k: Number of examples to return.

        Returns:
            List of Commentary objects sorted by blended score.
        """
        # Build query text from context
        query_text = self._build_query_text(variance_context)

        # Embed query
        query_vector = await self._embedding.embed(query_text)
        if query_vector is None:
            return []

        # Over-fetch for re-ranking
        raw_results = await self._store.query(query_vector, top_k=top_k * 3)
        if not raw_results:
            return []

        # Re-rank with weighted blend
        target_account = variance_context.get("account_id", "")
        target_magnitude = abs(variance_context.get("variance_amount", 0))

        scored: list[tuple[float, SearchResult]] = []
        for result in raw_results:
            semantic = result.score  # Already cosine similarity [0, 1]
            account = 1.0 if result.metadata.get("account_id") == target_account else 0.0
            magnitude = self._magnitude_similarity(
                target_magnitude,
                abs(result.metadata.get("variance_amount", 0)),
            )
            blended = (
                self.SEMANTIC_WEIGHT * semantic
                + self.ACCOUNT_WEIGHT * account
                + self.MAGNITUDE_WEIGHT * magnitude
            )
            scored.append((blended, result))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            Commentary(
                commentary_id=result.id,
                narrative_text=result.metadata.get("narrative_text", ""),
                account_id=result.metadata.get("account_id", ""),
                variance_amount=result.metadata.get("variance_amount", 0),
                score=score,
                metadata=result.metadata,
            )
            for score, result in scored[:top_k]
        ]

    def _build_query_text(self, context: dict[str, Any]) -> str:
        """Build a natural language query from variance context."""
        parts = []
        if context.get("account_name"):
            parts.append(context["account_name"])
        if context.get("variance_amount"):
            direction = "increased" if context["variance_amount"] > 0 else "decreased"
            parts.append(f"{direction} by ${abs(context['variance_amount']):,.0f}")
        if context.get("bu_id"):
            parts.append(f"in {context['bu_id']}")
        if context.get("pl_category"):
            parts.append(f"({context['pl_category']})")
        return " ".join(parts) if parts else "variance analysis"

    @staticmethod
    def _magnitude_similarity(a: float, b: float) -> float:
        """Compute magnitude proximity score [0, 1].

        Uses log-ratio: 1 - |log(a/b)| normalized.
        Same formula as pass4_correlation.py.
        """
        if a <= 0 or b <= 0:
            return 0.0
        try:
            log_ratio = abs(math.log(a / b))
            return max(0.0, 1.0 - log_ratio / 3.0)  # 3.0 = ~20x difference -> score 0
        except (ValueError, ZeroDivisionError):
            return 0.0
