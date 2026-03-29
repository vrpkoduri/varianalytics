"""Async HTTP client for Computation Service.

Provides typed methods for every Computation API endpoint.
Used by ToolExecutor in the agent pipeline.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class ComputationServiceError(Exception):
    """Raised on 5xx or network errors from Computation Service."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ComputationClient:
    """Async HTTP client wrapping all Computation Service (port 8001) endpoints.

    Usage::

        client = ComputationClient(base_url="http://localhost:8001")
        cards = await client.get_summary_cards(period_id="2026-03")
        await client.close()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict | None:
        """Make GET request. Returns JSON dict on 200, None on 404, raises on error."""
        try:
            cleaned = {k: v for k, v in (params or {}).items() if v is not None}
            resp = await self._client.get(path, params=cleaned)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except (json.JSONDecodeError, ValueError) as e:
                    raise ComputationServiceError(
                        f"Malformed JSON response from {path}: {e}",
                        status_code=resp.status_code,
                    ) from e
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
        except httpx.TimeoutException as e:
            raise ComputationServiceError(f"Timeout calling {path}: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ComputationServiceError(
                f"HTTP {e.response.status_code} from {path}",
                e.response.status_code,
            ) from e
        except httpx.HTTPError as e:
            raise ComputationServiceError(f"Network error calling {path}: {e}") from e
        return None

    # ------------------------------------------------------------------
    # Dashboard endpoints
    # ------------------------------------------------------------------

    async def get_summary_cards(
        self,
        period_id: str,
        bu_id: str | None = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
    ) -> dict | None:
        """GET /api/v1/dashboard/summary — KPI summary cards."""
        return await self._get(
            "/api/v1/dashboard/summary",
            params={
                "period_id": period_id,
                "bu_id": bu_id,
                "view_id": view_id,
                "base_id": base_id,
            },
        )

    async def get_waterfall(
        self,
        period_id: str,
        bu_id: str | None = None,
        base_id: str = "BUDGET",
    ) -> dict | None:
        """GET /api/v1/dashboard/waterfall — Bridge chart data."""
        return await self._get(
            "/api/v1/dashboard/waterfall",
            params={
                "period_id": period_id,
                "bu_id": bu_id,
                "base_id": base_id,
            },
        )

    async def get_heatmap(
        self,
        period_id: str,
        base_id: str = "BUDGET",
    ) -> dict | None:
        """GET /api/v1/dashboard/heatmap — Geo x BU variance heatmap."""
        return await self._get(
            "/api/v1/dashboard/heatmap",
            params={
                "period_id": period_id,
                "base_id": base_id,
            },
        )

    async def get_trends(
        self,
        bu_id: str | None = None,
        account_id: str = "acct_gross_revenue",
        base_id: str = "BUDGET",
        periods: int = 12,
    ) -> dict | None:
        """GET /api/v1/dashboard/trends — Time-series trend data."""
        return await self._get(
            "/api/v1/dashboard/trends",
            params={
                "bu_id": bu_id,
                "account_id": account_id,
                "base_id": base_id,
                "periods": periods,
            },
        )

    # ------------------------------------------------------------------
    # Variance endpoints
    # ------------------------------------------------------------------

    async def get_variance_list(
        self,
        period_id: str,
        bu_id: str | None = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
        pl_category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict | None:
        """GET /api/v1/variances/ — Paginated material variances."""
        return await self._get(
            "/api/v1/variances/",
            params={
                "period_id": period_id,
                "bu_id": bu_id,
                "view_id": view_id,
                "base_id": base_id,
                "pl_category": pl_category,
                "page": page,
                "page_size": page_size,
            },
        )

    async def get_variance_detail(self, variance_id: str) -> dict | None:
        """GET /api/v1/variances/{variance_id} — Full variance detail."""
        return await self._get(f"/api/v1/variances/{variance_id}")

    async def get_variance_by_account(
        self,
        account_id: str,
        period_id: str,
        bu_id: str | None = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
    ) -> dict | None:
        """GET /api/v1/variances/by-account/{account_id} — Account variances."""
        return await self._get(
            f"/api/v1/variances/by-account/{account_id}",
            params={
                "period_id": period_id,
                "bu_id": bu_id,
                "view_id": view_id,
                "base_id": base_id,
            },
        )

    # ------------------------------------------------------------------
    # P&L endpoints
    # ------------------------------------------------------------------

    async def get_pl_statement(
        self,
        period_id: str,
        bu_id: str | None = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
    ) -> dict | None:
        """GET /api/v1/pl/statement — Full P&L with hierarchy."""
        return await self._get(
            "/api/v1/pl/statement",
            params={
                "period_id": period_id,
                "bu_id": bu_id,
                "view_id": view_id,
                "base_id": base_id,
            },
        )

    async def get_account_detail(
        self,
        account_id: str,
        period_id: str,
        bu_id: str | None = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
    ) -> dict | None:
        """GET /api/v1/pl/account/{account_id}/detail — Account breakdown."""
        return await self._get(
            f"/api/v1/pl/account/{account_id}/detail",
            params={
                "period_id": period_id,
                "bu_id": bu_id,
                "view_id": view_id,
                "base_id": base_id,
            },
        )

    # ------------------------------------------------------------------
    # Drilldown endpoints
    # ------------------------------------------------------------------

    async def get_decomposition(self, variance_id: str) -> dict | None:
        """GET /api/v1/drilldown/decomposition/{variance_id} — Variance decomposition."""
        return await self._get(f"/api/v1/drilldown/decomposition/{variance_id}")

    async def get_netting(self, node_id: str, period_id: str) -> dict | None:
        """GET /api/v1/drilldown/netting/{node_id} — Netting analysis."""
        return await self._get(
            f"/api/v1/drilldown/netting/{node_id}",
            params={"period_id": period_id},
        )

    async def get_correlations(self, variance_id: str) -> dict | None:
        """GET /api/v1/drilldown/correlations/{variance_id} — Correlated variances."""
        return await self._get(f"/api/v1/drilldown/correlations/{variance_id}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    async def health_check(self) -> bool:
        """GET /health — returns True if Computation Service is healthy."""
        try:
            resp = await self._client.get("/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
