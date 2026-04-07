"""Pass 4 — Correlation & Root Cause Analysis (Cross-Period Enhanced).

Performs pairwise correlation scans across material variances to
identify potential causal relationships. Enhanced with cross-period
analysis for period-over-period and year-over-year causal patterns.

**Within-Period Scoring** (combined score for each pair):
    0.4 * dimension_overlap  +  0.3 * direction_match  +  0.3 * magnitude_similarity

**Cross-Period Analysis** (3 types):
    1. Persistent variances — same account+BU unfavorable across consecutive periods
    2. Lead-lag patterns — variance A in period T precedes correlated variance B in T+1
    3. Year-over-year echoes — same variance recurred vs prior year same month

Filters:
- Within-period: Only MTD / BUDGET rows. Pairs score >= 0.3. Top 20 kept.
- Cross-period: Uses existing_material from prior periods. Top 10 persistent,
  top 10 lead-lag, top 10 YoY echoes.

Output: populates context["correlations"] as a DataFrame matching
the fact_correlations schema, with a ``correlation_type`` column
distinguishing within_period / persistent / lead_lag / yoy_echo.
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

# Scoring weights (within-period)
_W_OVERLAP = 0.4
_W_DIRECTION = 0.3
_W_MAGNITUDE = 0.3

# Thresholds
_MIN_SCORE = 0.3
_MAX_PAIRS = 20
_MAX_CROSS_PERIOD_PAIRS = 10  # Per cross-period type

# Dimension columns used for overlap scoring
_DIM_COLS = [
    "bu_id",
    "costcenter_node_id",
    "geo_node_id",
    "segment_node_id",
    "lob_node_id",
    "account_id",
]

# Grouping columns for cross-period matching (account + BU grain)
_CROSS_PERIOD_KEY_COLS = ["account_id", "bu_id"]

# Finer grain for lead-lag (includes cost center and geo)
_LEAD_LAG_KEY_COLS = ["account_id", "bu_id", "costcenter_node_id", "geo_node_id"]


async def _generate_hypothesis(
    llm_client: Any, row_a: dict, row_b: dict, correlation_type: str = "within_period"
) -> tuple[str | None, float | None]:
    """Generate a root cause hypothesis for a correlated variance pair."""
    if (
        not llm_client
        or not hasattr(llm_client, "is_available")
        or not llm_client.is_available
    ):
        return None, None
    try:
        type_context = {
            "within_period": "in the same period",
            "persistent": "persisting across multiple consecutive periods",
            "lead_lag": "where the first variance preceded and likely caused the second in the following period",
            "yoy_echo": "recurring in the same month as the prior year",
        }

        prompt = (
            f"These two variances are correlated ({type_context.get(correlation_type, 'related')}):\n"
            f"1. {row_a.get('account_id', '?')} ({row_a.get('period_id', '?')}): "
            f"${row_a.get('variance_amount', 0):,.0f} "
            f"({row_a.get('variance_pct', 0):.1f}%)\n"
            f"2. {row_b.get('account_id', '?')} ({row_b.get('period_id', '?')}): "
            f"${row_b.get('variance_amount', 0):,.0f} "
            f"({row_b.get('variance_pct', 0):.1f}%)\n"
            f"Shared dimensions: {row_a.get('bu_id', '?')}\n"
            f"Correlation type: {correlation_type}\n"
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
                        "For cross-period correlations, focus on structural or "
                        "operational causes that persist over time. "
                        "Also provide a confidence score from 0.0 to 1.0."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        if isinstance(response, dict) and response.get("fallback"):
            return None, None
        content = response.choices[0].message.content
        confidence: float | None = None
        conf_match = re.search(r"confidence[:\s]+([0-9.]+)", content, re.IGNORECASE)
        if conf_match:
            confidence = min(1.0, max(0.0, float(conf_match.group(1))))
        hypothesis = content.split("\n")[0].strip()
        if len(hypothesis) > 500:
            hypothesis = hypothesis[:500]
        return hypothesis, confidence or 0.7
    except Exception:
        return None, None


async def find_correlations(context: dict[str, Any]) -> None:
    """Scan material variances for within-period and cross-period correlations.

    Takes material variances filtered to MTD + BUDGET. For within-period:
    computes pairwise scores. For cross-period: analyzes persistent patterns,
    lead-lag relationships, and year-over-year echoes using existing_material.

    Args:
        context: Pipeline context dict. Must contain ``material_variances``.
            Optional ``existing_material`` for cross-period analysis.
    """
    material: pd.DataFrame = context.get("material_variances", pd.DataFrame())

    if material.empty:
        logger.warning("Pass 4: No material variances — skipping correlation scan")
        context["correlations"] = pd.DataFrame()
        return

    period_id = context.get("period_id", "")

    # ------------------------------------------------------------------
    # 1. Within-Period Correlations (original logic)
    # ------------------------------------------------------------------
    mask = (material["view_id"] == "MTD") & (material["base_id"] == "BUDGET")
    mtd_budget = material[mask].copy()

    within_pairs: list[dict[str, Any]] = []
    within_pair_rows: list[tuple[dict, dict]] = []

    if len(mtd_budget) >= 2:
        logger.info(
            "Pass 4: Scanning %d MTD/BUDGET variances for within-period correlations",
            len(mtd_budget),
        )
        rows = mtd_budget.to_dict("records")
        n = len(rows)

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
                    within_pairs.append(
                        {
                            "correlation_id": str(uuid4()),
                            "variance_id_a": row_a["variance_id"],
                            "variance_id_b": row_b["variance_id"],
                            "correlation_score": round(combined, 4),
                            "correlation_type": "within_period",
                            "dimension_overlap": shared_dims,
                            "directional_match": direction_score == 1.0,
                            "hypothesis": None,
                            "confidence": None,
                            "created_at": datetime.now(timezone.utc),
                        }
                    )
                    within_pair_rows.append((row_a, row_b))

    # Sort and keep top N within-period
    indexed = list(enumerate(within_pairs))
    indexed.sort(key=lambda x: x[1]["correlation_score"], reverse=True)
    top_indexed = indexed[:_MAX_PAIRS]

    top_within = [p for _, p in top_indexed]
    top_within_rows = [within_pair_rows[i] for i, _ in top_indexed]

    logger.info(
        "Pass 4: Found %d within-period pairs, kept top %d",
        len(within_pairs),
        len(top_within),
    )

    # ------------------------------------------------------------------
    # 2. Cross-Period Correlations
    # ------------------------------------------------------------------
    existing_material: pd.DataFrame | None = context.get("existing_material")
    cross_period_pairs: list[dict[str, Any]] = []
    cross_period_rows: list[tuple[dict, dict]] = []

    if existing_material is not None and not existing_material.empty and period_id:
        # Filter existing to MTD/BUDGET only
        em_mask = (
            (existing_material["view_id"] == "MTD")
            & (existing_material["base_id"] == "BUDGET")
        )
        prior_mtd = existing_material[em_mask].copy()

        if not prior_mtd.empty:
            # --- 2a. Persistent Variances ---
            persistent = _find_persistent_variances(
                current=mtd_budget, prior=prior_mtd, period_id=period_id
            )
            cross_period_pairs.extend(persistent["pairs"])
            cross_period_rows.extend(persistent["rows"])
            logger.info(
                "Pass 4: Found %d persistent cross-period correlations",
                len(persistent["pairs"]),
            )

            # --- 2b. Lead-Lag Patterns ---
            lead_lag = _find_lead_lag_patterns(
                current=mtd_budget, prior=prior_mtd, period_id=period_id
            )
            cross_period_pairs.extend(lead_lag["pairs"])
            cross_period_rows.extend(lead_lag["rows"])
            logger.info(
                "Pass 4: Found %d lead-lag cross-period correlations",
                len(lead_lag["pairs"]),
            )

            # --- 2c. Year-over-Year Echoes ---
            yoy = _find_yoy_echoes(
                current=mtd_budget, prior=prior_mtd, period_id=period_id
            )
            cross_period_pairs.extend(yoy["pairs"])
            cross_period_rows.extend(yoy["rows"])
            logger.info(
                "Pass 4: Found %d year-over-year echo correlations",
                len(yoy["pairs"]),
            )
    else:
        logger.info(
            "Pass 4: No prior period data — skipping cross-period analysis"
        )

    # ------------------------------------------------------------------
    # 3. Combine all pairs
    # ------------------------------------------------------------------
    all_pairs = top_within + cross_period_pairs
    all_pair_rows = top_within_rows + cross_period_rows

    # ------------------------------------------------------------------
    # 4. LLM hypothesis generation for all top pairs
    # ------------------------------------------------------------------
    llm_client = context.get("llm_client")
    if llm_client and all_pairs:
        sem = asyncio.Semaphore(15)  # Max 15 concurrent LLM calls

        async def _gen_with_sem(
            a: dict, b: dict, ctype: str
        ) -> tuple[str | None, float | None]:
            async with sem:
                return await _generate_hypothesis(llm_client, a, b, ctype)

        tasks = [
            _gen_with_sem(a, b, pair["correlation_type"])
            for (a, b), pair in zip(all_pair_rows, all_pairs)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        hyp_count = 0
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            hypothesis, confidence = result
            if hypothesis:
                all_pairs[idx]["hypothesis"] = hypothesis
                all_pairs[idx]["confidence"] = confidence
                hyp_count += 1

        if hyp_count > 0:
            logger.info("Pass 4: Generated %d LLM hypotheses for all pairs", hyp_count)

    corr_df = pd.DataFrame(all_pairs) if all_pairs else pd.DataFrame()
    context["correlations"] = corr_df

    # Summary
    type_counts = {}
    for p in all_pairs:
        t = p.get("correlation_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    logger.info(
        "Pass 4: Total %d correlations — %s",
        len(all_pairs),
        ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items())),
    )


# ===========================================================================
# Cross-Period Analysis: Persistent Variances
# ===========================================================================


def _find_persistent_variances(
    current: pd.DataFrame,
    prior: pd.DataFrame,
    period_id: str,
) -> dict[str, list]:
    """Find account+BU combinations that are unfavorable across consecutive periods.

    A persistent variance = same account+BU had material variance in 2+
    prior periods AND in the current period, with the same sign direction.

    Returns:
        Dict with 'pairs' (correlation dicts) and 'rows' (row pairs for LLM).
    """
    pairs: list[dict[str, Any]] = []
    rows: list[tuple[dict, dict]] = []

    if current.empty or prior.empty:
        return {"pairs": pairs, "rows": rows}

    # Group current period variances by account+BU
    current_keys = {}
    for _, row in current.iterrows():
        key = tuple(str(row.get(c, "")) for c in _CROSS_PERIOD_KEY_COLS)
        current_keys[key] = row.to_dict()

    # Group prior period variances by account+BU+period
    prior_by_key: dict[tuple, list[dict]] = {}
    for _, row in prior.iterrows():
        key = tuple(str(row.get(c, "")) for c in _CROSS_PERIOD_KEY_COLS)
        prior_by_key.setdefault(key, []).append(row.to_dict())

    scored: list[tuple[float, dict, dict, dict, int]] = []

    for key, curr_row in current_keys.items():
        if key not in prior_by_key:
            continue

        prior_rows = prior_by_key[key]
        curr_amount = curr_row.get("variance_amount", 0)
        if curr_amount == 0:
            continue

        curr_sign = 1 if curr_amount > 0 else -1

        # Count consecutive prior periods with same sign
        # Sort prior rows by period descending (most recent first)
        sorted_prior = sorted(
            prior_rows,
            key=lambda r: r.get("period_id", ""),
            reverse=True,
        )

        consecutive = 0
        total_prior_amount = 0.0
        earliest_row = None

        for pr in sorted_prior:
            pr_amount = pr.get("variance_amount", 0)
            if pr_amount == 0:
                break
            pr_sign = 1 if pr_amount > 0 else -1
            if pr_sign == curr_sign:
                consecutive += 1
                total_prior_amount += pr_amount
                earliest_row = pr
            else:
                break

        if consecutive >= 2 and earliest_row is not None:
            # Score: more consecutive periods + larger magnitude = higher score
            persistence_score = min(1.0, consecutive / 6.0)  # 6+ months = 1.0
            mag_score = _magnitude_similarity(curr_row, earliest_row)
            combined = 0.5 * persistence_score + 0.3 * mag_score + 0.2

            pair_data = {
                "correlation_id": str(uuid4()),
                "variance_id_a": earliest_row.get("variance_id", str(uuid4())),
                "variance_id_b": curr_row.get("variance_id", str(uuid4())),
                "correlation_score": round(combined, 4),
                "correlation_type": "persistent",
                "dimension_overlap": list(_CROSS_PERIOD_KEY_COLS),
                "directional_match": True,
                "hypothesis": (
                    f"Persistent {consecutive + 1}-month pattern: "
                    f"{curr_row.get('account_id', '?')} in {curr_row.get('bu_id', '?')} "
                    f"has been {'unfavorable' if curr_sign < 0 else 'favorable'} "
                    f"for {consecutive + 1} consecutive months "
                    f"(cumulative ${abs(total_prior_amount + curr_amount):,.0f})"
                ),
                "confidence": None,
                "created_at": datetime.now(timezone.utc),
            }
            scored.append((combined, pair_data, earliest_row, curr_row, consecutive))

    # Keep top N by score
    scored.sort(key=lambda x: x[0], reverse=True)
    for _, pair_data, prior_row, curr_row, _ in scored[:_MAX_CROSS_PERIOD_PAIRS]:
        pairs.append(pair_data)
        rows.append((prior_row, curr_row))

    return {"pairs": pairs, "rows": rows}


# ===========================================================================
# Cross-Period Analysis: Lead-Lag Patterns
# ===========================================================================


def _find_lead_lag_patterns(
    current: pd.DataFrame,
    prior: pd.DataFrame,
    period_id: str,
) -> dict[str, list]:
    """Find lead-lag: variance in account A last period → account B this period.

    Looks for DIFFERENT accounts within the same BU where a variance in
    the immediately prior period is followed by a related variance in the
    current period. Classic examples: Revenue drop → COGS mismatch,
    Headcount increase → salary overspend.

    Returns:
        Dict with 'pairs' and 'rows'.
    """
    pairs: list[dict[str, Any]] = []
    rows: list[tuple[dict, dict]] = []

    if current.empty or prior.empty:
        return {"pairs": pairs, "rows": rows}

    prior_period = _get_prior_period(period_id)
    if not prior_period:
        return {"pairs": pairs, "rows": rows}

    # Filter prior to immediately preceding period only
    prior_prev = prior[prior["period_id"] == prior_period]
    if prior_prev.empty:
        return {"pairs": pairs, "rows": rows}

    # Group by BU for cross-account matching
    current_by_bu: dict[str, list[dict]] = {}
    for _, row in current.iterrows():
        bu = str(row.get("bu_id", ""))
        current_by_bu.setdefault(bu, []).append(row.to_dict())

    prior_by_bu: dict[str, list[dict]] = {}
    for _, row in prior_prev.iterrows():
        bu = str(row.get("bu_id", ""))
        prior_by_bu.setdefault(bu, []).append(row.to_dict())

    scored: list[tuple[float, dict, dict, dict]] = []

    for bu_id, curr_rows in current_by_bu.items():
        if bu_id not in prior_by_bu:
            continue

        pr_rows = prior_by_bu[bu_id]

        # Cross-account pairs within same BU
        for pr in pr_rows:
            pr_acct = pr.get("account_id", "")
            pr_amount = pr.get("variance_amount", 0)
            if pr_amount == 0:
                continue

            for cr in curr_rows:
                cr_acct = cr.get("account_id", "")
                # Skip same account (that's persistence, not lead-lag)
                if cr_acct == pr_acct:
                    continue

                cr_amount = cr.get("variance_amount", 0)
                if cr_amount == 0:
                    continue

                # Score: direction match + magnitude similarity + dimension overlap
                direction = _direction_match(pr, cr)
                magnitude = _magnitude_similarity(pr, cr)
                # Partial dimension overlap (same BU = 1/6 baseline)
                overlap, shared = _dimension_overlap(pr, cr)

                combined = (
                    0.35 * direction
                    + 0.35 * magnitude
                    + 0.30 * overlap
                )

                if combined >= _MIN_SCORE:
                    scored.append((combined, pr, cr, {
                        "correlation_id": str(uuid4()),
                        "variance_id_a": pr.get("variance_id", str(uuid4())),
                        "variance_id_b": cr.get("variance_id", str(uuid4())),
                        "correlation_score": round(combined, 4),
                        "correlation_type": "lead_lag",
                        "dimension_overlap": shared,
                        "directional_match": direction == 1.0,
                        "hypothesis": None,
                        "confidence": None,
                        "created_at": datetime.now(timezone.utc),
                    }))

    # Keep top N
    scored.sort(key=lambda x: x[0], reverse=True)
    for _, pr_row, cr_row, pair_data in scored[:_MAX_CROSS_PERIOD_PAIRS]:
        pairs.append(pair_data)
        rows.append((pr_row, cr_row))

    return {"pairs": pairs, "rows": rows}


# ===========================================================================
# Cross-Period Analysis: Year-over-Year Echoes
# ===========================================================================


def _find_yoy_echoes(
    current: pd.DataFrame,
    prior: pd.DataFrame,
    period_id: str,
) -> dict[str, list]:
    """Find YoY echoes: same variance occurred in the same month last year.

    Matches account+BU from the current period against the same month
    in the prior year. If the same account had a material variance in
    both periods with the same direction, it's a structural/seasonal echo.

    Returns:
        Dict with 'pairs' and 'rows'.
    """
    pairs: list[dict[str, Any]] = []
    rows: list[tuple[dict, dict]] = []

    if current.empty or prior.empty:
        return {"pairs": pairs, "rows": rows}

    yoy_period = _get_yoy_period(period_id)
    if not yoy_period:
        return {"pairs": pairs, "rows": rows}

    # Filter prior to same-month-last-year
    prior_yoy = prior[prior["period_id"] == yoy_period]
    if prior_yoy.empty:
        return {"pairs": pairs, "rows": rows}

    # Index prior by account+BU
    prior_key_map: dict[tuple, dict] = {}
    for _, row in prior_yoy.iterrows():
        key = tuple(str(row.get(c, "")) for c in _CROSS_PERIOD_KEY_COLS)
        prior_key_map[key] = row.to_dict()

    scored: list[tuple[float, dict, dict, dict]] = []

    for _, curr_row_raw in current.iterrows():
        curr_row = curr_row_raw.to_dict()
        key = tuple(str(curr_row.get(c, "")) for c in _CROSS_PERIOD_KEY_COLS)

        if key not in prior_key_map:
            continue

        pr_row = prior_key_map[key]
        curr_amount = curr_row.get("variance_amount", 0)
        pr_amount = pr_row.get("variance_amount", 0)

        if curr_amount == 0 or pr_amount == 0:
            continue

        direction = _direction_match(curr_row, pr_row)
        magnitude = _magnitude_similarity(curr_row, pr_row)

        # YoY echo score: higher if same direction + similar magnitude
        combined = 0.4 * direction + 0.4 * magnitude + 0.2

        if combined >= _MIN_SCORE:
            curr_sign = "unfavorable" if curr_amount < 0 else "favorable"
            scored.append((combined, pr_row, curr_row, {
                "correlation_id": str(uuid4()),
                "variance_id_a": pr_row.get("variance_id", str(uuid4())),
                "variance_id_b": curr_row.get("variance_id", str(uuid4())),
                "correlation_score": round(combined, 4),
                "correlation_type": "yoy_echo",
                "dimension_overlap": list(_CROSS_PERIOD_KEY_COLS),
                "directional_match": direction == 1.0,
                "hypothesis": (
                    f"YoY echo: {curr_row.get('account_id', '?')} in "
                    f"{curr_row.get('bu_id', '?')} was also {curr_sign} "
                    f"in {yoy_period} (${pr_amount:,.0f} then vs "
                    f"${curr_amount:,.0f} now) — potential seasonal/structural pattern"
                ),
                "confidence": None,
                "created_at": datetime.now(timezone.utc),
            }))

    # Keep top N
    scored.sort(key=lambda x: x[0], reverse=True)
    for _, pr_row, cr_row, pair_data in scored[:_MAX_CROSS_PERIOD_PAIRS]:
        pairs.append(pair_data)
        rows.append((pr_row, cr_row))

    return {"pairs": pairs, "rows": rows}


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------


def _get_prior_period(period_id: str) -> str | None:
    """Return the immediately prior period (e.g. '2026-06' → '2026-05')."""
    try:
        parts = period_id.split("-")
        year, month = int(parts[0]), int(parts[1])
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        return f"{year}-{month:02d}"
    except (ValueError, IndexError):
        return None


def _get_yoy_period(period_id: str) -> str | None:
    """Return the same month in the prior year (e.g. '2026-06' → '2025-06')."""
    try:
        parts = period_id.split("-")
        year, month = int(parts[0]), int(parts[1])
        return f"{year - 1}-{month:02d}"
    except (ValueError, IndexError):
        return None


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
