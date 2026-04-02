"""Tests for seasonal profile configuration and narrative context."""

import pytest
from shared.config.seasonal import SeasonalConfig


@pytest.fixture
def config() -> SeasonalConfig:
    return SeasonalConfig()


class TestSeasonalConfig:
    def test_loads_config(self, config):
        assert config.tolerance > 0

    def test_december_revenue_factor(self, config):
        factor = config.get_seasonal_factor("Revenue", 12)
        assert factor == 1.40

    def test_august_revenue_factor(self, config):
        factor = config.get_seasonal_factor("Revenue", 8)
        assert factor == 0.85

    def test_neutral_month_factor(self, config):
        factor = config.get_seasonal_factor("Revenue", 5)
        assert factor == 1.00

    def test_nonop_no_seasonality(self, config):
        factor = config.get_seasonal_factor("NonOp", 12)
        assert factor == 1.00

    def test_unknown_category_returns_1(self, config):
        factor = config.get_seasonal_factor("Unknown", 6)
        assert factor == 1.0


class TestSeasonalNotes:
    def test_december_high_season_note(self, config):
        note = config.get_seasonal_note("Revenue", 12)
        assert "December" in note
        assert "peak" in note.lower() or "1.4" in note

    def test_august_low_season_note(self, config):
        note = config.get_seasonal_note("Revenue", 8)
        assert "August" in note
        assert "trough" in note.lower() or "0.85" in note

    def test_neutral_month_no_note(self, config):
        note = config.get_seasonal_note("Revenue", 5)
        # May factor is 1.0 — no special note
        assert note == ""

    def test_nonop_no_note(self, config):
        note = config.get_seasonal_note("NonOp", 12)
        assert note == ""


class TestSeasonalNormCheck:
    def test_december_within_norm(self, config):
        # December revenue expected +40%. If variance is ~40%, it's within norm.
        result = config.is_within_seasonal_norm("Revenue", 12, 38.0)
        assert result is True

    def test_december_exceeds_norm(self, config):
        # December expected +40%. If variance is 60%, it exceeds tolerance.
        result = config.is_within_seasonal_norm("Revenue", 12, 60.0)
        assert result is False

    def test_high_season_check(self, config):
        assert config.is_high_season(12) is True
        assert config.is_high_season(6) is False

    def test_low_season_check(self, config):
        assert config.is_low_season(8) is True
        assert config.is_low_season(3) is False
