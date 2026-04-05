"""Narrative Coherence — cross-narrative consistency validation.

Heuristic checks that a narrative is consistent with its correlated
variances and siblings (e.g., if correlated variance is favorable,
this narrative shouldn't claim the opposite without explanation).

Example output:
    "Coherence warning: narrative says 'decreased' but variance is positive."
"""

from __future__ import annotations

import re
from typing import Any


def compute_narrative_coherence(
    variance_id: str,
    narrative_text: str,
    variance_amount: float,
    correlations: list[dict[str, Any]],
    sibling_narratives: dict[str, str],
) -> dict[str, Any]:
    """Check narrative consistency with variance data and related narratives.

    Args:
        variance_id: Current variance ID.
        narrative_text: The generated narrative text to validate.
        variance_amount: The actual variance dollar amount.
        correlations: Correlated variances with partner info.
        sibling_narratives: Sibling variance_id → their narrative text.

    Returns:
        Dict with coherence_score (0-1), issues list, and note.
    """
    if not narrative_text:
        return {"coherence_score": 1.0, "issues": [], "note": ""}

    issues: list[str] = []

    # Check 1: Direction consistency — narrative direction matches variance sign
    direction_ok = _check_direction_consistency(narrative_text, variance_amount)
    if not direction_ok:
        issues.append("Direction mismatch: narrative direction doesn't match variance sign")

    # Check 2: Magnitude reasonableness — mentioned amounts are within range
    magnitude_ok = _check_magnitude_reasonableness(narrative_text, variance_amount)
    if not magnitude_ok:
        issues.append("Magnitude issue: mentioned amounts seem inconsistent with variance")

    # Check 3: Cross-narrative consistency with siblings
    sibling_issues = _check_sibling_consistency(narrative_text, sibling_narratives, variance_amount)
    issues.extend(sibling_issues)

    # Compute score
    max_issues = 4  # Normalize against max possible issues
    coherence_score = max(0.0, 1.0 - (len(issues) * 0.25))

    note = ""
    if issues:
        note = f"Coherence: {issues[0]}"

    return {
        "coherence_score": round(coherence_score, 2),
        "issues": issues,
        "note": note,
    }


def _check_direction_consistency(text: str, amount: float) -> bool:
    """Check if narrative direction words match variance sign."""
    text_lower = text.lower()

    positive_words = {"increased", "grew", "higher", "above", "favorable", "exceeded"}
    negative_words = {"decreased", "declined", "lower", "below", "unfavorable", "shortfall"}

    has_positive = any(w in text_lower for w in positive_words)
    has_negative = any(w in text_lower for w in negative_words)

    if amount > 0 and has_negative and not has_positive:
        return False
    if amount < 0 and has_positive and not has_negative:
        return False

    return True


def _check_magnitude_reasonableness(text: str, amount: float) -> bool:
    """Check if dollar amounts in narrative are within 3x of actual."""
    # Extract dollar amounts from text
    pattern = r'\$[\d,]+(?:\.\d+)?(?:\s*[KMBkmb])?'
    matches = re.findall(pattern, text)

    abs_amount = abs(amount)
    if abs_amount == 0 or not matches:
        return True

    for match in matches:
        parsed = _parse_dollar(match)
        if parsed is not None and parsed > abs_amount * 3:
            return False

    return True


def _parse_dollar(text: str) -> float | None:
    """Parse a dollar string like '$1.2M' or '$150,000' to float."""
    try:
        clean = text.replace("$", "").replace(",", "").strip()
        multiplier = 1
        if clean.endswith(("K", "k")):
            multiplier = 1_000
            clean = clean[:-1]
        elif clean.endswith(("M", "m")):
            multiplier = 1_000_000
            clean = clean[:-1]
        elif clean.endswith(("B", "b")):
            multiplier = 1_000_000_000
            clean = clean[:-1]
        return float(clean) * multiplier
    except (ValueError, IndexError):
        return None


def _check_sibling_consistency(
    text: str,
    sibling_narratives: dict[str, str],
    amount: float,
) -> list[str]:
    """Check for contradictions with sibling narratives."""
    issues = []

    if not sibling_narratives:
        return issues

    # Simple check: if >3 siblings say "favorable" and we say "unfavorable" (or vice versa)
    favorable_count = sum(
        1 for sib_text in sibling_narratives.values()
        if sib_text and "favorable" in sib_text.lower()
    )
    unfavorable_count = sum(
        1 for sib_text in sibling_narratives.values()
        if sib_text and "unfavorable" in sib_text.lower()
    )

    # No strong pattern to check against
    if favorable_count < 3 and unfavorable_count < 3:
        return issues

    text_lower = text.lower()
    if favorable_count >= 3 and "unfavorable" in text_lower and amount > 0:
        issues.append("Sibling conflict: most siblings favorable but narrative says unfavorable")
    if unfavorable_count >= 3 and "favorable" in text_lower and amount < 0:
        issues.append("Sibling conflict: most siblings unfavorable but narrative says favorable")

    return issues
