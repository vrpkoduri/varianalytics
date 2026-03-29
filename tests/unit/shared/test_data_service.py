"""Tests for the DataService — centralized data access layer.

Uses actual parquet data from data/output/.
"""

import math
import shutil

import pytest

from shared.data.service import DataService


@pytest.fixture(scope="module")
def svc() -> DataService:
    """DataService loaded from actual parquet data."""
    DataService.reset_instance()
    return DataService(data_dir="data/output")


def _latest_period(svc: DataService) -> str:
    """Return a period_id that has variance data.

    fact_variance_material may not cover all dim_period rows,
    so pick the latest period that actually has variance rows.
    """
    vm = svc._table("fact_variance_material")
    if vm.empty:
        periods = svc.get_periods()
        return periods[-1]["period_id"]
    return vm["period_id"].max()


# ------------------------------------------------------------------
# Summary Cards
# ------------------------------------------------------------------


@pytest.mark.unit
class TestSummaryCards:
    def test_summary_cards_returns_7_metrics(self, svc: DataService) -> None:
        period = _latest_period(svc)
        cards = svc.get_summary_cards(period)
        assert len(cards) == 7
        names = [c["metric_name"] for c in cards]
        assert "Total Revenue" in names
        assert "Total COGS" in names
        assert "Gross Profit" in names
        assert "Total OpEx" in names
        assert "EBITDA" in names
        assert "Operating Income" in names
        assert "Net Income" in names

    def test_summary_cards_filter_by_bu(self, svc: DataService) -> None:
        period = _latest_period(svc)
        all_cards = svc.get_summary_cards(period)
        bu_cards = svc.get_summary_cards(period, bu_id="marsh")
        assert len(bu_cards) == 7
        # BU-filtered revenue should be smaller than total
        all_rev = next(c for c in all_cards if c["metric_name"] == "Total Revenue")
        bu_rev = next(c for c in bu_cards if c["metric_name"] == "Total Revenue")
        assert abs(bu_rev["actual"]) < abs(all_rev["actual"])

    def test_summary_cards_have_required_fields(self, svc: DataService) -> None:
        period = _latest_period(svc)
        cards = svc.get_summary_cards(period)
        for card in cards:
            assert "metric_name" in card
            assert "actual" in card
            assert "comparator" in card
            assert "variance_amount" in card
            assert "variance_pct" in card
            assert "is_favorable" in card
            assert "is_material" in card

    def test_summary_cards_empty_period(self, svc: DataService) -> None:
        cards = svc.get_summary_cards("9999-12")
        assert cards == []


# ------------------------------------------------------------------
# Waterfall
# ------------------------------------------------------------------


@pytest.mark.unit
class TestWaterfall:
    def test_waterfall_starts_with_budget_ends_with_actual(self, svc: DataService) -> None:
        period = _latest_period(svc)
        steps = svc.get_waterfall(period)
        assert len(steps) >= 3
        assert steps[0]["name"] == "Budget"
        assert steps[0]["is_total"] is True
        assert steps[-1]["name"] == "Actual"
        assert steps[-1]["is_total"] is True

    def test_waterfall_steps_sum_to_total(self, svc: DataService) -> None:
        period = _latest_period(svc)
        steps = svc.get_waterfall(period)
        budget = steps[0]["value"]
        actual = steps[-1]["value"]
        variance_sum = sum(s["value"] for s in steps[1:-1])
        assert abs((budget + variance_sum) - actual) < 0.02  # rounding tolerance

    def test_waterfall_has_bu_steps(self, svc: DataService) -> None:
        period = _latest_period(svc)
        steps = svc.get_waterfall(period)
        # Middle steps (not first or last) are BU variances
        bu_steps = [s for s in steps if not s["is_total"]]
        assert len(bu_steps) == 5  # 5 BUs


# ------------------------------------------------------------------
# Heatmap
# ------------------------------------------------------------------


@pytest.mark.unit
class TestHeatmap:
    def test_heatmap_has_5_bu_columns(self, svc: DataService) -> None:
        period = _latest_period(svc)
        heatmap = svc.get_heatmap(period)
        assert len(heatmap["columns"]) == 5

    def test_heatmap_has_rows_and_cells(self, svc: DataService) -> None:
        period = _latest_period(svc)
        heatmap = svc.get_heatmap(period)
        assert len(heatmap["rows"]) > 0
        assert len(heatmap["cells"]) == len(heatmap["rows"])
        for row_cells in heatmap["cells"]:
            assert len(row_cells) == len(heatmap["columns"])

    def test_heatmap_cell_structure(self, svc: DataService) -> None:
        period = _latest_period(svc)
        heatmap = svc.get_heatmap(period)
        cell = heatmap["cells"][0][0]
        assert "value" in cell
        assert "pct" in cell
        assert "is_material" in cell


# ------------------------------------------------------------------
# Trends
# ------------------------------------------------------------------


@pytest.mark.unit
class TestTrends:
    def test_trends_returns_requested_periods(self, svc: DataService) -> None:
        result = svc.get_trends(periods=6)
        assert len(result) <= 6
        assert len(result) > 0

    def test_trends_sorted_by_period(self, svc: DataService) -> None:
        result = svc.get_trends(periods=12)
        period_ids = [r["period_id"] for r in result]
        assert period_ids == sorted(period_ids)

    def test_trends_have_required_fields(self, svc: DataService) -> None:
        result = svc.get_trends(periods=3)
        for item in result:
            assert "period_id" in item
            assert "actual" in item
            assert "comparator" in item
            assert "variance_amount" in item
            assert "variance_pct" in item


# ------------------------------------------------------------------
# Variance List
# ------------------------------------------------------------------


@pytest.mark.unit
class TestVarianceList:
    def test_variance_list_pagination(self, svc: DataService) -> None:
        period = _latest_period(svc)
        result = svc.get_variance_list(period, page=1, page_size=5)
        assert result["page"] == 1
        assert result["page_size"] == 5
        assert len(result["items"]) <= 5
        assert result["total_count"] > 0
        assert result["total_pages"] == math.ceil(result["total_count"] / 5)

    def test_variance_list_sort_by_amount(self, svc: DataService) -> None:
        period = _latest_period(svc)
        result = svc.get_variance_list(period, page=1, page_size=10, sort_by="variance_amount", sort_desc=True)
        items = result["items"]
        if len(items) >= 2:
            amounts = [abs(i["variance_amount"]) for i in items]
            assert amounts == sorted(amounts, reverse=True)

    def test_variance_list_filter_by_category(self, svc: DataService) -> None:
        period = _latest_period(svc)
        result = svc.get_variance_list(period, pl_category="Revenue")
        for item in result["items"]:
            assert item["pl_category"] == "Revenue"

    def test_variance_list_item_structure(self, svc: DataService) -> None:
        period = _latest_period(svc)
        result = svc.get_variance_list(period, page_size=1)
        if result["items"]:
            item = result["items"][0]
            assert "variance_id" in item
            assert "account_id" in item
            assert "account_name" in item
            assert "bu_id" in item
            assert "variance_amount" in item
            assert "narrative_oneliner" in item


# ------------------------------------------------------------------
# Variance Detail
# ------------------------------------------------------------------


@pytest.mark.unit
class TestVarianceDetail:
    def test_variance_detail_includes_decomposition(self, svc: DataService) -> None:
        # Get a variance_id that has decomposition
        period = _latest_period(svc)
        vlist = svc.get_variance_list(period, page_size=50)
        # Find one with decomposition by trying each
        found = False
        for item in vlist["items"]:
            detail = svc.get_variance_detail(item["variance_id"])
            if detail and detail["decomposition"] is not None:
                assert "method" in detail["decomposition"]
                assert "components" in detail["decomposition"]
                assert "total_explained" in detail["decomposition"]
                found = True
                break
        assert found, "No variance with decomposition found"

    def test_variance_detail_has_narratives(self, svc: DataService) -> None:
        period = _latest_period(svc)
        vlist = svc.get_variance_list(period, page_size=1)
        if vlist["items"]:
            detail = svc.get_variance_detail(vlist["items"][0]["variance_id"])
            assert detail is not None
            assert "narratives" in detail
            assert "detail" in detail["narratives"]
            assert "oneliner" in detail["narratives"]

    def test_variance_detail_not_found(self, svc: DataService) -> None:
        result = svc.get_variance_detail("nonexistent-id")
        assert result is None


# ------------------------------------------------------------------
# P&L Statement
# ------------------------------------------------------------------


@pytest.mark.unit
class TestPLStatement:
    def test_pl_statement_has_root_node(self, svc: DataService) -> None:
        period = _latest_period(svc)
        pl = svc.get_pl_statement(period)
        assert len(pl) == 1
        root = pl[0]
        assert root["account_id"] == "acct_total_pl"
        assert root["account_name"] == "Total P&L"
        assert root["depth"] == 0

    def test_pl_statement_calculated_rows_present(self, svc: DataService) -> None:
        period = _latest_period(svc)
        pl = svc.get_pl_statement(period)
        root = pl[0]

        # Collect all account_ids in the tree
        def _collect_ids(node: dict) -> list[str]:
            ids = [node["account_id"]]
            for child in node.get("children", []):
                ids.extend(_collect_ids(child))
            return ids

        all_ids = _collect_ids(root)
        # These calculated rows should be present
        for calc_id in ["acct_gross_profit", "acct_ebitda", "acct_net_income"]:
            assert calc_id in all_ids, f"{calc_id} missing from P&L tree"

    def test_pl_statement_children_have_structure(self, svc: DataService) -> None:
        period = _latest_period(svc)
        pl = svc.get_pl_statement(period)
        root = pl[0]
        assert len(root["children"]) > 0
        child = root["children"][0]
        assert "account_id" in child
        assert "actual" in child
        assert "comparator" in child
        assert "variance_amount" in child
        assert "children" in child


# ------------------------------------------------------------------
# Dimension Lookups
# ------------------------------------------------------------------


@pytest.mark.unit
class TestDimensionLookups:
    def test_get_business_units_returns_5(self, svc: DataService) -> None:
        bus = svc.get_business_units()
        assert len(bus) == 5

    def test_get_periods_returns_36(self, svc: DataService) -> None:
        periods = svc.get_periods()
        assert len(periods) == 36

    def test_get_accounts_returns_38(self, svc: DataService) -> None:
        accounts = svc.get_accounts()
        assert len(accounts) == 38

    def test_get_dimension_hierarchy_geography(self, svc: DataService) -> None:
        tree = svc.get_dimension_hierarchy("Geography")
        assert len(tree) == 1
        root = tree[0]
        assert root["node_id"] == "geo_global"
        assert len(root["children"]) > 0

    def test_get_dimension_hierarchy_unknown(self, svc: DataService) -> None:
        tree = svc.get_dimension_hierarchy("Nonexistent")
        assert tree == []

    def test_business_unit_has_fields(self, svc: DataService) -> None:
        bus = svc.get_business_units()
        bu = bus[0]
        assert "bu_id" in bu
        assert "bu_name" in bu

    def test_period_has_fields(self, svc: DataService) -> None:
        periods = svc.get_periods()
        p = periods[0]
        assert "period_id" in p
        assert "fiscal_year" in p


# ------------------------------------------------------------------
# Corrupted / missing file resilience
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dataservice_survives_missing_table(tmp_path):
    """DataService starts with empty table if parquet file is corrupted or missing."""
    # Copy actual data directory
    shutil.copytree("data/output", tmp_path / "output")

    # Corrupt one file
    corrupt_path = tmp_path / "output" / "fact_netting_flags.parquet"
    corrupt_path.write_bytes(b"this is not a parquet file")

    # DataService should still init, with netting flags as empty DataFrame
    DataService.reset_instance()
    ds = DataService(data_dir=str(tmp_path / "output"))

    # The corrupted table should be empty, not crash
    netting = ds._table("fact_netting_flags")
    assert netting.empty

    # Other tables should be fine
    assert len(ds.get_business_units()) == 5
