"""Tests for netting/trend alert DataService methods."""
import pytest
from shared.data.service import DataService


@pytest.fixture(scope="module")
def ds():
    return DataService("data/output")


class TestNettingAlerts:
    def test_returns_list(self, ds):
        alerts = ds.get_netting_alerts(period_id="2026-06")
        assert isinstance(alerts, list)

    def test_alert_has_required_keys(self, ds):
        alerts = ds.get_netting_alerts(period_id="2026-06")
        if alerts:
            alert = alerts[0]
            assert "left" in alert
            assert "right" in alert
            assert "net" in alert

    def test_respects_limit(self, ds):
        alerts = ds.get_netting_alerts(period_id="2026-06", limit=2)
        assert len(alerts) <= 2

    def test_invalid_period_returns_empty(self, ds):
        alerts = ds.get_netting_alerts(period_id="9999-99")
        assert alerts == []


class TestTrendAlerts:
    def test_returns_list(self, ds):
        alerts = ds.get_trend_alerts()
        assert isinstance(alerts, list)

    def test_alert_has_required_keys(self, ds):
        alerts = ds.get_trend_alerts()
        if alerts:
            alert = alerts[0]
            assert "description" in alert
            assert "projection" in alert

    def test_respects_limit(self, ds):
        alerts = ds.get_trend_alerts(limit=3)
        assert len(alerts) <= 3

    def test_deduplicates_by_account(self, ds):
        alerts = ds.get_trend_alerts(limit=10)
        # Each account should appear at most once
        descriptions = [a["description"] for a in alerts]
        # No exact duplicates
        assert len(descriptions) == len(set(descriptions))
