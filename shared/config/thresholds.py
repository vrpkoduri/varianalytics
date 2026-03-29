"""Threshold configuration loader.

Loads materiality thresholds from thresholds.yaml and provides resolution
logic: close_week > role > account > domain > global.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml


class ThresholdConfig:
    """Materiality threshold configuration with hierarchical resolution.

    Resolution order (most specific wins):
    1. close_week overrides (during close week)
    2. role overrides (CFO, Board)
    3. account-level overrides (future)
    4. domain overrides (Revenue, T&E)
    5. global defaults
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Load threshold config from YAML file.

        Args:
            config_path: Path to thresholds.yaml. Defaults to shared/config/thresholds.yaml.
        """
        if config_path is None:
            config_path = str(Path(__file__).parent / "thresholds.yaml")

        with open(config_path) as f:
            self._config = yaml.safe_load(f)

        self._global = self._config["global"]
        self._domain_overrides = {
            d["scope"]: d for d in self._config.get("domain_overrides", [])
        }
        self._netting = self._config.get("netting", {})
        self._trend = self._config.get("trend", {})
        self._close_week = self._config.get("close_week", {})
        self._role_overrides = self._config.get("role_overrides", {})

    def get_thresholds(
        self,
        pl_category: Optional[str] = None,
        account_name: Optional[str] = None,
        role: Optional[str] = None,
        is_close_week: bool = False,
    ) -> dict[str, Any]:
        """Resolve thresholds with hierarchical override logic.

        Args:
            pl_category: P&L category (Revenue, COGS, OpEx, etc.)
            account_name: Specific account name for domain matching
            role: User role (cfo, board) for role overrides
            is_close_week: Whether we're in close week

        Returns:
            Dict with 'abs_threshold', 'pct_threshold', 'logic'.
        """
        # Start with global defaults
        abs_thresh = self._global["abs_threshold"]
        pct_thresh = self._global["pct_threshold"]
        logic = self._global.get("logic", "OR")

        # Domain overrides
        if pl_category and pl_category in self._domain_overrides:
            override = self._domain_overrides[pl_category]
            if "abs_threshold" in override:
                abs_thresh = override["abs_threshold"]
            if "pct_threshold" in override:
                pct_thresh = override["pct_threshold"]

        if account_name and account_name in self._domain_overrides:
            override = self._domain_overrides[account_name]
            if "abs_threshold" in override:
                abs_thresh = override["abs_threshold"]
            if "pct_threshold" in override:
                pct_thresh = override["pct_threshold"]

        # Role overrides (more specific)
        if role and role in self._role_overrides:
            override = self._role_overrides[role]
            abs_thresh = override.get("abs_threshold", abs_thresh)
            pct_thresh = override.get("pct_threshold", pct_thresh)

        # Close-week overrides (most specific)
        if is_close_week and self._close_week:
            abs_thresh = self._close_week.get("abs_threshold", abs_thresh)
            pct_thresh = self._close_week.get("pct_threshold", pct_thresh)

        return {
            "abs_threshold": abs_thresh,
            "pct_threshold": pct_thresh,
            "logic": logic,
        }

    def is_material(
        self,
        variance_amount: float,
        variance_pct: Optional[float],
        pl_category: Optional[str] = None,
        is_close_week: bool = False,
    ) -> bool:
        """Check if a variance exceeds materiality threshold.

        Uses OR logic: either absolute OR percentage breach triggers.

        Args:
            variance_amount: Absolute variance amount.
            variance_pct: Variance percentage (None if comparator=0).
            pl_category: P&L category for domain overrides.
            is_close_week: Close week flag.

        Returns:
            True if variance is material.
        """
        thresholds = self.get_thresholds(
            pl_category=pl_category, is_close_week=is_close_week
        )
        abs_breach = abs(variance_amount) >= thresholds["abs_threshold"]
        pct_breach = (
            variance_pct is not None
            and abs(variance_pct) >= thresholds["pct_threshold"]
        )
        return abs_breach or pct_breach

    @property
    def netting_ratio_threshold(self) -> float:
        """Gross/net ratio threshold for netting detection."""
        return self._netting.get("netting_ratio_threshold", 3.0)

    @property
    def child_dispersion_threshold(self) -> float:
        """Std dev threshold for child dispersion check."""
        return self._netting.get("child_dispersion_threshold", 10.0)

    @property
    def min_child_variance_pct(self) -> float:
        """Minimum child variance % to consider in netting."""
        return self._netting.get("min_child_variance_pct", 1.0)

    @property
    def cross_account_enabled(self) -> bool:
        """Whether cross-account netting is enabled."""
        return self._netting.get("cross_account_enabled", True)

    @property
    def consecutive_periods(self) -> int:
        """Minimum consecutive periods for trend detection."""
        return self._trend.get("consecutive_periods", 3)

    @property
    def cumulative_breach_enabled(self) -> bool:
        """Whether cumulative YTD breach check is enabled."""
        return self._trend.get("cumulative_breach_enabled", True)
