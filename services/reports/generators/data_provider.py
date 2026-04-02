"""Report data provider — fetches context from computation service."""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ReportContext:
    """All data needed to generate a report."""
    period_id: str
    comparison_base: str = "BUDGET"
    view: str = "MTD"
    bu_id: Optional[str] = None
    summary_cards: list[dict] = field(default_factory=list)
    variances: list[dict] = field(default_factory=list)
    pl_rows: list[dict] = field(default_factory=list)
    waterfall_steps: list[dict] = field(default_factory=list)
    netting_alerts: list[dict] = field(default_factory=list)
    trend_alerts: list[dict] = field(default_factory=list)
    executive_summary: dict = field(default_factory=dict)
    section_narratives: list[dict] = field(default_factory=list)


class ReportDataProvider:
    """Fetches report data from the computation service."""

    def __init__(self, computation_url: str = "http://localhost:8001") -> None:
        self._base_url = computation_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch_context(
        self, period_id: str, comparison_base: str = "BUDGET",
        view: str = "MTD", bu_id: Optional[str] = None,
    ) -> ReportContext:
        """Fetch all report data concurrently."""
        client = await self._ensure_client()
        params = f"period_id={period_id}&base_id={comparison_base}&view_id={view}"
        if bu_id:
            params += f"&bu_id={bu_id}"

        async def _get(path: str) -> Any:
            try:
                resp = await client.get(f"/api/v1{path}")
                if resp.status_code == 200:
                    return resp.json()
            except Exception as exc:
                logger.warning("Failed to fetch %s: %s", path, exc)
            return {}

        summary, variances, pl, waterfall, netting, trends, exec_summary, sections = await asyncio.gather(
            _get(f"/dashboard/summary?{params}"),
            _get(f"/variances/?{params}&page_size=500"),
            _get(f"/pl/statement?{params}"),
            _get(f"/dashboard/waterfall?{params}"),
            _get(f"/dashboard/alerts/netting?period_id={period_id}"),
            _get(f"/dashboard/alerts/trends?period_id={period_id}"),
            _get(f"/dashboard/executive-summary?{params}"),
            _get(f"/dashboard/section-narratives?{params}"),
        )

        return ReportContext(
            period_id=period_id,
            comparison_base=comparison_base,
            view=view,
            bu_id=bu_id,
            summary_cards=summary.get("cards", []),
            variances=variances.get("variances", variances.get("items", [])),
            pl_rows=pl.get("rows", []),
            waterfall_steps=waterfall.get("steps", []),
            netting_alerts=netting.get("alerts", []),
            trend_alerts=trends.get("alerts", []),
            executive_summary=exec_summary or {},
            section_narratives=sections.get("sections", []),
        )
