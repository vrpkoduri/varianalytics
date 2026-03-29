"""Tests for response templates — formatting helpers and template rendering."""

from __future__ import annotations

import pytest

from services.gateway.agents.intent import Intent
from services.gateway.agents.templates import (
    build_variance_table_data,
    format_currency,
    format_pct,
    format_response,
    get_suggestions,
)


# ---------------------------------------------------------------------------
# format_currency
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_format_currency_positive():
    assert format_currency(1234567.89) == "$1,234,568"


@pytest.mark.unit
def test_format_currency_negative():
    assert format_currency(-500000) == "($500,000)"


# ---------------------------------------------------------------------------
# format_pct
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_format_pct():
    assert format_pct(0.054) == "+5.4%"
    assert format_pct(-0.123) == "-12.3%"
    assert format_pct(None) == "N/A"
    assert format_pct(0.0) == "+0.0%"


# ---------------------------------------------------------------------------
# format_response
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_format_response_revenue_overview():
    data = {
        "period": "March 2026",
        "actual": "$10,500,000",
        "direction": "up",
        "variance": "$500,000",
        "pct": "+5.0%",
        "base": "Budget",
        "table": "Marsh: $5M | Mercer: $3M",
        "top_driver": "Marsh drove the largest favorable variance.",
    }
    result = format_response(Intent.REVENUE_OVERVIEW, data)

    assert "Revenue Performance Summary for March 2026" in result
    assert "$10,500,000" in result
    assert "Marsh drove the largest favorable variance." in result


@pytest.mark.unit
def test_format_response_missing_data():
    """Missing keys do not crash — they render as empty strings."""
    result = format_response(Intent.REVENUE_OVERVIEW, {"period": "March 2026"})

    assert "Revenue Performance Summary for March 2026" in result
    # Should not raise; missing keys become ""
    assert result is not None


# ---------------------------------------------------------------------------
# get_suggestions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_suggestions_revenue():
    suggestions = get_suggestions(Intent.REVENUE_OVERVIEW)
    assert len(suggestions) > 0
    assert any("waterfall" in s.lower() for s in suggestions)


@pytest.mark.unit
def test_get_suggestions_general():
    suggestions = get_suggestions(Intent.GENERAL)
    assert len(suggestions) > 0


# ---------------------------------------------------------------------------
# build_variance_table_data
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_variance_table_data():
    variances = [
        {
            "account_name": "Advisory Fees",
            "actual_amount": 5000000,
            "comparator_amount": 4500000,
            "variance_amount": 500000,
            "variance_pct": 0.111,
        },
        {
            "account_name": "Consulting Fees",
            "actual_amount": 3000000,
            "budget_amount": 3200000,
            "variance_amount": -200000,
            "variance_pct": -0.0625,
        },
    ]

    columns, rows = build_variance_table_data(variances)

    assert columns == ["Account", "Actual", "Budget", "Variance ($)", "Variance (%)"]
    assert len(rows) == 2
    assert rows[0][0] == "Advisory Fees"
    assert rows[0][1] == "$5,000,000"
    assert rows[1][3] == "($200,000)"
    assert rows[1][4] == "-6.2%"
