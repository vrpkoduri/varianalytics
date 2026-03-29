"""Currency, percentage, and variance display formatters.

Shared across services and used in narratives, API responses, and exports.
"""

from typing import Optional


def format_currency(amount: float, decimals: int = 0, prefix: str = "$") -> str:
    """Format a number as currency with thousands separators.

    Args:
        amount: Dollar amount.
        decimals: Decimal places (0 for whole dollars).
        prefix: Currency symbol.

    Returns:
        Formatted string, e.g. '$1,234,567' or '-$500'.

    Examples:
        >>> format_currency(1234567)
        '$1,234,567'
        >>> format_currency(-500000)
        '-$500,000'
        >>> format_currency(1234.56, decimals=2)
        '$1,234.56'
    """
    sign = "-" if amount < 0 else ""
    abs_amount = abs(amount)
    if decimals > 0:
        formatted = f"{abs_amount:,.{decimals}f}"
    else:
        formatted = f"{abs_amount:,.0f}"
    return f"{sign}{prefix}{formatted}"


def format_currency_thousands(amount: float) -> str:
    """Format as currency in thousands (K) or millions (M).

    Args:
        amount: Dollar amount.

    Returns:
        Abbreviated string, e.g. '$1.2M' or '$450K'.

    Examples:
        >>> format_currency_thousands(1234567)
        '$1.2M'
        >>> format_currency_thousands(450000)
        '$450K'
        >>> format_currency_thousands(500)
        '$500'
    """
    sign = "-" if amount < 0 else ""
    abs_amount = abs(amount)
    if abs_amount >= 1_000_000:
        return f"{sign}${abs_amount / 1_000_000:.1f}M"
    elif abs_amount >= 1_000:
        return f"{sign}${abs_amount / 1_000:.0f}K"
    else:
        return f"{sign}${abs_amount:.0f}"


def format_percentage(value: Optional[float], decimals: int = 1) -> str:
    """Format a percentage value.

    Args:
        value: Percentage (already in %, e.g. 3.5 means 3.5%).
        decimals: Decimal places.

    Returns:
        Formatted string, e.g. '3.5%' or 'N/A' if None.

    Examples:
        >>> format_percentage(3.5)
        '3.5%'
        >>> format_percentage(-1.2)
        '-1.2%'
        >>> format_percentage(None)
        'N/A'
    """
    if value is None:
        return "N/A"
    return f"{value:+.{decimals}f}%"


def format_variance(amount: float, pct: Optional[float] = None) -> str:
    """Format a variance with both dollar and percentage.

    Args:
        amount: Variance dollar amount.
        pct: Variance percentage (optional).

    Returns:
        Combined string, e.g. '+$1.2M (+3.5%)' or '-$500K (N/A)'.

    Examples:
        >>> format_variance(1200000, 3.5)
        '+$1.2M (+3.5%)'
        >>> format_variance(-500000, -2.1)
        '-$500K (-2.1%)'
    """
    sign = "+" if amount >= 0 else ""
    dollar = format_currency_thousands(amount)
    if amount >= 0:
        dollar = f"+{dollar}"
    pct_str = format_percentage(pct)
    return f"{dollar} ({pct_str})"


def sign_convention_label(amount: float, is_inverse: bool) -> str:
    """Return 'Favorable' or 'Unfavorable' based on sign convention.

    Args:
        amount: Variance amount.
        is_inverse: True for cost accounts (negative variance = favorable).

    Returns:
        'Favorable' or 'Unfavorable'.
    """
    if is_inverse:
        return "Favorable" if amount < 0 else "Unfavorable"
    else:
        return "Favorable" if amount > 0 else "Unfavorable"
