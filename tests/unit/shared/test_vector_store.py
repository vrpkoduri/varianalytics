"""Tests for VectorStore implementations."""

import pytest

from shared.knowledge.vector_store import InMemoryVectorStore, create_vector_store


class TestInMemoryVectorStore:
    @pytest.mark.asyncio
    async def test_upsert_and_query(self):
        store = InMemoryVectorStore()
        await store.upsert("v1", [1.0, 0.0, 0.0], {"account": "revenue"})
        await store.upsert("v2", [0.9, 0.1, 0.0], {"account": "cogs"})
        await store.upsert("v3", [0.0, 1.0, 0.0], {"account": "opex"})

        results = await store.query([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0].id == "v1"  # Most similar
        assert results[0].score > results[1].score

    @pytest.mark.asyncio
    async def test_empty_store_returns_empty(self):
        store = InMemoryVectorStore()
        results = await store.query([1.0, 0.0], top_k=3)
        assert results == []

    @pytest.mark.asyncio
    async def test_delete_removes_vector(self):
        store = InMemoryVectorStore()
        await store.upsert("v1", [1.0, 0.0], {"x": 1})
        assert await store.count() == 1
        await store.delete("v1")
        assert await store.count() == 0

    @pytest.mark.asyncio
    async def test_filter_dict_applies(self):
        store = InMemoryVectorStore()
        await store.upsert("v1", [1.0, 0.0], {"account": "revenue"})
        await store.upsert("v2", [0.9, 0.1], {"account": "cogs"})

        results = await store.query([1.0, 0.0], top_k=5, filter_dict={"account": "cogs"})
        assert len(results) == 1
        assert results[0].id == "v2"

    def test_factory_returns_inmemory_without_qdrant(self):
        store = create_vector_store(qdrant_url=None)
        assert isinstance(store, InMemoryVectorStore)
