"""Trend Detection — 2 MVP rules for temporal variance patterns.

Identifies variances with significant temporal patterns even when the
current-period magnitude is below the materiality threshold.

MVP rules (1-2):
1. Consecutive direction — For each (account, bu, cc, base='BUDGET',
   view='MTD') key, look at variance_amount across periods sorted
   chronologically. If same sign for N+ consecutive periods (default 3)
   → flag as trending.

2. Cumulative YTD breach — For each key, sum MTD variances YTD.
   If individual periods are all below threshold but cumulative
   exceeds → flag as trending.

Phase 2 rules (3-4):
3. Monotonic acceleration — magnitude increasing each period (Phase 2).
4. Regression slope — linear regression detects slope (Phase 2).

Returns DataFrame matching fact_trend_flags schema:
    trend_id, account_id, dimension_key, rule_type,
    consecutive_periods, cumulative_amount, direction,
    period_details, created_at
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from shared.config.thresholds import ThresholdConfig
from shared.models.enums import TrendRuleType

logger = logging.getLogger(__name__)

# Dimension columns that together with account_id form a unique variance key
_DIM_COLS = [
    "account_id", "bu_id", "costcenter_node_id",
    "geo_node_id", "segment_node_id", "lob_node_id",
]


def detect_trends(
    all_variances: pd.DataFrame,
    threshold_config: ThresholdConfig,
) -> pd.DataFrame:
    """Run trend detection rules 1-2 on the full variance history.

    Filters to base='BUDGET', view='MTD', then groups by dimension key
    and checks temporal patterns across periods.

    Args:
        all_variances: Full variance DataFrame from Pass 1 containing
            all periods, with columns including account_id, bu_id,
            costcenter_node_id, geo_node_id, segment_node_id, lob_node_id,
            period_id, variance_amount, variance_pct, pl_category,
            view_id, base_id.
        threshold_config: Loaded ThresholdConfig instance.

    Returns:
        DataFrame with fact_trend_flags schema columns.
    """
    # Filter to BUDGET base and MTD view
    mask = (
        (all_variances["base_id"] == "BUDGET")
        & (all_variances["view_id"] == "MTD")
    )
    df = all_variances[mask].copy()

    if df.empty:
        logger.warning("No MTD/BUDGET variances available — skipping trend detection")
        return _empty_trend_df()

    logger.info("Trend detection: %d MTD/BUDGET rows across all periods", len(df))

    flags: list[dict[str, Any]] = []

    # Group by dimension key (account + all dimension columns)
    grouped = df.groupby(_DIM_COLS, dropna=False)

    for key, group_df in grouped:
        # Sort chronologically by period_id (YYYY-MM format sorts lexicographically)
        series = group_df.sort_values("period_id")

        account_id = key[0] if isinstance(key, tuple) else key
        dimension_key = "|".join(str(k) for k in key) if isinstance(key, tuple) else str(key)
        pl_category = series["pl_category"].iloc[0] if "pl_category" in series.columns else None

        # --- Rule 1: Consecutive direction ---
        consecutive_flags = _check_consecutive_direction(
            series=series,
            account_id=account_id,
            dimension_key=dimension_key,
            min_consecutive=threshold_config.consecutive_periods,
        )
        flags.extend(consecutive_flags)

        # --- Rule 2: Cumulative YTD breach ---
        if threshold_config.cumulative_breach_enabled:
            cumulative_flags = _check_cumulative_ytd_breach(
                series=series,
                account_id=account_id,
                dimension_key=dimension_key,
                threshold_config=threshold_config,
                pl_category=pl_category,
            )
            flags.extend(cumulative_flags)

    if not flags:
        logger.info("Trend detection: no trend patterns found")
        return _empty_trend_df()

    result = pd.DataFrame(flags)
    logger.info("Trend detection: %d trend flags generated", len(result))
    return result


# ---------------------------------------------------------------------------
# Rule 1: Consecutive direction
# ---------------------------------------------------------------------------


def _check_consecutive_direction(
    series: pd.DataFrame,
    account_id: str,
    dimension_key: str,
    min_consecutive: int,
) -> list[dict[str, Any]]:
    """Rule 1 — Check for N+ consecutive periods with variance in the same sign direction.

    Args:
        series: Chronologically sorted variance rows for a single dimension key.
        account_id: Account identifier.
        dimension_key: Pipe-delimited dimension key string.
        min_consecutive: Minimum consecutive periods to trigger (default 3).

    Returns:
        List of trend flag dicts (may be empty or have multiple if
        there are distinct streaks).
    """
    flags: list[dict[str, Any]] = []

    if len(series) < min_consecutive:
        return flags

    periods = series["period_id"].tolist()
    amounts = series["variance_amount"].tolist()

    # Track consecutive streaks
    streak_start = 0
    current_sign: int | None = None

    for i, amt in enumerate(amounts):
        if abs(amt) < 1e-10:
            # Zero variance breaks the streak
            if current_sign is not None and (i - streak_start) >= min_consecutive:
                flags.append(_make_consecutive_flag(
                    account_id, dimension_key,
                    periods[streak_start:i], amounts[streak_start:i],
                    current_sign,
                ))
            streak_start = i + 1
            current_sign = None
            continue

        sign = 1 if amt > 0 else -1

        if sign != current_sign:
            # Sign changed — check if previous streak qualifies
            if current_sign is not None and (i - streak_start) >= min_consecutive:
                flags.append(_make_consecutive_flag(
                    account_id, dimension_key,
                    periods[streak_start:i], amounts[streak_start:i],
                    current_sign,
                ))
            streak_start = i
            current_sign = sign

    # Check final streak
    if current_sign is not None and (len(amounts) - streak_start) >= min_consecutive:
        flags.append(_make_consecutive_flag(
            account_id, dimension_key,
            periods[streak_start:], amounts[streak_start:],
            current_sign,
        ))

    return flags


def _make_consecutive_flag(
    account_id: str,
    dimension_key: str,
    periods: list[str],
    amounts: list[float],
    sign: int,
) -> dict[str, Any]:
    """Build a trend flag dict for a consecutive direction streak."""
    direction = "increasing" if sign > 0 else "decreasing"
    cumulative = sum(amounts)
    period_details = [
        {"period_id": p, "variance_amount": float(a)}
        for p, a in zip(periods, amounts)
    ]

    return {
        "trend_id": str(uuid4()),
        "account_id": account_id,
        "dimension_key": dimension_key,
        "rule_type": TrendRuleType.CONSECUTIVE_DIRECTION.value,
        "consecutive_periods": len(periods),
        "cumulative_amount": float(cumulative),
        "direction": direction,
        "period_details": period_details,
        "created_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# Rule 2: Cumulative YTD breach
# ---------------------------------------------------------------------------


def _check_cumulative_ytd_breach(
    series: pd.DataFrame,
    account_id: str,
    dimension_key: str,
    threshold_config: ThresholdConfig,
    pl_category: str | None,
) -> list[dict[str, Any]]:
    """Rule 2 — Check if cumulative YTD variance breaches materiality
    even though individual MTD periods are all below threshold.

    Groups periods by fiscal_year and checks each year independently.

    Args:
        series: Chronologically sorted variance rows for a single dimension key.
        account_id: Account identifier.
        dimension_key: Pipe-delimited dimension key string.
        threshold_config: For checking individual and cumulative materiality.
        pl_category: P&L category for threshold resolution.

    Returns:
        List of trend flag dicts.
    """
    flags: list[dict[str, Any]] = []

    if "fiscal_year" not in series.columns:
        return flags

    for fy, fy_group in series.groupby("fiscal_year"):
        fy_sorted = fy_group.sort_values("period_id")
        periods = fy_sorted["period_id"].tolist()
        amounts = fy_sorted["variance_amount"].tolist()
        pcts = fy_sorted["variance_pct"].tolist()

        # Check: are ALL individual periods below threshold?
        all_below = True
        for amt, pct in zip(amounts, pcts):
            pct_val = pct if pd.notna(pct) else None
            if threshold_config.is_material(amt, pct_val, pl_category=pl_category):
                all_below = False
                break

        if not all_below:
            # At least one period is individually material — not a cumulative-only breach
            continue

        # Compute cumulative YTD
        cumulative = sum(amounts)
        # Use the cumulative amount against the same threshold to check breach
        # For cumulative pct, we'd need cumulative comparator — approximate with avg pct
        valid_pcts = [p for p in pcts if pd.notna(p)]
        avg_pct = float(np.mean(valid_pcts)) if valid_pcts else None

        if threshold_config.is_material(cumulative, avg_pct, pl_category=pl_category):
            period_details = [
                {"period_id": p, "variance_amount": float(a)}
                for p, a in zip(periods, amounts)
            ]

            direction = "increasing" if cumulative > 0 else "decreasing"

            flags.append({
                "trend_id": str(uuid4()),
                "account_id": account_id,
                "dimension_key": dimension_key,
                "rule_type": TrendRuleType.CUMULATIVE_YTD_BREACH.value,
                "consecutive_periods": len(periods),
                "cumulative_amount": float(cumulative),
                "direction": direction,
                "period_details": period_details,
                "created_at": datetime.now(timezone.utc),
            })

    return flags


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_trend_df() -> pd.DataFrame:
    """Return an empty DataFrame with the fact_trend_flags schema."""
    return pd.DataFrame(columns=[
        "trend_id", "account_id", "dimension_key", "rule_type",
        "consecutive_periods", "cumulative_amount", "direction",
        "period_details", "created_at",
    ])
