"""Causal Chains — links correlated variances into cause-effect narratives.

Uses Pass 4 correlation scores and hypotheses to identify the strongest
causal relationships for a given variance.

Example output:
    "Linked to Headcount (r=0.87): 15-FTE shortfall likely driving Advisory Fee decline."
"""

from __future__ import annotations

from typing import Any, Optional


# Minimum correlation score to consider as a causal link
_MIN_CAUSAL_SCORE = 0.50


def compute_causal_chain(
    correlations: list[dict[str, Any]],
    acct_meta: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Identify causal relationships from correlation data.

    Args:
        correlations: From graph.get_correlations() — partner_id, score, hypothesis.
        acct_meta: Account metadata dict for name lookups.

    Returns:
        Dict with has_causal_link, strongest_link, chain_length, note.
    """
    if not correlations:
        return {
            "has_causal_link": False,
            "strongest_link": None,
            "chain_length": 0,
            "note": "",
        }

    # Filter to meaningful correlations
    strong_links = [
        c for c in correlations
        if c.get("score", 0) >= _MIN_CAUSAL_SCORE
    ]

    if not strong_links:
        return {
            "has_causal_link": False,
            "strongest_link": None,
            "chain_length": 0,
            "note": "",
        }

    # Sort by score descending
    strong_links.sort(key=lambda x: x.get("score", 0), reverse=True)
    strongest = strong_links[0]

    # Look up partner account name
    partner_id = strongest.get("partner_id", "")
    # partner_id is a variance_id — we need to find its account
    partner_name = partner_id  # fallback
    for acct_id, meta in acct_meta.items():
        # Check if partner_id matches any known account pattern
        if acct_id in partner_id or partner_id.startswith(acct_id):
            partner_name = meta.get("account_name", acct_id)
            break

    score = strongest.get("score", 0)
    hypothesis = strongest.get("hypothesis")

    # Build the link dict
    link = {
        "partner_id": partner_id,
        "partner_account": partner_name,
        "score": round(score, 3),
        "hypothesis": hypothesis,
    }

    # Build note
    note = _build_causal_note(partner_name, score, hypothesis, len(strong_links))

    return {
        "has_causal_link": True,
        "strongest_link": link,
        "chain_length": len(strong_links),
        "note": note,
    }


def _build_causal_note(
    partner_name: str, score: float, hypothesis: Optional[str], chain_length: int
) -> str:
    note = f"Linked to {partner_name} (r={score:.2f})."
    if hypothesis and str(hypothesis) not in ("None", "nan", ""):
        note += f" {hypothesis}"
    if chain_length > 1:
        note += f" ({chain_length} total causal links detected.)"
    return note
