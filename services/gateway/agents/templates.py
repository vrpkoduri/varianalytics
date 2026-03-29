"""Response templates for template-based agent responses (Sprint 1).

Templates use {variable} placeholders that are filled with real data from
Computation Service responses. These will be replaced by LLM-generated
narratives in SD-14.
"""

from __future__ import annotations

from typing import Any

from services.gateway.agents.intent import Intent


# ---------------------------------------------------------------------------
# Response templates keyed by intent
# ---------------------------------------------------------------------------

RESPONSE_TEMPLATES: dict[Intent, str] = {
    Intent.REVENUE_OVERVIEW: (
        "Revenue Performance Summary for {period}\n\n"
        "Total Revenue was {actual}, {direction} {variance} ({pct}) vs {base}.\n\n"
        "By Business Unit:\n{table}\n\n"
        "{top_driver}"
    ),
    Intent.PL_SUMMARY: (
        "P&L Summary for {period}\n\n"
        "{summary_table}\n\n"
        "Key highlights: {highlights}"
    ),
    Intent.WATERFALL: (
        "Revenue Bridge: {base_label} to Actual\n\n"
        "{bridge_narrative}\n\n"
        "Largest contributor: {top_step}"
    ),
    Intent.HEATMAP: (
        "Variance Intensity by Geography x Business Unit\n\n"
        "{heatmap_narrative}\n\n"
        "Hotspot: {hotspot}"
    ),
    Intent.TREND: (
        "{account} Trend ({periods} months)\n\n"
        "{trend_narrative}"
    ),
    Intent.DECOMPOSITION: (
        "Variance Decomposition for {account}\n\n"
        "{components_narrative}"
    ),
    Intent.VARIANCE_DETAIL: (
        "Variance Detail: {account}\n\n"
        "Actual: {actual}  |  {base_label}: {comparator}  |  Variance: {variance} ({pct})\n\n"
        "{narrative}"
    ),
    Intent.DRILL_DOWN: (
        "Drill-Down: {node_label}\n\n"
        "Total variance: {total_variance}\n\n"
        "Children:\n{children_table}"
    ),
    Intent.REVIEW_STATUS: (
        "Review Queue Status\n\n"
        "{stats_narrative}"
    ),
    Intent.NETTING: (
        "Netting Analysis\n\n"
        "{netting_narrative}"
    ),
    Intent.GENERAL: (
        "I can help you analyze financial variances. Try asking about:\n"
        "- Revenue performance\n"
        "- P&L summary\n"
        "- Variance trends\n"
        "- Review queue status"
    ),
}


# ---------------------------------------------------------------------------
# Follow-up suggestions per intent
# ---------------------------------------------------------------------------

SUGGESTION_MAP: dict[Intent, list[str]] = {
    Intent.REVENUE_OVERVIEW: [
        "Show the revenue waterfall",
        "Which BU had the largest variance?",
        "Show revenue trend over 12 months",
        "Break down the top variance",
    ],
    Intent.PL_SUMMARY: [
        "Show the revenue waterfall",
        "What are the top variances?",
        "Drill into EBITDA",
        "Show the variance heatmap",
    ],
    Intent.WATERFALL: [
        "Drill into the largest step",
        "Show the variance heatmap",
        "Compare to prior year",
    ],
    Intent.HEATMAP: [
        "Drill into the hotspot",
        "Show revenue waterfall",
        "What are the top variances?",
    ],
    Intent.TREND: [
        "Show 24-month trend",
        "Break down the latest variance",
        "Compare to forecast",
    ],
    Intent.DECOMPOSITION: [
        "Show correlations",
        "What is the revenue trend?",
        "Show the full P&L",
    ],
    Intent.VARIANCE_DETAIL: [
        "Break down this variance",
        "Show correlations",
        "Show the trend for this account",
    ],
    Intent.DRILL_DOWN: [
        "Drill deeper",
        "Show decomposition",
        "Back to P&L summary",
    ],
    Intent.REVIEW_STATUS: [
        "Show pending reviews",
        "Show approved items",
        "Show revenue variances",
    ],
    Intent.NETTING: [
        "Show the underlying variances",
        "Show the variance heatmap",
        "Show revenue performance",
    ],
    Intent.GENERAL: [
        "How did revenue perform this month?",
        "Show me the P&L",
        "What needs review?",
        "Show the variance heatmap",
    ],
}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_currency(value: float) -> str:
    """Format as $X,XXX or ($X,XXX) for negative values.

    Examples:
        >>> format_currency(1234567.89)
        '$1,234,568'
        >>> format_currency(-500000)
        '($500,000)'
    """
    if value < 0:
        return f"(${abs(value):,.0f})"
    return f"${value:,.0f}"


def format_pct(value: float | None) -> str:
    """Format as +X.X% or -X.X%. Returns 'N/A' for None.

    Examples:
        >>> format_pct(0.054)
        '+5.4%'
        >>> format_pct(-0.123)
        '-12.3%'
    """
    if value is None:
        return "N/A"
    pct = value * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def format_response(intent: Intent, data: dict[str, Any]) -> str:
    """Format a response using the template for the given intent.

    Missing keys are replaced with empty strings to avoid crashes.

    Args:
        intent: The classified intent.
        data: Dict of template variables.

    Returns:
        Formatted response string.
    """
    template = RESPONSE_TEMPLATES.get(intent, RESPONSE_TEMPLATES[Intent.GENERAL])

    # Build a safe dict that returns "" for missing keys
    class SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return ""

    safe_data = SafeDict(data)
    try:
        return template.format_map(safe_data)
    except (KeyError, ValueError):
        return template


def get_suggestions(intent: Intent) -> list[str]:
    """Get follow-up suggestions for the given intent."""
    return SUGGESTION_MAP.get(intent, SUGGESTION_MAP[Intent.GENERAL])


def build_variance_table_data(
    variances: list[dict[str, Any]],
) -> tuple[list[str], list[list[Any]]]:
    """Build columns and rows for a DataTableEvent from a variance list.

    Args:
        variances: List of variance dicts from the Computation Service.

    Returns:
        Tuple of (column_headers, rows) suitable for DataTableEvent.
    """
    columns = ["Account", "Actual", "Budget", "Variance ($)", "Variance (%)"]
    rows: list[list[Any]] = []

    for v in variances:
        rows.append([
            v.get("account_name", v.get("account_id", "")),
            format_currency(v.get("actual_amount", 0)),
            format_currency(v.get("comparator_amount", v.get("budget_amount", 0))),
            format_currency(v.get("variance_amount", 0)),
            format_pct(v.get("variance_pct")),
        ])

    return columns, rows
