"""Leading/Lagging Indicators — detects early warning signals.

Cross-correlates time series of correlated accounts with time offsets
to find if one account's variance moves before another.

Example output:
    "Compensation variance moved 2 months before Revenue — staffing signal."
"""

from __future__ import annotations

from typing import Any

# Max lag to check (months)
_MAX_LAG_MONTHS = 3

# Minimum correlation to consider a lead/lag relationship
_MIN_CORRELATION = 0.60


def compute_leading_lagging(
    correlations: list[dict[str, Any]],
    period_history: list[dict[str, Any]],
    partner_histories: dict[str, list[dict[str, Any]]],
    acct_meta: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Detect leading/lagging relationships between correlated accounts.

    Args:
        correlations: From graph.get_correlations() — partner_id, score.
        period_history: This account's variance history (sorted oldest-first).
        partner_histories: Dict of partner_id → their variance history.
        acct_meta: Account metadata for name lookups.

    Returns:
        Dict with has_lead_lag, leading_account, lag_months, note.
    """
    if not correlations or not period_history or len(period_history) < 4:
        return _empty_result()

    # Only check strongly correlated partners
    strong = [c for c in correlations if c.get("score", 0) >= _MIN_CORRELATION]
    if not strong:
        return _empty_result()

    best_lead: dict[str, Any] | None = None
    best_corr = 0.0

    for corr in strong:
        partner_id = corr.get("partner_id", "")
        partner_history = partner_histories.get(partner_id, [])

        if not partner_history or len(partner_history) < 4:
            continue

        # Build aligned time series
        my_series = {h["period_id"]: h.get("variance_pct", 0) for h in period_history if h.get("period_id")}
        partner_series = {h["period_id"]: h.get("variance_pct", 0) for h in partner_history if h.get("period_id")}

        # Test each lag offset
        for lag in range(1, _MAX_LAG_MONTHS + 1):
            # Check if partner leads (partner's value at t predicts mine at t+lag)
            r = _cross_correlate(partner_series, my_series, lag)
            if r is not None and abs(r) > best_corr:
                best_corr = abs(r)
                partner_name = _get_name(partner_id, acct_meta)
                best_lead = {
                    "partner_id": partner_id,
                    "partner_name": partner_name,
                    "lag_months": lag,
                    "cross_correlation": round(r, 3),
                    "direction": "leads",
                }

            # Check if I lead the partner
            r_reverse = _cross_correlate(my_series, partner_series, lag)
            if r_reverse is not None and abs(r_reverse) > best_corr:
                best_corr = abs(r_reverse)
                partner_name = _get_name(partner_id, acct_meta)
                best_lead = {
                    "partner_id": partner_id,
                    "partner_name": partner_name,
                    "lag_months": lag,
                    "cross_correlation": round(r_reverse, 3),
                    "direction": "lags",
                }

    if not best_lead or best_corr < _MIN_CORRELATION:
        return _empty_result()

    note = _build_note(best_lead)

    return {
        "has_lead_lag": True,
        "leading_account": best_lead["partner_name"],
        "lag_months": best_lead["lag_months"],
        "cross_correlation": best_lead["cross_correlation"],
        "direction": best_lead["direction"],
        "note": note,
    }


def _cross_correlate(
    series_a: dict[str, float],
    series_b: dict[str, float],
    lag: int,
) -> float | None:
    """Compute simple cross-correlation with time offset.

    Checks if series_a at time t correlates with series_b at time t+lag.
    Returns Pearson-like correlation coefficient, or None if insufficient data.
    """
    # Build aligned periods
    periods_a = sorted(series_a.keys())
    pairs = []

    for i, p in enumerate(periods_a):
        if i + lag < len(periods_a):
            future_period = periods_a[i + lag]
            if p in series_a and future_period in series_b:
                pairs.append((series_a[p], series_b[future_period]))

    if len(pairs) < 3:
        return None

    # Simple Pearson correlation
    n = len(pairs)
    x = [p[0] for p in pairs]
    y = [p[1] for p in pairs]

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
    std_x = (sum((xi - mean_x) ** 2 for xi in x) / n) ** 0.5
    std_y = (sum((yi - mean_y) ** 2 for yi in y) / n) ** 0.5

    if std_x == 0 or std_y == 0:
        return None

    return cov / (std_x * std_y)


def _get_name(partner_id: str, acct_meta: dict | None) -> str:
    if not acct_meta:
        return partner_id
    for acct_id, meta in acct_meta.items():
        if acct_id in partner_id:
            return meta.get("account_name", acct_id)
    return partner_id


def _build_note(lead: dict[str, Any]) -> str:
    name = lead["partner_name"]
    lag = lead["lag_months"]
    direction = lead["direction"]
    r = lead["cross_correlation"]

    if direction == "leads":
        return f"{name} moves {lag} month(s) ahead (r={r:.2f}) — potential leading indicator."
    else:
        return f"This account leads {name} by {lag} month(s) (r={r:.2f})."


def _empty_result() -> dict[str, Any]:
    return {
        "has_lead_lag": False,
        "leading_account": None,
        "lag_months": 0,
        "cross_correlation": 0.0,
        "direction": None,
        "note": "",
    }
