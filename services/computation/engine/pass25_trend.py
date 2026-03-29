"""Pass 2.5 — Trend Detection.

Identifies variances with significant temporal patterns even if the
current-period variance is below the materiality threshold.

Two trend rules (MVP):
1. Consecutive direction — variance in the same direction for N+
   consecutive periods (default N=3).
2. Cumulative YTD breach — individual periods all below threshold
   but cumulative YTD sum exceeds materiality.

Variances flagged as trending are fed into Pass 2 threshold filter
with qualification_type = "trending".

Output: populates context["trend_flags"] with fact_trend_flags DataFrame.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from services.computation.detection.trend import detect_trends as run_trend_detection
from shared.config.thresholds import ThresholdConfig

logger = logging.getLogger(__name__)


async def detect_trends(context: dict[str, Any]) -> None:
    """Run trend detection rules on trailing variance history.

    Reads context["all_variances"] produced by Pass 1, applies the two
    MVP trend rules across all periods, and stores results in
    context["trend_flags"].

    Args:
        context: Pipeline context dict. Must contain:
            - all_variances: DataFrame from Pass 1 (all periods)
    """
    all_variances: pd.DataFrame = context["all_variances"]

    if all_variances.empty:
        logger.warning("Pass 2.5: No variances available — skipping trend detection")
        context["trend_flags"] = pd.DataFrame()
        return

    threshold_config = ThresholdConfig()

    logger.info(
        "Pass 2.5: Running trend detection on %d total variance rows",
        len(all_variances),
    )

    trend_flags = run_trend_detection(
        all_variances=all_variances,
        threshold_config=threshold_config,
    )

    context["trend_flags"] = trend_flags

    logger.info(
        "Pass 2.5: Trend detection complete — %d flags generated",
        len(trend_flags),
    )
