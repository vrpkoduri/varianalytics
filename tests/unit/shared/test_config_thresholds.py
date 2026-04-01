"""Unit tests for threshold configuration (shared/config/thresholds.py).

Tests threshold resolution hierarchy, OR logic, netting/trend properties.
"""

import pytest
from shared.config.thresholds import ThresholdConfig


@pytest.fixture
def config() -> ThresholdConfig:
    """Load the real thresholds.yaml config."""
    return ThresholdConfig()


class TestGlobalDefaults:
    """Tests for global default thresholds."""

    def test_global_abs_threshold(self, config):
        t = config.get_thresholds()
        assert t["abs_threshold"] == 50000

    def test_global_pct_threshold(self, config):
        t = config.get_thresholds()
        assert t["pct_threshold"] == 3.0

    def test_or_logic(self, config):
        t = config.get_thresholds()
        assert t["logic"] == "OR"


class TestDomainOverrides:
    """Domain overrides should narrow thresholds for specific categories."""

    def test_revenue_override(self, config):
        t = config.get_thresholds(pl_category="Revenue")
        assert t["pct_threshold"] == 2.0  # Tighter than global 3%

    def test_te_override(self, config):
        t = config.get_thresholds(account_name="Travel & Entertainment")
        assert t["pct_threshold"] == 5.0  # Wider than global 3%


class TestRoleOverrides:
    """Role overrides should raise thresholds for senior personas."""

    def test_cfo_higher_threshold(self, config):
        t = config.get_thresholds(role="cfo")
        assert t["abs_threshold"] == 100000
        assert t["pct_threshold"] == 5.0

    def test_board_highest_threshold(self, config):
        t = config.get_thresholds(role="board")
        assert t["abs_threshold"] == 500000
        assert t["pct_threshold"] == 10.0


class TestCloseWeekOverrides:
    """Close week overrides should tighten thresholds."""

    def test_close_week_tighter(self, config):
        t = config.get_thresholds(is_close_week=True)
        assert t["abs_threshold"] == 25000  # Tighter than global 50K
        assert t["pct_threshold"] == 2.0  # Tighter than global 3%


class TestResolutionHierarchy:
    """Most specific override should win: close_week > role > domain > global."""

    def test_close_week_beats_role(self, config):
        """Close week override should beat role override."""
        t = config.get_thresholds(role="cfo", is_close_week=True)
        assert t["abs_threshold"] == 25000  # Close week (not CFO's 100K)

    def test_role_beats_domain(self, config):
        """Role override should beat domain override."""
        t = config.get_thresholds(pl_category="Revenue", role="cfo")
        assert t["abs_threshold"] == 100000  # CFO override


class TestMaterialityCheck:
    """Tests for is_material() with OR logic."""

    def test_abs_breach_is_material(self, config):
        assert config.is_material(60000, 1.0) is True  # > 50K

    def test_pct_breach_is_material(self, config):
        assert config.is_material(10000, 5.0) is True  # > 3%

    def test_both_below_not_material(self, config):
        assert config.is_material(10000, 1.0) is False

    def test_none_pct_uses_abs_only(self, config):
        """When variance_pct is None (budget=0), only abs threshold applies."""
        assert config.is_material(60000, None) is True
        assert config.is_material(10000, None) is False


class TestNettingProperties:
    """Tests for netting-related threshold properties."""

    def test_netting_ratio(self, config):
        assert config.netting_ratio_threshold == 3.0

    def test_child_dispersion(self, config):
        assert config.child_dispersion_threshold == 10.0

    def test_cross_account_enabled(self, config):
        assert config.cross_account_enabled is True


class TestTrendProperties:
    """Tests for trend-related threshold properties."""

    def test_consecutive_periods(self, config):
        assert config.consecutive_periods == 3

    def test_cumulative_breach_enabled(self, config):
        assert config.cumulative_breach_enabled is True
