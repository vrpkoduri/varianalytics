"""Tests for ToolExecutor — maps tool names to ComputationClient calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.gateway.agents.tools import ToolExecutor
from services.gateway.clients.computation_client import (
    ComputationClient,
    ComputationServiceError,
)


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock ComputationClient with AsyncMock methods."""
    client = AsyncMock(spec=ComputationClient)
    return client


@pytest.fixture
def executor(mock_client: AsyncMock) -> ToolExecutor:
    return ToolExecutor(client=mock_client)


# ---------------------------------------------------------------------------
# Tool execution tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_dashboard_summary(executor: ToolExecutor, mock_client: AsyncMock):
    """get_dashboard_summary calls client.get_summary_cards."""
    mock_client.get_summary_cards.return_value = {"cards": []}

    result = await executor.execute(
        "get_dashboard_summary",
        {"period_id": "2026-03", "view": "MTD", "base": "BUDGET"},
    )

    assert result == {"cards": []}
    mock_client.get_summary_cards.assert_awaited_once_with(
        period_id="2026-03",
        bu_id=None,
        view_id="MTD",
        base_id="BUDGET",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_variance_detail(executor: ToolExecutor, mock_client: AsyncMock):
    """get_variance_detail calls client.get_variance_detail."""
    mock_client.get_variance_detail.return_value = {"variance_id": "var_001"}

    result = await executor.execute(
        "get_variance_detail",
        {"variance_id": "var_001"},
    )

    assert result == {"variance_id": "var_001"}
    mock_client.get_variance_detail.assert_awaited_once_with(variance_id="var_001")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_variance_list(executor: ToolExecutor, mock_client: AsyncMock):
    """get_variance_list calls client.get_variance_list."""
    mock_client.get_variance_list.return_value = {"variances": [], "total": 0}

    result = await executor.execute(
        "get_variance_list",
        {"period_id": "2026-03"},
    )

    assert result is not None
    assert result["total"] == 0
    mock_client.get_variance_list.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_unknown_tool(executor: ToolExecutor):
    """Unknown tool name returns None."""
    result = await executor.execute("nonexistent_tool", {})
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_handles_client_error(executor: ToolExecutor, mock_client: AsyncMock):
    """ComputationServiceError is caught and returns None."""
    mock_client.get_summary_cards.side_effect = ComputationServiceError("boom", 500)

    result = await executor.execute(
        "get_dashboard_summary",
        {"period_id": "2026-03"},
    )

    assert result is None
