"""Integration tests for Phase 3C: Cascade Manager + Regenerator.

Tests the full cascade lifecycle: trigger → debounce → regenerate.
Also tests the CascadeManager debouncing behavior.
"""

import asyncio

import pytest

from shared.cascade.manager import CascadeManager
from shared.cascade.regenerator import CascadeRegenerator, CascadeResult
from shared.data.service import DataService
from shared.knowledge.graph_builder import build_variance_graph_from_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def data_dir():
    return "data/output"


@pytest.fixture
def data_service(data_dir):
    return DataService(data_dir)


@pytest.fixture
def graph(data_dir):
    return build_variance_graph_from_data(data_dir, period_id="2026-06")


@pytest.fixture
def manager(data_service, graph):
    """CascadeManager with 1-second debounce for fast testing."""
    return CascadeManager(
        data_service=data_service,
        graph=graph,
        debounce_seconds=1,  # 1s for testing instead of 60s
    )


@pytest.fixture
def sample_leaf_variance_id(graph):
    """Find a real leaf variance ID."""
    for node_id, data in graph._graph.nodes(data=True):
        if (
            data.get("node_type") == "variance"
            and data.get("period_id") == "2026-06"
            and data.get("base_id") == "BUDGET"
            and data.get("view_id") == "MTD"
        ):
            acct_id = data.get("account_id", "")
            acct_data = graph.get_node(acct_id)
            if acct_data and not acct_data.get("is_calculated", False):
                parent = acct_data.get("parent_id")
                if parent and graph.has_node(parent):
                    return node_id
    pytest.skip("No suitable leaf variance found")


# ---------------------------------------------------------------------------
# Tests: CascadeManager Debouncing
# ---------------------------------------------------------------------------


class TestCascadeManagerDebounce:
    """Test debounce behavior of CascadeManager."""

    @pytest.mark.asyncio
    async def test_single_edit_triggers_cascade(self, manager, sample_leaf_variance_id):
        """Single edit triggers cascade after debounce window."""
        await manager.on_narrative_changed(sample_leaf_variance_id, "2026-06")

        # Should be pending
        pending = manager.get_pending()
        assert len(pending) == 1
        assert pending[0]["period_id"] == "2026-06"

        # Wait for debounce (1s) + execution
        await asyncio.sleep(3)

        # Should be complete
        pending = manager.get_pending()
        assert len(pending) == 0

        history = manager.get_history()
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_rapid_edits_debounce(self, manager, sample_leaf_variance_id):
        """Rapid edits within debounce window result in single cascade."""
        # Trigger 3 rapid edits
        await manager.on_narrative_changed(sample_leaf_variance_id, "2026-06")
        await asyncio.sleep(0.1)
        await manager.on_narrative_changed(sample_leaf_variance_id, "2026-06")
        await asyncio.sleep(0.1)
        await manager.on_narrative_changed(sample_leaf_variance_id, "2026-06")

        # Should be only 1 pending (debounce resets)
        pending = manager.get_pending()
        assert len(pending) == 1

        # Wait for debounce + execution
        await asyncio.sleep(3)

        # Only 1 cascade should have executed
        history = manager.get_history()
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_execute_now_skips_debounce(self, manager, sample_leaf_variance_id):
        """execute_now runs cascade immediately."""
        result = await manager.execute_now(sample_leaf_variance_id, "2026-06")
        assert isinstance(result, CascadeResult)
        assert result.cascade_id != ""

    @pytest.mark.asyncio
    async def test_execute_now_cancels_pending(self, manager, sample_leaf_variance_id):
        """execute_now cancels any pending debounced cascade."""
        await manager.on_narrative_changed(sample_leaf_variance_id, "2026-06")
        assert len(manager.get_pending()) == 1

        result = await manager.execute_now(sample_leaf_variance_id, "2026-06")
        assert len(manager.get_pending()) == 0


# ---------------------------------------------------------------------------
# Tests: CascadeManager History
# ---------------------------------------------------------------------------


class TestCascadeManagerHistory:
    """Test cascade history tracking."""

    @pytest.mark.asyncio
    async def test_history_records_cascade(self, manager, sample_leaf_variance_id):
        """Cascade results are recorded in history."""
        result = await manager.execute_now(sample_leaf_variance_id, "2026-06")

        history = manager.get_history()
        assert len(history) == 1
        assert history[0]["cascade_id"] == result.cascade_id

    @pytest.mark.asyncio
    async def test_history_has_expected_fields(self, manager, sample_leaf_variance_id):
        """History entries have all expected fields."""
        await manager.execute_now(sample_leaf_variance_id, "2026-06")

        history = manager.get_history()
        entry = history[0]
        assert "cascade_id" in entry
        assert "trigger_variance_id" in entry
        assert "period_id" in entry
        assert "regenerated_count" in entry
        assert "total_seconds" in entry

    @pytest.mark.asyncio
    async def test_history_limit(self, manager, sample_leaf_variance_id):
        """get_history respects limit parameter."""
        await manager.execute_now(sample_leaf_variance_id, "2026-06")
        await manager.execute_now(sample_leaf_variance_id, "2026-06")

        history = manager.get_history(limit=1)
        assert len(history) == 1


# ---------------------------------------------------------------------------
# Tests: Full Chain Integration
# ---------------------------------------------------------------------------


class TestFullCascadeChain:
    """Test end-to-end cascade from trigger to regenerated narratives."""

    @pytest.mark.asyncio
    async def test_cascade_regenerates_parent_and_section(self, manager, sample_leaf_variance_id):
        """Full cascade regenerates at least some parent/section/exec."""
        result = await manager.execute_now(sample_leaf_variance_id, "2026-06")

        # Should have regenerated + skipped some entries
        total_processed = len(result.regenerated) + len(result.skipped)
        assert total_processed > 0

    @pytest.mark.asyncio
    async def test_cascade_chain_is_topological(self, manager, sample_leaf_variance_id, graph):
        """Cascade chain from graph is in topological order."""
        chain = graph.get_cascade_chain_typed(sample_leaf_variance_id)
        levels = [e["level"] for e in chain]
        assert levels == sorted(levels)

    @pytest.mark.asyncio
    async def test_cascade_result_complete(self, manager, sample_leaf_variance_id):
        """Cascade result has all audit fields populated."""
        result = await manager.execute_now(sample_leaf_variance_id, "2026-06")
        assert result.cascade_id != ""
        assert result.trigger_variance_id == sample_leaf_variance_id
        assert result.period_id == "2026-06"
        assert result.total_seconds > 0
        assert isinstance(result.chain, list)
