"""API endpoint latency benchmark tests.

Validates that key API endpoints respond within SLA thresholds.
Each endpoint is called 5 times and the p95 (worst of 5) is checked.

SLAs:
- Dashboard endpoints: < 200ms
- Variance list: < 300ms
- P&L statement: < 500ms
- Auth login: < 500ms
- Dimensions: < 100ms
"""

import statistics
import time

import pytest
from fastapi.testclient import TestClient

from shared.data.service import DataService

# Default query params for a valid period
DEFAULT_PARAMS = "period_id=2026-03&view_id=MTD&base_id=BUDGET"
ITERATIONS = 5


@pytest.fixture(scope="module")
def comp_client():
    """Computation service test client with DataService initialized."""
    from services.computation.main import app
    app.state.data_service = DataService()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def gw_client():
    """Gateway test client (dev mode — no auth required)."""
    from services.gateway.main import app
    with TestClient(app) as c:
        yield c


def _measure_p95(client, method: str, url: str, iterations: int = ITERATIONS, **kwargs) -> float:
    """Call an endpoint multiple times and return p95 latency in milliseconds."""
    times_ms = []
    for _ in range(iterations):
        start = time.monotonic()
        if method == "GET":
            resp = client.get(url, **kwargs)
        elif method == "POST":
            resp = client.post(url, **kwargs)
        else:
            raise ValueError(f"Unknown method: {method}")
        elapsed_ms = (time.monotonic() - start) * 1000
        times_ms.append(elapsed_ms)
        assert resp.status_code in (200, 201, 204), (
            f"{url} returned {resp.status_code}: {resp.text[:200]}"
        )
    # p95 of 5 samples ≈ the maximum
    return max(times_ms)


# ---------------------------------------------------------------------------
# Dashboard endpoints (computation service)
# ---------------------------------------------------------------------------

@pytest.mark.performance
class TestDashboardLatency:
    """Dashboard API endpoints must respond within SLA."""

    def test_summary_under_200ms(self, comp_client):
        p95 = _measure_p95(comp_client, "GET", f"/api/v1/dashboard/summary?{DEFAULT_PARAMS}")
        assert p95 < 200, f"Dashboard summary p95={p95:.0f}ms (SLA: <200ms)"

    def test_waterfall_under_200ms(self, comp_client):
        p95 = _measure_p95(comp_client, "GET", f"/api/v1/dashboard/waterfall?{DEFAULT_PARAMS}")
        assert p95 < 200, f"Waterfall p95={p95:.0f}ms (SLA: <200ms)"

    def test_heatmap_under_300ms(self, comp_client):
        p95 = _measure_p95(comp_client, "GET", f"/api/v1/dashboard/heatmap?{DEFAULT_PARAMS}")
        assert p95 < 300, f"Heatmap p95={p95:.0f}ms (SLA: <300ms)"

    def test_trends_under_200ms(self, comp_client):
        p95 = _measure_p95(comp_client, "GET", "/api/v1/dashboard/trends")
        assert p95 < 200, f"Trends p95={p95:.0f}ms (SLA: <200ms)"


# ---------------------------------------------------------------------------
# Variance endpoints (computation service)
# ---------------------------------------------------------------------------

@pytest.mark.performance
class TestVarianceLatency:
    """Variance API endpoints must respond within SLA."""

    def test_variance_list_under_300ms(self, comp_client):
        p95 = _measure_p95(
            comp_client, "GET",
            f"/api/v1/variances/?{DEFAULT_PARAMS}&page_size=50",
        )
        assert p95 < 300, f"Variance list p95={p95:.0f}ms (SLA: <300ms)"

    def test_pl_statement_under_500ms(self, comp_client):
        p95 = _measure_p95(
            comp_client, "GET",
            f"/api/v1/pl/statement?{DEFAULT_PARAMS}",
        )
        assert p95 < 500, f"P&L statement p95={p95:.0f}ms (SLA: <500ms)"


# ---------------------------------------------------------------------------
# Gateway endpoints
# ---------------------------------------------------------------------------

@pytest.mark.performance
class TestGatewayLatency:
    """Gateway API endpoints must respond within SLA."""

    def test_review_queue_under_200ms(self, gw_client):
        p95 = _measure_p95(gw_client, "GET", "/api/v1/review/queue")
        assert p95 < 200, f"Review queue p95={p95:.0f}ms (SLA: <200ms)"

    def test_dimensions_hierarchy_under_100ms(self, gw_client):
        p95 = _measure_p95(gw_client, "GET", "/api/v1/dimensions/hierarchies/geography")
        assert p95 < 100, f"Dimensions p95={p95:.0f}ms (SLA: <100ms)"
