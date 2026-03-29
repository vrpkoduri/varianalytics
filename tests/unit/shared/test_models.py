"""Unit tests for shared.models — Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from shared.models.dimensions import (
    DimAccount,
    DimBusinessUnit,
    DimComparisonBase,
    DimHierarchy,
    DimPeriod,
    DimView,
)
from shared.models.enums import (
    ComparisonBase,
    PLCategory,
    ReviewStatus,
    VarianceSign,
    ViewType,
)
from shared.models.facts import FactFinancials, FactVarianceMaterial


@pytest.mark.unit
class TestDimHierarchy:
    """Tests for dimension hierarchy schema."""

    def test_valid_hierarchy_node(self) -> None:
        node = DimHierarchy(
            node_id="geo_us",
            node_name="United States",
            dimension_name="Geography",
            parent_id="geo_na",
            depth=3,
            is_leaf=False,
            rollup_path="geo_global/geo_americas/geo_na/geo_us",
            sort_order=1,
        )
        assert node.node_id == "geo_us"
        assert node.is_leaf is False

    def test_root_node_null_parent(self) -> None:
        node = DimHierarchy(
            node_id="geo_global",
            node_name="Global",
            dimension_name="Geography",
            parent_id=None,
            depth=0,
            is_leaf=False,
            rollup_path="geo_global",
        )
        assert node.parent_id is None


@pytest.mark.unit
class TestDimAccount:
    """Tests for account dimension schema."""

    def test_detail_account(self) -> None:
        acct = DimAccount(
            account_id="acct_advisory_fees",
            account_name="Advisory & Brokerage Fees",
            parent_id="acct_revenue",
            depth=2,
            is_leaf=True,
            is_calculated=False,
            pl_category=PLCategory.REVENUE,
            variance_sign=VarianceSign.NATURAL,
            rollup_path="acct_total_pl/acct_revenue/acct_advisory_fees",
        )
        assert acct.is_calculated is False
        assert acct.pl_category == PLCategory.REVENUE

    def test_calculated_row(self) -> None:
        acct = DimAccount(
            account_id="acct_ebitda",
            account_name="EBITDA",
            depth=1,
            is_leaf=False,
            is_calculated=True,
            calc_formula="acct_gross_profit - acct_total_opex + acct_da",
            calc_dependencies=["acct_gross_profit", "acct_total_opex", "acct_da"],
            rollup_path="acct_total_pl/acct_ebitda",
        )
        assert acct.is_calculated is True
        assert len(acct.calc_dependencies) == 3


@pytest.mark.unit
class TestFactFinancials:
    """Tests for base fact table schema."""

    def test_valid_record(self) -> None:
        fact = FactFinancials(
            period_id="2026-06",
            bu_id="marsh",
            account_id="acct_advisory_fees",
            geo_node_id="geo_us_ne",
            segment_node_id="seg_large_corp",
            lob_node_id="lob_pc",
            costcenter_node_id="cc_new_biz",
            fiscal_year=2026,
            actual_amount=500000.0,
            budget_amount=480000.0,
        )
        assert fact.actual_amount == 500000.0
        assert fact.forecast_amount is None  # Optional
        assert fact.prior_year_amount is None

    def test_zero_budget_allowed(self) -> None:
        """Budget=0 is valid — variance pct will be NULL."""
        fact = FactFinancials(
            period_id="2026-06",
            bu_id="marsh",
            account_id="acct_other_revenue",
            geo_node_id="geo_us_ne",
            segment_node_id="seg_large_corp",
            lob_node_id="lob_pc",
            costcenter_node_id="cc_new_biz",
            fiscal_year=2026,
            actual_amount=10000.0,
            budget_amount=0.0,
        )
        assert fact.budget_amount == 0.0


@pytest.mark.unit
class TestEnums:
    """Tests for shared enums."""

    def test_review_status_values(self) -> None:
        assert ReviewStatus.AI_DRAFT.value == "AI_DRAFT"
        assert ReviewStatus.APPROVED.value == "APPROVED"

    def test_view_type_values(self) -> None:
        assert len(ViewType) == 3
        assert ViewType.MTD in ViewType

    def test_comparison_base_values(self) -> None:
        assert len(ComparisonBase) == 3
        assert ComparisonBase.BUDGET.value == "BUDGET"
