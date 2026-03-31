"""Pass 4 — Correlation & Root Cause Analysis.

Performs pairwise correlation scans across material variances to
identify potential causal relationships. When ``context["llm_client"]``
is available, generates LLM-powered root cause hypotheses for the top
correlated pairs. Falls back to ``hypothesis=None`` when unavailable.

Scoring formula (combined score for each pair):
    0.4 * dimension_overlap  +  0.3 * direction_match  +  0.3 * magnitude_similarity

Filters:
- Only MTD / BUDGET rows are considered.
- Pairs must score >= 0.3.
- Top 20 pairs kept (sorted descending by score).

Output: populates context["correlations"] as a DataFrame matching
the fact_correlations schema.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pandas as pd

logger = logging.getLogger(__name__)

# Scoring weights
_W_OVERLAP = 0.4
_W_DIRECTION = 0.3
_W_MAGNITUDE = 0.3

# Thresholds
_MIN_SCORE = 0.3
_MAX_PAIRS = 20

# Dimension columns used for overlap scoring
_DIM_COLS = [
    "bu_id",
    "costcenter_node_id",
    "geo_node_id",
    "segment_node_id",
    "lob_node_id",
    "account_id",
]


async def _generate_hypothesis(
    llm_client: Any, row_a: dict, row_b: dict
) -> tuple[str | None, float | None]:
    """Generate a root cause hypothesis for a correlated variance pair."""
    if (
        not llm_client
        or not hasattr(llm_client, "is_available")
        or not llm_client.is_available
    ):
        return None, None
    try:
        prompt = (
            f"These two variances are correlated:\n"
            f"1. {row_a.get('account_id', '?')}: "
            f"${row_a.get('variance_amount', 0):,.0f} "
            f"({row_a.get('variance_pct', 0):.1f}%)\n"
            f"2. {row_b.get('account_id', '?')}: "
            f"${row_b.get('variance_amount', 0):,.0f} "
            f"({row_b.get('variance_pct', 0):.1f}%)\n"
            f"Shared dimensions: {row_a.get('bu_id', '?')}\n"
            f"In 1-2 sentences, what is the most likely root cause?"
        )
        response = await llm_client.complete(
            task="hypothesis_generation",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an FP&A analyst generating root cause hypotheses "
                        "for correlated variances. Be specific and data-driven. "
                        "Also provide a confidence score from 0.0 to 1.0."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        if isinstance(response, dict) and response.get("fallback"):
            return None, None
        content = response.choices[0].message.content
        # Extract confidence if mentioned (e.g., "Confidence: 0.85")
        confidence: float | None = None
        conf_match = re.search(r"confidence[:\s]+([0-9.]+)", content, re.IGNORECASE)
        if conf_match:
            confidence = min(1.0, max(0.0, float(conf_match.group(1))))
        # Clean the hypothesis text
        hypothesis = content.split("\n")[0].strip()
        if len(hypothesis) > 500:
            hypothesis = hypothesis[:500]
        return hypothesis, confidence or 0.7
    except Exception:
        return None, None


async def find_correlations(context: dict[str, Any]) -> None:
    """Scan material variances for pairwise correlations.

    Takes material variances filtered to MTD + BUDGET. For each unique
    pair (i, j) where i < j, computes a combined score from:

    1. **Dimension overlap** — fraction of shared dimension values (0-1).
    2. **Direction match** — 1.0 if both positive or both negative, else 0.0.
    3. **Magnitude similarity** — ``1 - abs(log(abs(a)/abs(b)))`` clamped to [0, 1].

    Keeps top 20 pairs above the minimum score threshold.

    LLM hypothesis generation is deferred to Sprint 3.

    Args:
        context: Pipeline context dict. Must contain ``material_variances``.
    """
    material: pd.DataFrame = context.get("material_variances", pd.DataFrame())

    if material.empty:
        logger.warning("Pass 4: No material variances — skipping correlation scan")
        context["correlations"] = pd.DataFrame()
        return

    # ------------------------------------------------------------------
    # Filter to MTD / BUDGET only
    # ------------------------------------------------------------------
    mask = (material["view_id"] == "MTD") & (material["base_id"] == "BUDGET")
    mtd_budget = material[mask].copy()

    if len(mtd_budget) < 2:
        logger.info("Pass 4: Fewer than 2 MTD/BUDGET variances — no pairs to scan")
        context["correlations"] = pd.DataFrame()
        return

    logger.info("Pass 4: Scanning %d MTD/BUDGET variances for correlations", len(mtd_budget))

    # Convert to list of dicts for pairwise iteration
    rows = mtd_budget.to_dict("records")
    n = len(rows)

    scored_pairs: list[dict[str, Any]] = []
    # Track row refs for LLM hypothesis generation
    pair_rows: list[tuple[dict, dict]] = []

    for i in range(n):
        for j in range(i + 1, n):
            row_a = rows[i]
            row_b = rows[j]

            overlap_score, shared_dims = _dimension_overlap(row_a, row_b)
            direction_score = _direction_match(row_a, row_b)
            magnitude_score = _magnitude_similarity(row_a, row_b)

            combined = (
                _W_OVERLAP * overlap_score
                + _W_DIRECTION * direction_score
                + _W_MAGNITUDE * magnitude_score
            )

            if combined >= _MIN_SCORE:
                scored_pairs.append(
                    {
                        "correlation_id": str(uuid4()),
                        "variance_id_a": row_a["variance_id"],
                        "variance_id_b": row_b["variance_id"],
                        "correlation_score": round(combined, 4),
                        "dimension_overlap": shared_dims,
                        "directional_match": direction_score == 1.0,
                        "hypothesis": None,
                        "confidence": None,
                        "created_at": datetime.now(timezone.utc),
                    }
                )
                pair_rows.append((row_a, row_b))

    # ------------------------------------------------------------------
    # Keep top N pairs by score
    # ------------------------------------------------------------------
    # Sort pairs and row refs together
    indexed = list(enumerate(scored_pairs))
    indexed.sort(key=lambda x: x[1]["correlation_score"], reverse=True)
    top_indexed = indexed[:_MAX_PAIRS]

    top_pairs = [p for _, p in top_indexed]
    top_pair_rows = [pair_rows[i] for i, _ in top_indexed]

    # ------------------------------------------------------------------
    # LLM hypothesis generation for top pairs (rate-limited)
    # ------------------------------------------------------------------
    llm_client = context.get("llm_client")
    if llm_client and top_pairs:
        sem = asyncio.Semaphore(5)  # Max 5 concurrent LLM calls

        async def _gen_with_sem(a: dict, b: dict) -> tuple[str | None, float | None]:
            async with sem:
                return await _generate_hypothesis(llm_client, a, b)

        tasks = [_gen_with_sem(a, b) for a, b in top_pair_rows]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        hyp_count = 0
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            hypothesis, confidence = result
            if hypothesis:
                top_pairs[idx]["hypothesis"] = hypothesis
                top_pairs[idx]["confidence"] = confidence
                hyp_count += 1

        if hyp_count > 0:
            logger.info("Pass 4: Generated %d LLM hypotheses for top pairs", hyp_count)

    corr_df = pd.DataFrame(top_pairs) if top_pairs else pd.DataFrame()
    context["correlations"] = corr_df

    logger.info(
        "Pass 4: Found %d candidate pairs, kept top %d (min_score=%.2f)",
        len(scored_pairs),
        len(top_pairs),
        _MIN_SCORE,
    )


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def _dimension_overlap(
    row_a: dict[str, Any],
    row_b: dict[str, Any],
) -> tuple[float, list[str]]:
    """Compute dimension overlap score and list of shared dimension values.

    Returns:
        Tuple of (overlap_score 0-1, list of shared dimension column names).
    """
    shared: list[str] = []
    for col in _DIM_COLS:
        val_a = row_a.get(col)
        val_b = row_b.get(col)
        if val_a is not None and val_b is not None and val_a == val_b:
            shared.append(col)

    total = len(_DIM_COLS)
    score = len(shared) / total if total > 0 else 0.0
    return score, shared


def _direction_match(row_a: dict[str, Any], row_b: dict[str, Any]) -> float:
    """Return 1.0 if both variances have the same sign, 0.0 otherwise."""
    va = row_a.get("variance_amount", 0.0)
    vb = row_b.get("variance_amount", 0.0)

    if va == 0.0 or vb == 0.0:
        return 0.0

    same_sign = (va > 0 and vb > 0) or (va < 0 and vb < 0)
    return 1.0 if same_sign else 0.0


def _magnitude_similarity(row_a: dict[str, Any], row_b: dict[str, Any]) -> float:
    """Compute magnitude similarity: 1 - abs(log(abs(a)/abs(b))), clamped to [0, 1].

    When one value is zero, returns 0.0 (no similarity).
    """
    va = abs(row_a.get("variance_amount", 0.0))
    vb = abs(row_b.get("variance_amount", 0.0))

    if va == 0.0 or vb == 0.0:
        return 0.0

    try:
        log_ratio = abs(math.log(va / vb))
    except (ValueError, ZeroDivisionError):
        return 0.0

    # Clamp to [0, 1]
    return max(0.0, min(1.0, 1.0 - log_ratio))
