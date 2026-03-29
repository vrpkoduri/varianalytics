"""Pass 1.5 — Netting Detection.

Identifies summary hierarchy nodes where child variances offset each
other, causing the parent to appear immaterial even though significant
movements exist underneath.

Four netting checks (MVP):
1. Gross offset ratio — sum(abs(children)) / abs(parent) > 3.0
2. Dispersion — std dev of child variance_pcts > 10pp
3. Directional split — parent below threshold with children in both directions
4. Cross-account — revenue and cost variances offset within a dimension slice

Summary nodes below the materiality threshold but flagged as netted
are promoted to Pass 2 as "netted" qualification type.

Output: populates context["netting_flags"] with fact_netting_flags DataFrame.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from services.computation.detection.netting import detect_netting as run_netting_detection
from shared.config.thresholds import ThresholdConfig

logger = logging.getLogger(__name__)


async def detect_netting(context: dict[str, Any]) -> None:
    """Run netting detection checks on hierarchy summary nodes.

    Reads context["all_variances"] produced by Pass 1, applies the four
    MVP netting checks, and stores results in context["netting_flags"].

    Args:
        context: Pipeline context dict. Must contain:
            - all_variances: DataFrame from Pass 1
            - period_id: Current period key
    """
    all_variances: pd.DataFrame = context["all_variances"]
    period_id: str = context["period_id"]

    if all_variances.empty:
        logger.warning("Pass 1.5: No variances available — skipping netting detection")
        context["netting_flags"] = pd.DataFrame()
        return

    threshold_config = ThresholdConfig()

    logger.info(
        "Pass 1.5: Running netting detection for period=%s (%d total variance rows)",
        period_id,
        len(all_variances),
    )

    netting_flags = run_netting_detection(
        all_variances=all_variances,
        threshold_config=threshold_config,
        period_id=period_id,
    )

    context["netting_flags"] = netting_flags

    logger.info(
        "Pass 1.5: Netting detection complete — %d flags generated",
        len(netting_flags),
    )
