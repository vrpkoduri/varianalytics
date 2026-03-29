"""Unit tests for ThresholdConfig — materiality threshold loading and resolution.

Tests global defaults, domain overrides, close-week overrides, and the
is_material() OR-logic evaluation.
"""

from __future__ import annotations

import pytest

from shared.config.thresholds import ThresholdConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> ThresholdConfig:
    """Standard threshold config loaded from the project YAML."""
    return ThresholdConfig()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGlobalDefaults:
    """Verify global threshold defaults from thresholds.yaml."""

    def test_global_threshold_defaults(self, config: ThresholdConfig) -> None:
        """Global thresholds: abs=$50K, pct=3.0%, logic=OR."""
        thresholds = config.get_thresholds()
        assert thresholds["abs_threshold"] == 50_000
        assert thresholds["pct_threshold"] == 3.0
        assert thresholds["logic"] == "OR"


@pytest.mark.unit
class TestDomainOverrides:
    """Verify domain-level threshold overrides."""

    def test_revenue_domain_override(self, config: ThresholdConfig) -> None:
        """Revenue pct threshold should be 2.0 (tighter than global 3.0).

        The abs_threshold should remain at the global $50K default since
        only pct_threshold is overridden for Revenue.
        """
        thresholds = config.get_thresholds(pl_category="Revenue")
        assert thresholds["pct_threshold"] == 2.0
        assert thresholds["abs_threshold"] == 50_000


@pytest.mark.unit
class TestIsMaterial:
    """Test the is_material() OR-logic evaluation."""

    def test_is_material_abs_breach(self, config: ThresholdConfig) -> None:
        """$60K variance with 1% -> material (abs breach only).

        60K >= 50K threshold -> abs breach = True.
        1% < 3% threshold -> pct breach = False.
        OR logic -> material = True.
        """
        assert config.is_material(60_000, 1.0) is True

    def test_is_material_pct_breach(self, config: ThresholdConfig) -> None:
        """$10K variance with 5% -> material (pct breach only).

        10K < 50K threshold -> abs breach = False.
        5% >= 3% threshold -> pct breach = True.
        OR logic -> material = True.
        """
        assert config.is_material(10_000, 5.0) is True

    def test_not_material(self, config: ThresholdConfig) -> None:
        """$10K variance with 1% -> not material.

        10K < 50K threshold -> abs breach = False.
        1% < 3% threshold -> pct breach = False.
        OR logic -> material = False.
        """
        assert config.is_material(10_000, 1.0) is False

    def test_is_material_negative_variance(self, config: ThresholdConfig) -> None:
        """Negative $60K variance with -4% -> material.

        Uses absolute values: |60K| >= 50K and |-4%| >= 3%.
        """
        assert config.is_material(-60_000, -4.0) is True

    def test_is_material_pct_none(self, config: ThresholdConfig) -> None:
        """$60K variance with pct=None -> material (abs breach only).

        When comparator is zero, pct is None. Only abs is checked.
        """
        assert config.is_material(60_000, None) is True

    def test_not_material_pct_none(self, config: ThresholdConfig) -> None:
        """$10K variance with pct=None -> not material.

        10K < 50K, and pct is unavailable.
        """
        assert config.is_material(10_000, None) is False


@pytest.mark.unit
class TestCloseWeekOverride:
    """Test close week uses tighter thresholds."""

    def test_close_week_override(self, config: ThresholdConfig) -> None:
        """Close week: abs=$25K, pct=2.0%.

        A $30K / 2.5% variance is NOT material normally ($30K < $50K, 2.5% < 3%),
        but IS material during close week ($30K >= $25K).
        """
        # Normal: not material
        assert config.is_material(30_000, 2.5) is False

        # Close week: material (30K >= 25K threshold)
        assert config.is_material(30_000, 2.5, is_close_week=True) is True

    def test_close_week_pct_threshold(self, config: ThresholdConfig) -> None:
        """Close week pct threshold is 2.0% (tighter than global 3.0%).

        A $10K / 2.5% variance is NOT material normally but IS during close week.
        """
        assert config.is_material(10_000, 2.5) is False
        assert config.is_material(10_000, 2.5, is_close_week=True) is True


@pytest.mark.unit
class TestNettingProperties:
    """Test netting-related threshold properties."""

    def test_netting_ratio_threshold(self, config: ThresholdConfig) -> None:
        """Netting ratio threshold should be 3.0 from YAML."""
        assert config.netting_ratio_threshold == 3.0

    def test_child_dispersion_threshold(self, config: ThresholdConfig) -> None:
        """Child dispersion threshold should be 10.0 from YAML."""
        assert config.child_dispersion_threshold == 10.0

    def test_consecutive_periods(self, config: ThresholdConfig) -> None:
        """Consecutive periods for trend detection should be 3."""
        assert config.consecutive_periods == 3
