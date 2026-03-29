"""Cross-table referential integrity tests.

Validates that foreign key relationships, grain uniqueness, and
hierarchy parent-child links are consistent across all data tables.
"""

import pandas as pd
import pytest

DATA_DIR = "data/output"


@pytest.fixture(scope="module")
def ff():
    return pd.read_parquet(f"{DATA_DIR}/fact_financials.parquet")


@pytest.fixture(scope="module")
def vm():
    return pd.read_parquet(f"{DATA_DIR}/fact_variance_material.parquet")


@pytest.fixture(scope="module")
def dim_account():
    return pd.read_parquet(f"{DATA_DIR}/dim_account.parquet")


@pytest.fixture(scope="module")
def dim_period():
    return pd.read_parquet(f"{DATA_DIR}/dim_period.parquet")


@pytest.fixture(scope="module")
def dim_bu():
    return pd.read_parquet(f"{DATA_DIR}/dim_business_unit.parquet")


@pytest.fixture(scope="module")
def dim_hierarchy():
    return pd.read_parquet(f"{DATA_DIR}/dim_hierarchy.parquet")


# ---------------------------------------------------------------------------
# Foreign key referential integrity
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestForeignKeyIntegrity:
    """Tests that fact table foreign keys reference valid dimension records."""

    def test_ff_account_ids_in_dim_account(
        self, ff: pd.DataFrame, dim_account: pd.DataFrame,
    ) -> None:
        """All account_ids in fact_financials exist in dim_account."""
        ff_accounts = set(ff["account_id"].unique())
        dim_accounts = set(dim_account["account_id"].unique())
        missing = ff_accounts - dim_accounts
        assert len(missing) == 0, f"Account IDs in ff not in dim_account: {missing}"

    def test_ff_period_ids_in_dim_period(
        self, ff: pd.DataFrame, dim_period: pd.DataFrame,
    ) -> None:
        """All period_ids in fact_financials exist in dim_period."""
        ff_periods = set(ff["period_id"].unique())
        dim_periods = set(dim_period["period_id"].unique())
        missing = ff_periods - dim_periods
        assert len(missing) == 0, f"Period IDs in ff not in dim_period: {missing}"

    def test_ff_bu_ids_in_dim_bu(
        self, ff: pd.DataFrame, dim_bu: pd.DataFrame,
    ) -> None:
        """All bu_ids in fact_financials exist in dim_business_unit."""
        ff_bus = set(ff["bu_id"].unique())
        dim_bus = set(dim_bu["bu_id"].unique())
        missing = ff_bus - dim_bus
        assert len(missing) == 0, f"BU IDs in ff not in dim_bu: {missing}"

    def test_ff_only_leaf_accounts(
        self, ff: pd.DataFrame, dim_account: pd.DataFrame,
    ) -> None:
        """Fact_financials should only contain leaf (detail) accounts."""
        leaf_accounts = set(
            dim_account[dim_account["is_leaf"] == True]["account_id"]  # noqa: E712
        )
        ff_accounts = set(ff["account_id"].unique())
        non_leaf = ff_accounts - leaf_accounts
        assert len(non_leaf) == 0, (
            f"Fact_financials contains non-leaf accounts: {non_leaf}"
        )


# ---------------------------------------------------------------------------
# Grain uniqueness
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGrainUniqueness:
    """Tests that fact tables have unique grain and IDs."""

    def test_ff_grain_unique(self, ff: pd.DataFrame) -> None:
        """No duplicate (period_id, bu_id, costcenter_node_id, account_id) in ff."""
        grain_cols = ["period_id", "bu_id", "costcenter_node_id", "account_id"]
        dupes = ff.duplicated(subset=grain_cols, keep=False).sum()
        assert dupes == 0, f"Found {dupes} duplicate rows on grain columns"

    def test_vm_variance_ids_unique(self, vm: pd.DataFrame) -> None:
        """variance_id column in fact_variance_material has no duplicates."""
        dupes = vm["variance_id"].duplicated().sum()
        assert dupes == 0, f"Found {dupes} duplicate variance_ids"


# ---------------------------------------------------------------------------
# Hierarchy parent-child validity
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestHierarchyIntegrity:
    """Tests that parent-child relationships in dimensions are valid."""

    def test_dim_account_parent_ids_valid(self, dim_account: pd.DataFrame) -> None:
        """Every non-null parent_id in dim_account references a valid account_id."""
        all_ids = set(dim_account["account_id"])
        with_parent = dim_account[dim_account["parent_id"].notna()]
        invalid = set(with_parent["parent_id"]) - all_ids
        assert len(invalid) == 0, f"Invalid parent_ids in dim_account: {invalid}"

    def test_dim_hierarchy_parent_ids_valid(self, dim_hierarchy: pd.DataFrame) -> None:
        """Every non-null parent_id in dim_hierarchy references a valid node_id."""
        all_ids = set(dim_hierarchy["node_id"])
        with_parent = dim_hierarchy[dim_hierarchy["parent_id"].notna()]
        invalid = set(with_parent["parent_id"]) - all_ids
        assert len(invalid) == 0, f"Invalid parent_ids in dim_hierarchy: {invalid}"

    def test_dim_account_no_circular_deps(self, dim_account: pd.DataFrame) -> None:
        """Account calc_dependencies graph has no cycles (DFS cycle detection)."""
        # Build adjacency from calc_dependencies
        dep_graph: dict[str, list[str]] = {}
        for _, row in dim_account.iterrows():
            aid = row["account_id"]
            deps = row.get("calc_dependencies")
            if pd.notna(deps) and deps:
                # calc_dependencies is stored as a string like "acct_a,acct_b"
                if isinstance(deps, str):
                    dep_graph[aid] = [d.strip() for d in deps.split(",") if d.strip()]
                elif isinstance(deps, list):
                    dep_graph[aid] = deps

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {aid: WHITE for aid in dim_account["account_id"]}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in dep_graph.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    return True  # cycle found
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        has_cycle = False
        for node in dim_account["account_id"]:
            if color[node] == WHITE:
                if dfs(node):
                    has_cycle = True
                    break

        assert not has_cycle, "Circular dependency detected in dim_account calc_dependencies"


# ---------------------------------------------------------------------------
# Org mapping determinism
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestOrgMappingDeterminism:
    """Tests that org unit mapping is deterministic."""

    def test_org_mapping_deterministic(self, ff: pd.DataFrame) -> None:
        """Each (bu_id, costcenter_node_id) maps to exactly one (geo, segment, lob)."""
        mapping = ff.groupby(["bu_id", "costcenter_node_id"])[
            ["geo_node_id", "segment_node_id", "lob_node_id"]
        ].nunique()
        multi = mapping[(mapping > 1).any(axis=1)]
        assert len(multi) == 0, (
            f"BU+CC combos with multiple geo/segment/lob mappings:\n{multi}"
        )
