"""Seasonal profile configuration loader.

Provides seasonal context for narratives and trend detection.
Loads expected multipliers from seasonal_profiles.yaml.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class SeasonalConfig:
    """Seasonal profile configuration with narrative helpers.

    Loads expected seasonal multipliers per P&L category and month.
    Used to determine if a variance is "within seasonal norms" and
    to generate narrative context notes.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        if config_path is None:
            config_path = str(Path(__file__).parent / "seasonal_profiles.yaml")

        try:
            with open(config_path) as f:
                self._config = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning("Seasonal profiles not found at %s, using defaults", config_path)
            self._config = {"profiles": {}, "seasonal_tolerance": 0.10}

        self._profiles = self._config.get("profiles", {})
        self._tolerance = self._config.get("seasonal_tolerance", 0.10)
        self._high_months = set(self._config.get("high_season_months", [11, 12, 1]))
        self._low_months = set(self._config.get("low_season_months", [7, 8]))

    def get_seasonal_factor(self, pl_category: str, month: int) -> float:
        """Get expected seasonal multiplier for a category and month.

        Args:
            pl_category: P&L category (Revenue, COGS, OpEx, NonOp)
            month: Month number (1-12)

        Returns:
            Multiplier (e.g., 1.4 for December Revenue)
        """
        profile = self._profiles.get(pl_category, {})
        multipliers = profile.get("multipliers", [1.0] * 12)
        if 1 <= month <= 12 and len(multipliers) >= month:
            return multipliers[month - 1]
        return 1.0

    def is_within_seasonal_norm(
        self, pl_category: str, month: int, variance_pct: float
    ) -> bool:
        """Check if a variance percentage is within seasonal tolerance.

        A variance is "within norm" if the actual seasonal deviation
        is less than the configured tolerance.

        Args:
            pl_category: P&L category
            month: Month number (1-12)
            variance_pct: Actual variance percentage

        Returns:
            True if within seasonal expectation
        """
        factor = self.get_seasonal_factor(pl_category, month)
        if factor == 1.0:
            return False  # No seasonal pattern → can't be "within norm"

        # Expected deviation from average = (factor - 1.0) * 100
        expected_pct = (factor - 1.0) * 100
        actual_pct = abs(variance_pct) if variance_pct else 0

        # Check if actual is within tolerance of expected seasonal deviation
        if abs(actual_pct - abs(expected_pct)) <= self._tolerance * 100:
            return True

        return False

    def get_seasonal_note(self, pl_category: str, month: int) -> str:
        """Get narrative context note for the season.

        Args:
            pl_category: P&L category
            month: Month number (1-12)

        Returns:
            Contextual note like "Consistent with December seasonal peak (1.4x)."
            or empty string if no seasonal context.
        """
        factor = self.get_seasonal_factor(pl_category, month)
        month_name = MONTH_NAMES[month] if 1 <= month <= 12 else str(month)

        if factor == 1.0:
            return ""

        if month in self._high_months:
            return f"Consistent with {month_name} seasonal peak ({factor:.1f}x normal)."
        elif month in self._low_months:
            return f"Consistent with {month_name} seasonal trough ({factor:.1f}x normal)."
        elif factor > 1.05:
            return f"In line with seasonal uplift for {month_name} ({factor:.2f}x)."
        elif factor < 0.95:
            return f"In line with seasonal softness for {month_name} ({factor:.2f}x)."

        return ""

    def is_high_season(self, month: int) -> bool:
        """Check if month is in peak season."""
        return month in self._high_months

    def is_low_season(self, month: int) -> bool:
        """Check if month is in trough season."""
        return month in self._low_months

    @property
    def tolerance(self) -> float:
        """Get the seasonal tolerance percentage."""
        return self._tolerance
