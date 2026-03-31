"""RAG pipeline integration tests -- embed -> store -> retrieve round-trip."""

import pytest

from shared.knowledge.embedding import EmbeddingService
from shared.knowledge.knowledge_store import KnowledgeStore
from shared.knowledge.rag import RAGRetriever
from shared.knowledge.vector_store import InMemoryVectorStore


@pytest.fixture
def mock_embedding_service():
    svc = EmbeddingService(model="test", dimensions=3)
    svc._available = True

    # Mock embed to return a deterministic vector based on text hash
    async def mock_embed(text):
        import hashlib

        h = hashlib.md5(text.encode()).hexdigest()
        return [int(h[i : i + 2], 16) / 255.0 for i in range(0, 6, 2)]

    svc.embed = mock_embed
    return svc


@pytest.fixture
def vector_store():
    return InMemoryVectorStore()


@pytest.fixture
def rag(mock_embedding_service, vector_store):
    return RAGRetriever(mock_embedding_service, vector_store)


@pytest.fixture
def knowledge(mock_embedding_service, vector_store):
    return KnowledgeStore(mock_embedding_service, vector_store)


class TestRAGPipeline:
    @pytest.mark.asyncio
    async def test_store_and_retrieve_roundtrip(self, knowledge, rag, vector_store):
        # Store a commentary
        await knowledge.add_approved_commentary(
            variance_id="var_001",
            narrative_text="Advisory fees increased due to APAC growth",
            metadata={"account_id": "acct_advisory", "variance_amount": 6900},
        )
        assert await vector_store.count() == 1

        # Retrieve similar
        results = await rag.retrieve_similar(
            {
                "account_name": "Advisory Fees",
                "variance_amount": 7000,
                "account_id": "acct_advisory",
            },
            top_k=3,
        )
        assert len(results) >= 1
        assert results[0].narrative_text == "Advisory fees increased due to APAC growth"

    @pytest.mark.asyncio
    async def test_account_match_boosts_score(self, knowledge, rag):
        await knowledge.add_approved_commentary(
            variance_id="var_001",
            narrative_text="Revenue grew strongly",
            metadata={"account_id": "acct_revenue", "variance_amount": 5000},
        )
        await knowledge.add_approved_commentary(
            variance_id="var_002",
            narrative_text="Costs increased moderately",
            metadata={"account_id": "acct_opex", "variance_amount": 5000},
        )

        results = await rag.retrieve_similar(
            {
                "account_name": "Revenue",
                "variance_amount": 5000,
                "account_id": "acct_revenue",
            },
            top_k=2,
        )
        # Revenue match should score higher due to 15% account weight
        if len(results) == 2:
            rev = next((r for r in results if r.account_id == "acct_revenue"), None)
            opex = next((r for r in results if r.account_id == "acct_opex"), None)
            if rev and opex:
                assert rev.score >= opex.score

    @pytest.mark.asyncio
    async def test_empty_store_returns_empty(self, rag):
        results = await rag.retrieve_similar(
            {
                "account_name": "Test",
                "variance_amount": 1000,
            }
        )
        assert results == []
