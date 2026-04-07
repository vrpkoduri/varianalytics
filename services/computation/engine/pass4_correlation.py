"""Pass 4 — Correlation & Root Cause Analysis (Multi-Base, Cross-Period).

Performs pairwise correlation scans across material variances to
identify potential causal relationships. Runs for each comparison base
(Budget, Forecast, Prior Year) independently at MTD level.

**Within-Period Scoring** (combined score for each pair):
    0.4 * dimension_overlap  +  0.3 * direction_match  +  0.3 * magnitude_similarity

**Cross-Period Analysis** (3 types, per base):
    1. Persistent variances — same account+BU unfavorable across consecutive periods
    2. Lead-lag patterns — variance A in period T precedes correlated variance B in T+1
    3. Year-over-year echoes — same variance recurred vs prior year same month

Filters:
- MTD only (QTD/YTD are derived from MTD — same pairs, inflated amounts).
- All 3 bases processed independently.
- Within-period: pairs score >= 0.3, top 20 per base.
- Cross-period: top 10 per type per base.

Output: populates context["correlations"] as a DataFrame with
``correlation_type`` and ``base_id`` columns.
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
_MAX_PAIRS = 20  # Per base
_MAX_CROSS_PERIOD_PAIRS = 10  # Per cross-period type per base

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

# Base labels for logging and LLM prompts
_BASE_LABELS = {"BUDGET": "Budget", "FORECAST": "Forecast", "PRIOR_YEAR": "Prior Year"}


async def _generate_hypothesis(
    llm_client: Any, row_a: dict, row_b: dict,
    correlation_type: str = "within_period", base_label: str = "Budget",
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
            f"These two variances vs {base_label} are correlated "
            f"({type_context.get(correlation_type, 'related')}):\n"
            f"1. {row_a.get('account_id', '?')} ({row_a.get('period_id', '?')}): "
            f"${row_a.get('variance_amount', 0):,.0f} "
            f"({row_a.get('variance_pct', 0):.1f}%)\n"
            f"2. {row_b.get('account_id', '?')} ({row_b.get('period_id', '?')}): "
            f"${row_b.get('variance_amount', 0):,.0f} "
            f"({row_b.get('variance_pct', 0):.1f}%)\n"
            f"Shared dimensions: {row_a.get('bu_id', '?')}\n"
            f"Comparison base: {base_label}\n"
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

    Processes each comparison base (Budget, Forecast, PY) independently
    at MTD level. QTD/YTD are skipped (derived from MTD — same pairs).

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
    existing_material: pd.DataFrame | None = context.get("existing_material")

    # Identify all bases present in MTD data
    mtd_data = material[material["view_id"] == "MTD"] if "view_id" in material.columns else material
    if "base_id" in mtd_data.columns:
        bases = sorted(mtd_data["base_id"].unique().tolist())
    else:
        bases = ["BUDGET"]

    all_pairs: list[dict[str, Any]] = []
    all_pair_rows: list[tuple[dict, dict]] = []

    for base_id in bases:
        base_label = _BASE_LABELS.get(base_id, base_id)

        # ------------------------------------------------------------------
        # 1. Within-Period Correlations for this base
        # ------------------------------------------------------------------
        if "base_id" in material.columns:
            mask = (material["view_id"] == "MTD") & (material["base_id"] == base_id)
        else:
            mask = material["view_id"] == "MTD" if "view_id" in material.columns else pd.Series(True, index=material.index)
        mtd_base = material[mask].copy()

        within_pairs: list[dict[str, Any]] = []
        within_pair_rows: list[tuple[dict, dict]] = []

        if len(mtd_base) >= 2:
            logger.info(
                "Pass 4: Scanning %d MTD/%s variances for within-period correlations",
                len(mtd_base), base_id,
            )
            rows = mtd_base.to_dict("records")
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
                                "base_id": base_id,
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

        # Sort and keep top N within-period for this base
        indexed = list(enumerate(within_pairs))
        indexed.sort(key=lambda x: x[1]["correlation_score"], reverse=True)
        top_indexed = indexed[:_MAX_PAIRS]

        top_within = [p for _, p in top_indexed]
        top_within_rows = [within_pair_rows[i] for i, _ in top_indexed]

        all_pairs.extend(top_within)
        all_pair_rows.extend(top_within_rows)

        logger.info(
            "Pass 4: [%s] Found %d within-period pairs, kept top %d",
            base_id, len(within_pairs), len(top_within),
        )

        # ------------------------------------------------------------------
        # 2. Cross-Period Correlations for this base
        # ------------------------------------------------------------------
        if existing_material is not None and not existing_material.empty and period_id:
            if "base_id" in existing_material.columns:
                em_mask = (
                    (existing_material["view_id"] == "MTD")
                    & (existing_material["base_id"] == base_id)
                )
            else:
                em_mask = existing_material["view_id"] == "MTD" if "view_id" in existing_material.columns else pd.Series(True, index=existing_material.index)
            prior_mtd = existing_material[em_mask].copy()

            if not prior_mtd.empty:
                # --- 2a. Persistent Variances ---
                persistent = _find_persistent_variances(
                    current=mtd_base, prior=prior_mtd, period_id=period_id,
                    base_id=base_id,
                )
                all_pairs.extend(persistent["pairs"])
                all_pair_rows.extend(persistent["rows"])

                # --- 2b. Lead-Lag Patterns ---
                lead_lag = _find_lead_lag_patterns(
                    current=mtd_base, prior=prior_mtd, period_id=period_id,
                    base_id=base_id,
                )
                all_pairs.extend(lead_lag["pairs"])
                all_pair_rows.extend(lead_lag["rows"])

                # --- 2c. Year-over-Year Echoes ---
                yoy = _find_yoy_echoes(
                    current=mtd_base, prior=prior_mtd, period_id=period_id,
                    base_id=base_id,
                )
                all_pairs.extend(yoy["pairs"])
                all_pair_rows.extend(yoy["rows"])

                logger.info(
                    "Pass 4: [%s] Cross-period: %d persistent, %d lead-lag, %d YoY",
                    base_id, len(persistent["pairs"]),
                    len(lead_lag["pairs"]), len(yoy["pairs"]),
                )
        else:
            if base_id == bases[0]:  # Log once, not per base
                logger.info(
                    "Pass 4: No prior period data — skipping cross-period analysis"
                )

    # ------------------------------------------------------------------
    # 3. LLM hypothesis generation for all top pairs (across all bases)
    # ------------------------------------------------------------------
    llm_client = context.get("llm_client")
    if llm_client and all_pairs:
        sem = asyncio.Semaphore(15)  # Max 15 concurrent LLM calls

        async def _gen_with_sem(
            a: dict, b: dict, ctype: str, blabel: str,
        ) -> tuple[str | None, float | None]:
            async with sem:
                return await _generate_hypothesis(llm_client, a, b, ctype, blabel)

        tasks = [
            _gen_with_sem(
                a, b, pair["correlation_type"],
                _BASE_LABELS.get(pair.get("base_id", "BUDGET"), "Budget"),
            )
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

    # Summary by type and base
    type_base_counts: dict[str, int] = {}
    for p in all_pairs:
        key = f"{p.get('base_id', '?')}/{p.get('correlation_type', '?')}"
        type_base_counts[key] = type_base_counts.get(key, 0) + 1

    logger.info(
        "Pass 4: Total %d correlations across %d bases — %s",
        len(all_pairs),
        len(bases),
        ", ".join(f"{k}={v}" for k, v in sorted(type_base_counts.items())),
    )


# ===========================================================================
# Cross-Period Analysis: Persistent Variances
# ===========================================================================


def _find_persistent_variances(
    current: pd.DataFrame,
    prior: pd.DataFrame,
    period_id: str,
    base_id: str = "BUDGET",
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

    base_label = _BASE_LABELS.get(base_id, base_id)

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
            persistence_score = min(1.0, consecutive / 6.0)
            mag_score = _magnitude_similarity(curr_row, earliest_row)
            combined = 0.5 * persistence_score + 0.3 * mag_score + 0.2

            pair_data = {
                "correlation_id": str(uuid4()),
                "variance_id_a": earliest_row.get("variance_id", str(uuid4())),
                "variance_id_b": curr_row.get("variance_id", str(uuid4())),
                "base_id": base_id,
                "correlation_score": round(combined, 4),
                "correlation_type": "persistent",
                "dimension_overlap": list(_CROSS_PERIOD_KEY_COLS),
                "directional_match": True,
                "hypothesis": (
                    f"Persistent {consecutive + 1}-month pattern vs {base_label}: "
                    f"{curr_row.get('account_id', '?')} in {curr_row.get('bu_id', '?')} "
                    f"has been {'unfavorable' if curr_sign < 0 else 'favorable'} "
                    f"for {consecutive + 1} consecutive months "
                    f"(cumulative ${abs(total_prior_amount + curr_amount):,.0f})"
                ),
                "confidence": None,
                "created_at": datetime.now(timezone.utc),
            }
            scored.append((combined, pair_data, earliest_row, curr_row, consecutive))

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
    base_id: str = "BUDGET",
) -> dict[str, list]:
    """Find lead-lag: variance in account A last period → account B this period.

    Looks for DIFFERENT accounts within the same BU where a variance in
    the immediately prior period is followed by a related variance in the
    current period.

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

    prior_prev = prior[prior["period_id"] == prior_period]
    if prior_prev.empty:
        return {"pairs": pairs, "rows": rows}

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

        for pr in pr_rows:
            pr_acct = pr.get("account_id", "")
            pr_amount = pr.get("variance_amount", 0)
            if pr_amount == 0:
                continue

            for cr in curr_rows:
                cr_acct = cr.get("account_id", "")
                if cr_acct == pr_acct:
                    continue

                cr_amount = cr.get("variance_amount", 0)
                if cr_amount == 0:
                    continue

                direction = _direction_match(pr, cr)
                magnitude = _magnitude_similarity(pr, cr)
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
                        "base_id": base_id,
                        "correlation_score": round(combined, 4),
                        "correlation_type": "lead_lag",
                        "dimension_overlap": shared,
                        "directional_match": direction == 1.0,
                        "hypothesis": None,
                        "confidence": None,
                        "created_at": datetime.now(timezone.utc),
                    }))

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
    base_id: str = "BUDGET",
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

    base_label = _BASE_LABELS.get(base_id, base_id)

    prior_yoy = prior[prior["period_id"] == yoy_period]
    if prior_yoy.empty:
        return {"pairs": pairs, "rows": rows}

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

        combined = 0.4 * direction + 0.4 * magnitude + 0.2

        if combined >= _MIN_SCORE:
            curr_sign = "unfavorable" if curr_amount < 0 else "favorable"
            scored.append((combined, pr_row, curr_row, {
                "correlation_id": str(uuid4()),
                "variance_id_a": pr_row.get("variance_id", str(uuid4())),
                "variance_id_b": curr_row.get("variance_id", str(uuid4())),
                "base_id": base_id,
                "correlation_score": round(combined, 4),
                "correlation_type": "yoy_echo",
                "dimension_overlap": list(_CROSS_PERIOD_KEY_COLS),
                "directional_match": direction == 1.0,
                "hypothesis": (
                    f"YoY echo vs {base_label}: {curr_row.get('account_id', '?')} in "
                    f"{curr_row.get('bu_id', '?')} was also {curr_sign} "
                    f"in {yoy_period} (${pr_amount:,.0f} then vs "
                    f"${curr_amount:,.0f} now) — potential seasonal/structural pattern"
                ),
                "confidence": None,
                "created_at": datetime.now(timezone.utc),
            }))

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
    """Compute dimension overlap score and list of shared dimension values."""
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
    """Compute magnitude similarity: 1 - abs(log(abs(a)/abs(b))), clamped to [0, 1]."""
    va = abs(row_a.get("variance_amount", 0.0))
    vb = abs(row_b.get("variance_amount", 0.0))

    if va == 0.0 or vb == 0.0:
        return 0.0

    try:
        log_ratio = abs(math.log(va / vb))
    except (ValueError, ZeroDivisionError):
        return 0.0

    return max(0.0, min(1.0, 1.0 - log_ratio))
