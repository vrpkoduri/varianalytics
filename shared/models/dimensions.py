"""Pydantic schemas for dimension tables."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from shared.models.enums import ComparisonBase, PLCategory, VarianceSign, ViewType


class DimHierarchy(BaseModel):
    """Parent-child hierarchy for Geo, Segment, LOB, CostCenter dimensions.

    Supports ragged hierarchies with materialized rollup paths.
    """

    node_id: str = Field(..., description="Unique node identifier")
    node_name: str = Field(..., description="Display name")
    dimension_name: str = Field(..., description="Geo, Segment, LOB, or CostCenter")
    parent_id: Optional[str] = Field(None, description="Parent node ID (NULL for root)")
    depth: int = Field(..., description="Depth in tree (root=0)")
    is_leaf: bool = Field(..., description="True if no children")
    rollup_path: str = Field(
        ..., description="Materialized path, e.g. 'geo_global/geo_americas/geo_na/geo_us'"
    )
    sort_order: int = Field(0, description="Display sort order within parent")


class DimBusinessUnit(BaseModel):
    """Flat business unit dimension."""

    bu_id: str = Field(..., description="Business unit identifier")
    bu_name: str = Field(..., description="Display name")
    sort_order: int = Field(0, description="Display sort order")


class DimAccount(BaseModel):
    """P&L chart of accounts with parent-child hierarchy and calculated row support.

    Calculated rows (EBITDA, Gross Profit, etc.) are resolved AFTER bottom-up rollup
    in dependency order via calc_dependencies.
    """

    account_id: str = Field(..., description="Unique account identifier")
    account_name: str = Field(..., description="Display name")
    parent_id: Optional[str] = Field(None, description="Parent account ID")
    depth: int = Field(..., description="Depth in account tree (root=0)")
    is_leaf: bool = Field(..., description="True if no children (detail account)")
    is_calculated: bool = Field(False, description="True if computed from formula")
    calc_formula: Optional[str] = Field(
        None, description="Formula string, e.g. 'acct_gross_revenue - acct_total_cor'"
    )
    calc_dependencies: Optional[list[str]] = Field(
        None, description="Account IDs this calc depends on, for dependency ordering"
    )
    pl_category: Optional[PLCategory] = Field(None, description="Revenue, COGS, OpEx, NonOp, Tax")
    variance_sign: Optional[VarianceSign] = Field(
        None, description="natural (revenue) or inverse (costs)"
    )
    rollup_path: str = Field(..., description="Materialized path in account tree")
    sort_order: int = Field(0, description="Display sort order (P&L template ordering)")


class DimPeriod(BaseModel):
    """Time period dimension — 36 months."""

    period_id: str = Field(..., description="YYYY-MM format")
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_quarter: int = Field(..., description="1-4")
    fiscal_month: int = Field(..., description="1-12")
    period_start: date = Field(..., description="First day of month")
    period_end: date = Field(..., description="Last day of month")
    is_closed: bool = Field(False, description="True if period is closed")
    is_current: bool = Field(False, description="True if this is the current analysis period")


class DimView(BaseModel):
    """Time aggregation view dimension."""

    view_id: str = Field(..., description="MTD, QTD, or YTD")
    view_name: str = Field(..., description="Display name")
    view_type: ViewType = Field(..., description="View type enum")


class DimComparisonBase(BaseModel):
    """Comparison base dimension."""

    base_id: str = Field(..., description="BUDGET, FORECAST, or PRIOR_YEAR")
    base_name: str = Field(..., description="Display name")
    base_type: ComparisonBase = Field(..., description="Comparison base enum")
