"""Period calculation utilities.

Provides helper functions for fiscal period arithmetic:
prior period, quarter membership, month names, etc.
Used by the narrative engine for carry-forward and QTD/YTD context.
"""

from __future__ import annotations

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

MONTH_SHORT = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def get_prior_period(period_id: str) -> str | None:
    """Get the previous month's period_id.

    Args:
        period_id: "YYYY-MM" format (e.g., "2026-05")

    Returns:
        Prior period (e.g., "2026-04"), or None if invalid.
    """
    try:
        year, month = int(period_id[:4]), int(period_id[5:7])
        if month == 1:
            return f"{year - 1}-12"
        return f"{year}-{month - 1:02d}"
    except (ValueError, IndexError):
        return None


def get_fiscal_quarter(period_id: str) -> str:
    """Get the fiscal quarter label for a period.

    Assumes calendar year = fiscal year, standard quarters.

    Returns:
        "Q1", "Q2", "Q3", or "Q4"
    """
    try:
        month = int(period_id[5:7])
        return f"Q{(month - 1) // 3 + 1}"
    except (ValueError, IndexError):
        return "Q?"


def get_quarter_number(period_id: str) -> int:
    """Get the fiscal quarter number (1-4)."""
    try:
        month = int(period_id[5:7])
        return (month - 1) // 3 + 1
    except (ValueError, IndexError):
        return 0


def get_quarter_periods(period_id: str) -> list[str]:
    """Get all period_ids in the same fiscal quarter.

    Args:
        period_id: Any period in the quarter (e.g., "2026-05")

    Returns:
        List of 3 period_ids (e.g., ["2026-04", "2026-05", "2026-06"])
    """
    try:
        year = int(period_id[:4])
        month = int(period_id[5:7])
        q_start = ((month - 1) // 3) * 3 + 1  # Q2 → month 4
        return [f"{year}-{q_start + i:02d}" for i in range(3)]
    except (ValueError, IndexError):
        return []


def get_year_quarter_ends(period_id: str) -> list[str]:
    """Get quarter-end period_ids for the fiscal year.

    Returns:
        List of quarter-end periods (e.g., ["2026-03", "2026-06", "2026-09", "2026-12"])
    """
    try:
        year = int(period_id[:4])
        return [f"{year}-{m:02d}" for m in [3, 6, 9, 12]]
    except (ValueError, IndexError):
        return []


def get_month_name(period_id: str) -> str:
    """Get the full month name for a period.

    Returns:
        "May" for "2026-05"
    """
    try:
        month = int(period_id[5:7])
        return MONTH_NAMES[month]
    except (ValueError, IndexError):
        return period_id


def get_month_short(period_id: str) -> str:
    """Get the short month name.

    Returns:
        "May" for "2026-05"
    """
    try:
        month = int(period_id[5:7])
        return MONTH_SHORT[month]
    except (ValueError, IndexError):
        return period_id


def get_fiscal_year(period_id: str) -> int:
    """Get the fiscal year from a period_id."""
    try:
        return int(period_id[:4])
    except (ValueError, IndexError):
        return 0
