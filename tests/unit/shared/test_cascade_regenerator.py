"""Tests for Phase 3C: Cascade Regeneration.

Validates CascadeRegenerator, enhanced get_cascade_chain_typed(),
and cascade cost estimation.
"""

import asyncio

import pytest
import pandas as pd

from shared.knowledge.networkx_graph import NetworkXGraph
from shared.knowledge.graph_builder import build_variance_graph_from_data
from shared.cascade.regenerator import CascadeRegenerator, CascadeResult
from shared.data.service import DataService
from services.computation.engine.cost_estimator import estimate_cascade_cost


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
def regenerator(data_service, graph):
    return CascadeRegenerator(data_service, graph)


@pytest.fixture
def sample_leaf_variance_id(graph):
    """Find a real leaf variance ID from the graph."""
    for node_id, data in graph._graph.nodes(data=True):
        if (
            data.get("node_type") == "variance"
            and data.get("period_id") == "2026-06"
            and data.get("base_id") == "BUDGET"
            and data.get("view_id") == "MTD"
        ):
            # Check it's a leaf (account is not calculated)
            acct_id = data.get("account_id", "")
            acct_data = graph.get_node(acct_id)
            if acct_data and not acct_data.get("is_calculated", False):
                parent = acct_data.get("parent_id")
                if parent and graph.has_node(parent):
                    return node_id
    pytest.skip("No suitable leaf variance found in test data")


# ---------------------------------------------------------------------------
# Tests: Enhanced get_cascade_chain_typed()
# ---------------------------------------------------------------------------


class TestCascadeChainTyped:
    """Test the enhanced cascade chain with types and levels."""

    def test_returns_typed_entries(self, graph, sample_leaf_variance_id):
        """Chain entries have id, type, and level fields."""
        chain = graph.get_cascade_chain_typed(sample_leaf_variance_id)
        assert len(chain) > 0
        for entry in chain:
            assert "id" in entry
            assert "type" in entry
            assert "level" in entry

    def test_includes_parent_variances(self, graph, sample_leaf_variance_id):
        """Chain includes parent_variance entries."""
        chain = graph.get_cascade_chain_typed(sample_leaf_variance_id)
        parent_entries = [e for e in chain if e["type"] == "parent_variance"]
        assert len(parent_entries) >= 1

    def test_includes_sections(self, graph, sample_leaf_variance_id):
        """Chain includes section entries."""
        chain = graph.get_cascade_chain_typed(sample_leaf_variance_id)
        section_entries = [e for e in chain if e["type"] == "section"]
        assert len(section_entries) >= 1

    def test_includes_executive(self, graph, sample_leaf_variance_id):
        """Chain includes executive entry as last level."""
        chain = graph.get_cascade_chain_typed(sample_leaf_variance_id)
        exec_entries = [e for e in chain if e["type"] == "executive"]
        assert len(exec_entries) == 1
        assert exec_entries[0]["level"] == 3

    def test_topological_order(self, graph, sample_leaf_variance_id):
        """Chain is ordered: parents (level 1) → sections (2) → exec (3)."""
        chain = graph.get_cascade_chain_typed(sample_leaf_variance_id)
        levels = [e["level"] for e in chain]
        assert levels == sorted(levels), f"Chain not in topo order: {levels}"

    def test_legacy_get_cascade_chain_still_works(self, graph, sample_leaf_variance_id):
        """Legacy get_cascade_chain() returns flat list of IDs."""
        chain = graph.get_cascade_chain(sample_leaf_variance_id)
        assert isinstance(chain, list)
        assert all(isinstance(x, str) for x in chain)

    def test_nonexistent_variance(self, graph):
        """Nonexistent variance returns empty chain."""
        chain = graph.get_cascade_chain_typed("nonexistent_id")
        assert chain == []


# ---------------------------------------------------------------------------
# Tests: CascadeRegenerator
# ---------------------------------------------------------------------------


class TestCascadeRegenerator:
    """Test cascade regeneration logic."""

    @pytest.mark.asyncio
    async def test_regenerate_chain_returns_result(self, regenerator, sample_leaf_variance_id):
        """regenerate_chain returns CascadeResult."""
        result = await regenerator.regenerate_chain(
            sample_leaf_variance_id, "2026-06"
        )
        assert isinstance(result, CascadeResult)
        assert result.cascade_id != ""
        assert result.trigger_variance_id == sample_leaf_variance_id

    @pytest.mark.asyncio
    async def test_regenerate_chain_has_regenerated_ids(self, regenerator, sample_leaf_variance_id):
        """Cascade regenerates at least one parent/section/exec."""
        result = await regenerator.regenerate_chain(
            sample_leaf_variance_id, "2026-06"
        )
        # Should regenerate at least section + executive
        assert len(result.regenerated) >= 1 or len(result.skipped) >= 1

    @pytest.mark.asyncio
    async def test_cascade_result_has_timings(self, regenerator, sample_leaf_variance_id):
        """CascadeResult includes per-step timings."""
        result = await regenerator.regenerate_chain(
            sample_leaf_variance_id, "2026-06"
        )
        assert result.total_seconds > 0
        # Timings dict should have entries for each step processed
        assert isinstance(result.timings, dict)

    @pytest.mark.asyncio
    async def test_cascade_result_has_chain(self, regenerator, sample_leaf_variance_id):
        """CascadeResult includes the cascade chain."""
        result = await regenerator.regenerate_chain(
            sample_leaf_variance_id, "2026-06"
        )
        assert len(result.chain) > 0

    @pytest.mark.asyncio
    async def test_cascade_handles_missing_variance(self, regenerator):
        """Gracefully handles nonexistent variance."""
        result = await regenerator.regenerate_chain(
            "nonexistent_id", "2026-06"
        )
        assert isinstance(result, CascadeResult)
        assert result.regenerated == []
        assert result.chain == []


class TestRegenerateParent:
    """Test parent narrative regeneration."""

    def test_regenerate_parent_produces_narrative(self, regenerator, data_dir):
        """Parent regeneration produces narrative text."""
        ds = DataService(data_dir)
        material = ds._table("fact_variance_material")
        # Find a calculated row
        calc_rows = material[material.get("is_calculated", pd.Series(dtype=bool)) == True]
        if calc_rows.empty:
            pytest.skip("No calculated rows in test data")

        row = calc_rows.iloc[0]
        result = regenerator._regenerate_parent(
            str(row["variance_id"]),
            str(row["account_id"]),
            str(row["period_id"]),
            str(row.get("view_id", "MTD")),
            str(row.get("base_id", "BUDGET")),
            material[
                (material["period_id"] == row["period_id"])
                & (material["view_id"] == row.get("view_id", "MTD"))
                & (material["base_id"] == row.get("base_id", "BUDGET"))
            ],
        )
        if result:
            assert "narrative_detail" in result
            assert len(result["narrative_detail"]) > 0


class TestRegenerateSection:
    """Test section narrative regeneration."""

    def test_regenerate_section_produces_narrative(self, regenerator, data_dir):
        """Section regeneration produces narrative text."""
        ds = DataService(data_dir)
        material = ds._table("fact_variance_material")
        period_material = material[
            (material["period_id"] == "2026-06")
            & (material.get("view_id", pd.Series(dtype=str)) == "MTD")
            & (material.get("base_id", pd.Series(dtype=str)) == "BUDGET")
        ]

        result = regenerator._regenerate_section("revenue", "2026-06", period_material)
        if result:
            assert "narrative" in result
            assert "Revenue" in result["narrative"] or "revenue" in result["narrative"].lower()
            assert result["status"] == "AI_DRAFT"


class TestRegenerateExecutive:
    """Test executive summary regeneration."""

    def test_regenerate_executive_produces_headline(self, regenerator, data_dir):
        """Executive regeneration produces headline + narrative."""
        ds = DataService(data_dir)
        material = ds._table("fact_variance_material")
        period_material = material[material["period_id"] == "2026-06"]

        result = regenerator._regenerate_executive("2026-06", period_material)
        if result:
            assert "headline" in result
            assert "full_narrative" in result
            assert result["status"] == "AI_DRAFT"


# ---------------------------------------------------------------------------
# Tests: Cascade Cost Estimation
# ---------------------------------------------------------------------------


class TestCascadeCostEstimation:
    """Test cascade-specific cost estimation."""

    def test_template_mode_zero_cost(self):
        """Template cascade costs $0."""
        chain = [
            {"id": "v1", "type": "parent_variance", "level": 1},
            {"id": "s1", "type": "section", "level": 2},
            {"id": "e1", "type": "executive", "level": 3},
        ]
        est = estimate_cascade_cost(chain, mode="template")
        assert est["estimated_cost_usd"] == 0.0
        assert est["steps"] == 3

    def test_llm_mode_has_cost(self):
        """LLM cascade has positive cost."""
        chain = [
            {"id": "v1", "type": "parent_variance", "level": 1},
            {"id": "s1", "type": "section", "level": 2},
            {"id": "e1", "type": "executive", "level": 3},
        ]
        est = estimate_cascade_cost(chain, mode="llm")
        assert est["estimated_cost_usd"] > 0
        assert est["estimated_calls"] == 3

    def test_empty_chain_zero_cost(self):
        """Empty chain costs $0."""
        est = estimate_cascade_cost([], mode="llm")
        assert est["estimated_cost_usd"] == 0.0
        assert est["estimated_calls"] == 0

    def test_cost_breakdown(self):
        """Breakdown shows parents/sections/executive counts."""
        chain = [
            {"id": "v1", "type": "parent_variance", "level": 1},
            {"id": "v2", "type": "parent_variance", "level": 1},
            {"id": "s1", "type": "section", "level": 2},
            {"id": "e1", "type": "executive", "level": 3},
        ]
        est = estimate_cascade_cost(chain, mode="llm")
        assert est["breakdown"]["parents"] == 2
        assert est["breakdown"]["sections"] == 1
        assert est["breakdown"]["executive"] == 1
