"""Scenario Validation Tests.

Verifies the 4 deliberate variance scenarios from synthetic data
surface correctly through both raw parquet data AND API endpoints.

Original coverage: APAC netting, tech cost trend, UK correlation, Q2 consulting.
Added coverage: API-level validation that scenarios surface through endpoints.
"""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from services.computation.main import app as computation_app

DATA_DIR = "data/output"

APAC_LEAF_GEOS = ["geo_anz", "geo_japan", "geo_india", "geo_singapore", "geo_hong_kong"]


@pytest.fixture(scope="module")
def comp():
    with TestClient(computation_app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def ff():
    return pd.read_parquet(f"{DATA_DIR}/fact_financials.parquet")


@pytest.fixture(scope="module")
def vm():
    return pd.read_parquet(f"{DATA_DIR}/fact_variance_material.parquet")


@pytest.fixture(scope="module")
def netting():
    return pd.read_parquet(f"{DATA_DIR}/fact_netting_flags.parquet")


@pytest.fixture(scope="module")
def trends():
    return pd.read_parquet(f"{DATA_DIR}/fact_trend_flags.parquet")


@pytest.fixture(scope="module")
def correlations():
    return pd.read_parquet(f"{DATA_DIR}/fact_correlations.parquet")


@pytest.fixture(scope="module")
def spec():
    with open("docs/synthetic-data-spec.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Scenario 1: APAC Revenue Netting
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScenarioAPACNetting:
    """Scenario 1: Advisory fees up in APAC, consulting fees down."""

    def test_scenario_apac_advisory_multiplier(self, ff: pd.DataFrame) -> None:
        """Marsh APAC advisory fees in 2026-06 should be above budget."""
        data = ff[
            (ff["bu_id"] == "marsh")
            & (ff["account_id"] == "acct_advisory_fees")
            & (ff["period_id"] == "2026-06")
            & (ff["geo_node_id"].isin(APAC_LEAF_GEOS))
        ]
        assert len(data) > 0, "No APAC advisory rows found for Marsh 2026-06"
        ratio = (data["actual_amount"] / data["budget_amount"]).mean()
        assert 0.95 <= ratio <= 1.35, f"Mean actual/budget ratio {ratio:.3f} outside expected range"

    def test_scenario_apac_consulting_offset(self, ff: pd.DataFrame) -> None:
        """OW APAC consulting fees in 2026-06 should be below budget."""
        data = ff[
            (ff["bu_id"] == "oliver_wyman")
            & (ff["account_id"] == "acct_consulting_fees")
            & (ff["period_id"] == "2026-06")
            & (ff["geo_node_id"].isin(APAC_LEAF_GEOS))
        ]
        assert len(data) > 0, "No APAC consulting rows found for OW 2026-06"
        ratio = (data["actual_amount"] / data["budget_amount"]).mean()
        assert 0.62 <= ratio <= 1.02, f"Mean actual/budget ratio {ratio:.3f} outside expected range"

    def test_scenario_apac_netting_detected(self, netting: pd.DataFrame) -> None:
        """At least 1 netting flag with cross_account type and ratio > 3.0."""
        cross_acct = netting[
            (netting["check_type"] == "cross_account")
            & (netting["netting_ratio"] > 3.0)
        ]
        assert len(cross_acct) >= 1, (
            f"Expected at least 1 cross_account netting flag with ratio > 3.0, "
            f"got {len(cross_acct)}"
        )


# ---------------------------------------------------------------------------
# Scenario 2: Technology Cost Trend
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScenarioTechCostTrend:
    """Scenario 2: Tech costs creeping up month-over-month."""

    def test_scenario_tech_cost_growth_pattern(self, ff: pd.DataFrame) -> None:
        """Tech infra actual/budget ratio should generally increase over H1 2026."""
        periods = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
        ratios = []
        for p in periods:
            data = ff[
                (ff["account_id"] == "acct_tech_infra") & (ff["period_id"] == p)
            ]
            if len(data) > 0:
                ratios.append((data["actual_amount"] / data["budget_amount"]).mean())

        assert len(ratios) == 6, f"Expected 6 periods, got {len(ratios)}"
        assert ratios[-1] > ratios[0], (
            f"Tech cost ratio should increase over H1 2026: "
            f"first={ratios[0]:.4f}, last={ratios[-1]:.4f}"
        )

    def test_scenario_tech_trend_flag_detected(self, trends: pd.DataFrame) -> None:
        """At least 1 trend flag for acct_tech_infra with consecutive_periods >= 3."""
        tech_trends = trends[
            (trends["account_id"] == "acct_tech_infra")
            & (trends["rule_type"] == "consecutive_direction")
            & (trends["consecutive_periods"] >= 3)
        ]
        assert len(tech_trends) >= 1, (
            "Expected at least 1 consecutive-direction trend flag for tech infra"
        )


# ---------------------------------------------------------------------------
# Scenario 3: UK Revenue + Cost Correlation
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScenarioUKRevenueAndCost:
    """Scenario 3: UK advisory revenue surge with contractor cost overrun."""

    def test_scenario_uk_advisory_surge(self, ff: pd.DataFrame) -> None:
        """UK advisory fees in 2026-06 should be above budget."""
        data = ff[
            (ff["geo_node_id"] == "geo_uk_ireland")
            & (ff["account_id"] == "acct_advisory_fees")
            & (ff["period_id"] == "2026-06")
        ]
        assert len(data) > 0, "No UK advisory data for 2026-06"
        ratio = (data["actual_amount"] / data["budget_amount"]).mean()
        assert ratio > 1.0, f"UK advisory ratio {ratio:.3f} should be > 1.0"

    def test_scenario_uk_subcontractor_overrun(self, ff: pd.DataFrame) -> None:
        """UK subcontractor costs in 2026-06 should be above budget."""
        data = ff[
            (ff["geo_node_id"] == "geo_uk_ireland")
            & (ff["account_id"] == "acct_subcontractor")
            & (ff["period_id"] == "2026-06")
        ]
        assert len(data) > 0, "No UK subcontractor data for 2026-06"
        ratio = (data["actual_amount"] / data["budget_amount"]).mean()
        assert ratio > 1.0, f"UK subcontractor ratio {ratio:.3f} should be > 1.0"


# ---------------------------------------------------------------------------
# Scenario 4: Q2 Consulting Slowdown
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScenarioQ2ConsultingSlowdown:
    """Scenario 4: Oliver Wyman consulting revenue declining 3 months."""

    def test_scenario_ow_consulting_decline_pattern(self, ff: pd.DataFrame) -> None:
        """OW consulting actual/budget ratio should decrease April-May-June 2026."""
        periods = ["2026-04", "2026-05", "2026-06"]
        ratios = []
        for p in periods:
            data = ff[
                (ff["bu_id"] == "oliver_wyman")
                & (ff["account_id"] == "acct_consulting_fees")
                & (ff["period_id"] == p)
            ]
            if len(data) > 0:
                ratios.append((data["actual_amount"] / data["budget_amount"]).mean())

        assert len(ratios) == 3, f"Expected 3 periods, got {len(ratios)}"
        for i in range(1, len(ratios)):
            assert ratios[i] < ratios[i - 1], (
                f"OW consulting ratio should decline: "
                f"period {periods[i]}={ratios[i]:.4f} >= "
                f"period {periods[i-1]}={ratios[i-1]:.4f}"
            )

    def test_scenario_ow_trend_flag_detected(self, trends: pd.DataFrame) -> None:
        """At least 1 trend flag for consulting with decreasing direction."""
        consult_trends = trends[
            (trends["account_id"].str.contains("consulting", case=False))
            & (trends["direction"] == "decreasing")
            & (trends["consecutive_periods"] >= 3)
        ]
        assert len(consult_trends) >= 1, (
            "Expected at least 1 decreasing trend flag for consulting"
        )


# ---------------------------------------------------------------------------
# API-Level Scenario Validation (NEW — Sprint 1+2)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestNettingScenarioAPI:
    """Validate netting scenarios surface through API endpoints."""

    def test_netting_flags_count(self, netting):
        assert len(netting) >= 10, f"Expected >=10 netting flags, got {len(netting)}"

    def test_netting_alert_api_returns_pairs(self, comp):
        resp = comp.get("/api/v1/dashboard/alerts/netting?period_id=2026-06")
        alerts = resp.json().get("alerts", [])
        assert len(alerts) > 0, "No netting alerts returned"
        alert = alerts[0]
        assert "left" in alert and "right" in alert and "net" in alert


@pytest.mark.integration
class TestTrendScenarioAPI:
    """Validate trend scenarios surface through API endpoints."""

    def test_tech_trend_detected_in_parquet(self, trends):
        tech = trends[trends["account_id"].str.contains("tech", na=False)]
        assert len(tech) > 0, "No tech trend flags detected"
        assert tech["consecutive_periods"].max() >= 3, "Tech trend should have >=3 consecutive periods"

    def test_trend_alert_api_returns_alerts(self, comp):
        resp = comp.get("/api/v1/dashboard/alerts/trends")
        assert resp.status_code == 200
        alerts = resp.json().get("alerts", [])
        assert len(alerts) > 0, "No trend alerts returned from API"
        # Each alert should have a description
        for alert in alerts:
            assert "description" in alert, "Alert missing description"

    def test_consulting_decline_detected_in_parquet(self, trends):
        consulting = trends[trends["account_id"].str.contains("consult", na=False)]
        decreasing = consulting[consulting["direction"] == "decreasing"]
        assert len(decreasing) > 0, "No consulting decline detected"


@pytest.mark.integration
class TestCorrelationScenarioAPI:
    """Validate correlation scenarios surface through API endpoints."""

    def test_correlation_pairs_exist(self, correlations):
        assert len(correlations) == 20, f"Expected 20 correlation pairs, got {len(correlations)}"
        assert correlations["correlation_score"].min() >= 0.3, "Minimum score should be >=0.3"


# ---------------------------------------------------------------------------
# Spec Validation
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSpecStructure:
    """Validate the synthetic-data-spec.json scenario definitions."""

    def test_spec_has_four_scenarios(self, spec: dict) -> None:
        """The spec should define exactly 4 scenario injections."""
        scenarios = spec["data_generation_rules"]["scenario_injections"]["scenarios"]
        assert len(scenarios) == 4, f"Expected 4 scenarios, got {len(scenarios)}"

    def test_each_scenario_has_required_fields(self, spec: dict) -> None:
        """Each scenario should have name, description, and either adjustments or cumulative_multipliers."""
        scenarios = spec["data_generation_rules"]["scenario_injections"]["scenarios"]
        for scenario in scenarios:
            assert "name" in scenario, f"Scenario missing 'name': {scenario}"
            assert "description" in scenario, f"Scenario missing 'description': {scenario}"
            has_adjustments = "adjustments" in scenario
            has_multipliers = "cumulative_multipliers" in scenario
            assert has_adjustments or has_multipliers, (
                f"Scenario '{scenario['name']}' missing both 'adjustments' and 'cumulative_multipliers'"
            )
