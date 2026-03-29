"""Tests for ComputationClient — async HTTP client for Computation Service.

Uses httpx.MockTransport to mock HTTP responses without network calls.
"""

from __future__ import annotations

import json

import httpx
import pytest

from services.gateway.clients.computation_client import (
    ComputationClient,
    ComputationServiceError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_transport(
    status_code: int = 200,
    json_body: dict | None = None,
    raise_timeout: bool = False,
) -> httpx.MockTransport:
    """Create a MockTransport that returns the given status/body."""

    async def handler(request: httpx.Request) -> httpx.Response:
        if raise_timeout:
            raise httpx.ReadTimeout("mock timeout")
        body = json.dumps(json_body or {}).encode()
        return httpx.Response(status_code=status_code, content=body)

    return httpx.MockTransport(handler)


def _client_with_transport(transport: httpx.MockTransport) -> ComputationClient:
    """Create a ComputationClient backed by a mock transport."""
    client = ComputationClient.__new__(ComputationClient)
    client._base_url = "http://test"
    client._client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return client


# ---------------------------------------------------------------------------
# Dashboard tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_summary_cards_success():
    """200 response returns parsed JSON dict."""
    body = {"cards": [{"name": "Revenue", "actual": 100}], "period_id": "2026-03"}
    client = _client_with_transport(_mock_transport(200, body))

    result = await client.get_summary_cards(period_id="2026-03")

    assert result is not None
    assert result["cards"][0]["name"] == "Revenue"
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_summary_cards_with_bu_filter():
    """bu_id is passed as a query parameter."""
    captured_params: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_params.update(dict(request.url.params))
        return httpx.Response(200, content=b'{"cards": []}')

    transport = httpx.MockTransport(handler)
    client = _client_with_transport(transport)

    await client.get_summary_cards(period_id="2026-03", bu_id="marsh")

    assert captured_params["bu_id"] == "marsh"
    assert captured_params["period_id"] == "2026-03"
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_waterfall_success():
    """Waterfall endpoint returns parsed JSON."""
    body = {"steps": [{"label": "Budget", "value": 100}]}
    client = _client_with_transport(_mock_transport(200, body))

    result = await client.get_waterfall(period_id="2026-03")

    assert result is not None
    assert "steps" in result
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_trends_success():
    """Trends endpoint returns parsed JSON."""
    body = {"data": [{"period": "2026-01", "actual": 50}]}
    client = _client_with_transport(_mock_transport(200, body))

    result = await client.get_trends(account_id="acct_revenue")

    assert result is not None
    assert "data" in result
    await client.close()


# ---------------------------------------------------------------------------
# Variance tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_variance_detail_success():
    """200 response for variance detail."""
    body = {"variance_id": "var_001", "account_name": "Revenue"}
    client = _client_with_transport(_mock_transport(200, body))

    result = await client.get_variance_detail("var_001")

    assert result is not None
    assert result["variance_id"] == "var_001"
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_variance_detail_not_found():
    """404 response returns None."""
    client = _client_with_transport(_mock_transport(404))

    result = await client.get_variance_detail("var_nonexistent")

    assert result is None
    await client.close()


# ---------------------------------------------------------------------------
# P&L tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_pl_statement_success():
    """P&L statement returns parsed JSON."""
    body = {"rows": [{"account": "Revenue", "actual": 1000}]}
    client = _client_with_transport(_mock_transport(200, body))

    result = await client.get_pl_statement(period_id="2026-03")

    assert result is not None
    assert "rows" in result
    await client.close()


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_success():
    """200 from /health returns True."""
    client = _client_with_transport(_mock_transport(200, {"status": "ok"}))

    assert await client.health_check() is True
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_failure():
    """500 from /health returns False."""
    client = _client_with_transport(_mock_transport(500))

    assert await client.health_check() is False
    await client.close()


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeout_raises_error():
    """Timeout raises ComputationServiceError."""
    client = _client_with_transport(_mock_transport(raise_timeout=True))

    with pytest.raises(ComputationServiceError, match="Timeout"):
        await client.get_summary_cards(period_id="2026-03")

    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_server_error_raises_error():
    """500 response raises ComputationServiceError."""
    client = _client_with_transport(_mock_transport(500))

    with pytest.raises(ComputationServiceError, match="HTTP 500"):
        await client.get_summary_cards(period_id="2026-03")

    await client.close()
