"""Tests for period utility functions."""

import pytest
from shared.utils.period_utils import (
    get_prior_period,
    get_fiscal_quarter,
    get_quarter_periods,
    get_month_name,
    get_month_short,
    get_year_quarter_ends,
    get_quarter_number,
)


class TestGetPriorPeriod:
    def test_standard_month(self):
        assert get_prior_period("2026-05") == "2026-04"

    def test_year_boundary(self):
        assert get_prior_period("2026-01") == "2025-12"

    def test_december(self):
        assert get_prior_period("2025-12") == "2025-11"

    def test_invalid(self):
        assert get_prior_period("invalid") is None


class TestGetFiscalQuarter:
    def test_q1(self):
        assert get_fiscal_quarter("2026-01") == "Q1"
        assert get_fiscal_quarter("2026-03") == "Q1"

    def test_q2(self):
        assert get_fiscal_quarter("2026-04") == "Q2"
        assert get_fiscal_quarter("2026-06") == "Q2"

    def test_q3(self):
        assert get_fiscal_quarter("2026-07") == "Q3"

    def test_q4(self):
        assert get_fiscal_quarter("2026-12") == "Q4"


class TestGetQuarterPeriods:
    def test_q2(self):
        assert get_quarter_periods("2026-05") == ["2026-04", "2026-05", "2026-06"]

    def test_q1(self):
        assert get_quarter_periods("2026-02") == ["2026-01", "2026-02", "2026-03"]

    def test_q4(self):
        assert get_quarter_periods("2026-12") == ["2026-10", "2026-11", "2026-12"]


class TestMonthNames:
    def test_month_name(self):
        assert get_month_name("2026-05") == "May"
        assert get_month_name("2026-12") == "December"

    def test_month_short(self):
        assert get_month_short("2026-05") == "May"
        assert get_month_short("2026-01") == "Jan"


class TestYearQuarterEnds:
    def test_quarter_ends(self):
        result = get_year_quarter_ends("2026-05")
        assert result == ["2026-03", "2026-06", "2026-09", "2026-12"]


class TestQuarterNumber:
    def test_numbers(self):
        assert get_quarter_number("2026-01") == 1
        assert get_quarter_number("2026-06") == 2
        assert get_quarter_number("2026-09") == 3
        assert get_quarter_number("2026-12") == 4
