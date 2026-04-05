"""Dimension lookup endpoints.

Exposes cached hierarchy trees, business units, accounts, and fiscal periods
for use by the frontend filter panel and the chat agent's context resolution.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from shared.auth.middleware import UserContext, get_current_user

router = APIRouter(prefix="/dimensions", tags=["dimensions"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class HierarchyNode(BaseModel):
    """Single node in a ragged parent-child hierarchy."""

    node_id: str
    name: str
    parent_id: Optional[str] = None
    level: int
    rollup_path: str = Field("", description="Materialised path e.g. /NA/US/West")
    children: list["HierarchyNode"] = Field(default_factory=list)


class HierarchyResponse(BaseModel):
    """Full hierarchy tree for a dimension."""

    dimension_name: str
    roots: list[HierarchyNode] = Field(default_factory=list)


class BusinessUnit(BaseModel):
    """Flat business-unit record."""

    bu_id: str
    name: str
    region: str


class Account(BaseModel):
    """Account dimension record."""

    account_id: str
    name: str
    parent_id: Optional[str] = None
    is_calculated: bool = False
    pl_category: Optional[str] = None


class Period(BaseModel):
    """Fiscal period record."""

    period_id: str
    label: str
    fiscal_year: int
    fiscal_quarter: int
    fiscal_month: int
    is_closed: bool
    has_data: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/hierarchies/{dimension_name}",
    response_model=HierarchyResponse,
    summary="Get hierarchy tree for a dimension",
)
async def get_hierarchy(
    dimension_name: str,
    request: Request,
    user: UserContext = Depends(get_current_user),
) -> HierarchyResponse:
    """Return the full parent-child tree for the given dimension.

    Supported dimensions: geography, segment, lob, costcenter.
    """
    ds = request.app.state.data_service
    tree = ds.get_dimension_hierarchy(dimension_name)

    def _convert(node: dict) -> HierarchyNode:
        return HierarchyNode(
            node_id=node.get("node_id", ""),
            name=node.get("name", ""),
            parent_id=node.get("parent_id"),
            level=node.get("level", 0),
            rollup_path=node.get("rollup_path", ""),
            children=[_convert(c) for c in node.get("children", [])],
        )

    roots = [_convert(r) for r in tree] if tree else []
    return HierarchyResponse(dimension_name=dimension_name, roots=roots)


@router.get(
    "/business-units",
    response_model=list[BusinessUnit],
    summary="List all business units",
)
async def list_business_units(
    request: Request,
    user: UserContext = Depends(get_current_user),
) -> list[BusinessUnit]:
    """Return flat list of business units."""
    ds = request.app.state.data_service
    bus = ds.get_business_units()
    return [
        BusinessUnit(
            bu_id=bu["bu_id"],
            name=bu.get("bu_name", bu.get("name", "")),
            region=bu.get("region", ""),
        )
        for bu in bus
    ]


@router.get(
    "/accounts",
    response_model=list[Account],
    summary="List all accounts",
)
async def list_accounts(
    request: Request,
    user: UserContext = Depends(get_current_user),
) -> list[Account]:
    """Return account dimension with parent-child relationships."""
    ds = request.app.state.data_service
    accounts = ds.get_accounts()
    return [
        Account(
            account_id=a["account_id"],
            name=a.get("account_name", ""),
            parent_id=a.get("parent_id"),
            is_calculated=a.get("is_calculated", False),
            pl_category=a.get("pl_category"),
        )
        for a in accounts
    ]


@router.get(
    "/periods",
    response_model=list[Period],
    summary="List fiscal periods",
)
async def list_periods(
    request: Request,
    user: UserContext = Depends(get_current_user),
) -> list[Period]:
    """Return available fiscal periods."""
    ds = request.app.state.data_service
    periods = ds.get_periods()
    return [
        Period(
            period_id=p["period_id"],
            label=p.get("period_label", p["period_id"]),
            fiscal_year=int(p.get("fiscal_year", 0)),
            fiscal_quarter=int(p.get("fiscal_quarter", 0)),
            fiscal_month=int(p.get("fiscal_month", 0)),
            is_closed=bool(p.get("is_closed", False)),
            has_data=bool(p.get("has_data", False)),
        )
        for p in periods
    ]
