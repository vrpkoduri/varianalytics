"""Shared test fixtures for the variance agent test suite.

Provides reusable fixtures for:
- Sample hierarchy trees (Geo, Account)
- Sample fact data
- Test configuration
"""

import json
from pathlib import Path

import pytest

from shared.hierarchy.tree import HierarchyNode, build_tree_from_dict


@pytest.fixture
def sample_geo_tree_data() -> dict:
    """Minimal geography hierarchy for testing."""
    return {
        "node_id": "geo_global",
        "node_name": "Global",
        "children": [
            {
                "node_id": "geo_americas",
                "node_name": "Americas",
                "children": [
                    {
                        "node_id": "geo_us",
                        "node_name": "United States",
                        "children": [
                            {"node_id": "geo_us_ne", "node_name": "US Northeast", "children": []},
                            {"node_id": "geo_us_se", "node_name": "US Southeast", "children": []},
                        ],
                    },
                    {"node_id": "geo_canada", "node_name": "Canada", "children": []},
                ],
            },
            {
                "node_id": "geo_emea",
                "node_name": "EMEA",
                "children": [
                    {"node_id": "geo_uk_ireland", "node_name": "UK & Ireland", "children": []},
                ],
            },
        ],
    }


@pytest.fixture
def sample_geo_tree(sample_geo_tree_data: dict) -> HierarchyNode:
    """Build a HierarchyNode tree from sample geo data."""
    return build_tree_from_dict(sample_geo_tree_data)


@pytest.fixture
def sample_account_tree_data() -> dict:
    """Minimal account hierarchy for testing calculated rows."""
    return {
        "node_id": "acct_total_pl",
        "node_name": "Total P&L",
        "is_calculated": True,
        "children": [
            {
                "node_id": "acct_revenue",
                "node_name": "Revenue",
                "pl_category": "Revenue",
                "variance_sign": "natural",
                "is_calculated": False,
                "children": [
                    {
                        "node_id": "acct_advisory_fees",
                        "node_name": "Advisory Fees",
                        "pl_category": "Revenue",
                        "variance_sign": "natural",
                        "is_calculated": False,
                        "children": [],
                    },
                    {
                        "node_id": "acct_consulting_fees",
                        "node_name": "Consulting Fees",
                        "pl_category": "Revenue",
                        "variance_sign": "natural",
                        "is_calculated": False,
                        "children": [],
                    },
                ],
            },
            {
                "node_id": "acct_gross_revenue",
                "node_name": "Gross Revenue",
                "is_calculated": True,
                "calc_formula": "SUM(acct_revenue.children)",
                "children": [],
            },
        ],
    }


@pytest.fixture
def sample_account_tree(sample_account_tree_data: dict) -> HierarchyNode:
    """Build a HierarchyNode tree from sample account data."""
    return build_tree_from_dict(sample_account_tree_data)


@pytest.fixture
def synthetic_data_spec_path() -> Path:
    """Path to the synthetic data spec file."""
    return Path(__file__).parent.parent / "docs" / "synthetic-data-spec.json"


@pytest.fixture
def synthetic_data_spec(synthetic_data_spec_path: Path) -> dict:
    """Load the synthetic data spec."""
    with open(synthetic_data_spec_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Hierarchy Cache Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def hierarchy_cache() -> "HierarchyCache":
    """Empty HierarchyCache instance."""
    from shared.hierarchy.cache import HierarchyCache
    return HierarchyCache()


@pytest.fixture
def loaded_hierarchy_cache(
    hierarchy_cache: "HierarchyCache",
    sample_geo_tree_data: dict,
    sample_account_tree_data: dict,
) -> "HierarchyCache":
    """Pre-loaded cache with Geography and Account dimensions."""
    hierarchy_cache.load_dimension("Geography", sample_geo_tree_data)
    hierarchy_cache.load_dimension("Account", sample_account_tree_data)
    return hierarchy_cache


# ---------------------------------------------------------------------------
# Full Spec Hierarchy Fixtures (for synthetic data generator tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def full_geo_tree(synthetic_data_spec: dict) -> "HierarchyNode":
    """Full geography hierarchy from spec (26 nodes)."""
    from shared.hierarchy.tree import build_tree_from_dict
    return build_tree_from_dict(synthetic_data_spec["geography_hierarchy"]["tree"])


@pytest.fixture
def full_account_tree(synthetic_data_spec: dict) -> "HierarchyNode":
    """Full account hierarchy from spec (36 nodes)."""
    from shared.hierarchy.tree import build_tree_from_dict
    return build_tree_from_dict(synthetic_data_spec["account_hierarchy"]["tree"])
