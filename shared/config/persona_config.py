"""Persona configuration — maps persona to narrative level.

Each persona sees a different depth of narrative:
- Analyst: full detail (narrative_detail)
- BU Leader: mid-level summary (narrative_midlevel)
- Director: mid-level summary (narrative_midlevel)
- CFO: executive summary (narrative_summary)
- Board: one-liner / board-level (narrative_board → narrative_oneliner fallback)
"""

from __future__ import annotations

# Maps persona key → preferred narrative column in fact_variance_material
NARRATIVE_LEVEL_MAP: dict[str, str] = {
    "analyst": "narrative_detail",
    "bu_leader": "narrative_midlevel",
    "director": "narrative_midlevel",
    "cfo": "narrative_summary",
    "board": "narrative_board",
}

# Fallback chain: if preferred level is empty, try these in order
NARRATIVE_FALLBACK_CHAIN: list[str] = [
    "narrative_detail",
    "narrative_midlevel",
    "narrative_summary",
    "narrative_oneliner",
]

DEFAULT_PERSONA = "analyst"
DEFAULT_NARRATIVE_COLUMN = "narrative_detail"


def get_narrative_column(persona: str | None) -> str:
    """Return the narrative column name for a given persona.

    Args:
        persona: Persona key (e.g., 'analyst', 'cfo', 'bu_leader').
            Case-insensitive. None defaults to analyst.

    Returns:
        Column name in fact_variance_material (e.g., 'narrative_detail').
    """
    if not persona:
        return DEFAULT_NARRATIVE_COLUMN
    return NARRATIVE_LEVEL_MAP.get(persona.lower(), DEFAULT_NARRATIVE_COLUMN)


def select_narrative(row_dict: dict, persona: str | None) -> str:
    """Select the best narrative for a persona from a variance row.

    Tries the preferred level first, then walks the fallback chain.

    Args:
        row_dict: Dict of a single variance row (column→value).
        persona: Persona key. None defaults to analyst.

    Returns:
        Narrative string, or empty string if no narrative available.
    """
    preferred = get_narrative_column(persona)

    # Try preferred level
    val = row_dict.get(preferred)
    if val and str(val).strip() and str(val) != "nan":
        return str(val)

    # Fallback chain
    for col in NARRATIVE_FALLBACK_CHAIN:
        if col == preferred:
            continue
        val = row_dict.get(col)
        if val and str(val).strip() and str(val) != "nan":
            return str(val)

    return ""
