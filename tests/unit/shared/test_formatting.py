"""Unit tests for shared.utils.formatting — currency, percentage, variance formatters."""

import pytest

from shared.utils.formatting import (
    format_currency,
    format_currency_thousands,
    format_percentage,
    format_variance,
    sign_convention_label,
)


@pytest.mark.unit
class TestFormatCurrency:
    """Tests for currency formatting."""

    def test_positive_whole_dollars(self) -> None:
        assert format_currency(1234567) == "$1,234,567"

    def test_negative_amount(self) -> None:
        assert format_currency(-500000) == "-$500,000"

    def test_with_decimals(self) -> None:
        assert format_currency(1234.56, decimals=2) == "$1,234.56"

    def test_zero(self) -> None:
        assert format_currency(0) == "$0"


@pytest.mark.unit
class TestFormatCurrencyThousands:
    """Tests for abbreviated currency formatting."""

    def test_millions(self) -> None:
        assert format_currency_thousands(1234567) == "$1.2M"

    def test_thousands(self) -> None:
        assert format_currency_thousands(450000) == "$450K"

    def test_small_amount(self) -> None:
        assert format_currency_thousands(500) == "$500"

    def test_negative_millions(self) -> None:
        assert format_currency_thousands(-2500000) == "-$2.5M"


@pytest.mark.unit
class TestFormatPercentage:
    """Tests for percentage formatting."""

    def test_positive(self) -> None:
        assert format_percentage(3.5) == "+3.5%"

    def test_negative(self) -> None:
        assert format_percentage(-1.2) == "-1.2%"

    def test_none(self) -> None:
        assert format_percentage(None) == "N/A"

    def test_zero(self) -> None:
        assert format_percentage(0.0) == "+0.0%"


@pytest.mark.unit
class TestFormatVariance:
    """Tests for combined variance formatting."""

    def test_positive_variance(self) -> None:
        result = format_variance(1200000, 3.5)
        assert "+$1.2M" in result
        assert "+3.5%" in result

    def test_negative_variance(self) -> None:
        result = format_variance(-500000, -2.1)
        assert "-$500K" in result
        assert "-2.1%" in result


@pytest.mark.unit
class TestSignConvention:
    """Tests for favorable/unfavorable labeling."""

    def test_revenue_positive_favorable(self) -> None:
        assert sign_convention_label(100000, is_inverse=False) == "Favorable"

    def test_revenue_negative_unfavorable(self) -> None:
        assert sign_convention_label(-100000, is_inverse=False) == "Unfavorable"

    def test_cost_negative_favorable(self) -> None:
        assert sign_convention_label(-50000, is_inverse=True) == "Favorable"

    def test_cost_positive_unfavorable(self) -> None:
        assert sign_convention_label(50000, is_inverse=True) == "Unfavorable"
