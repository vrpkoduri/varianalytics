"""Dimension lookup endpoints.

Exposes cached hierarchy trees, business units, accounts, and fiscal periods
for use by the frontend filter panel and the chat agent's context resolution.
"""

from typing import Any, Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

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
    sign_convention: int = 1


class Period(BaseModel):
    """Fiscal period record."""

    period_id: str
    label: str
    fiscal_year: int
    fiscal_month: int
    is_closed: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/hierarchies/{dimension_name}",
    response_model=HierarchyResponse,
    summary="Get hierarchy tree for a dimension",
)
async def get_hierarchy(dimension_name: str) -> HierarchyResponse:
    """Return the full parent-child tree for the given dimension.

    Supported dimensions: geo, segment, lob, costcenter.
    """
    # TODO: read from hierarchy cache
    return HierarchyResponse(dimension_name=dimension_name, roots=[])


@router.get(
    "/business-units",
    response_model=list[BusinessUnit],
    summary="List all business units",
)
async def list_business_units() -> list[BusinessUnit]:
    """Return flat list of business units."""
    # TODO: read from dim_business_unit
    return []


@router.get(
    "/accounts",
    response_model=list[Account],
    summary="List all accounts",
)
async def list_accounts() -> list[Account]:
    """Return account dimension with parent-child relationships."""
    # TODO: read from dim_account
    return []


@router.get(
    "/periods",
    response_model=list[Period],
    summary="List fiscal periods",
)
async def list_periods() -> list[Period]:
    """Return available fiscal periods."""
    # TODO: read from dim_period
    return []
