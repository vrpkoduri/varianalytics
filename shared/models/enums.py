"""Shared enumerations used across all services."""

from enum import Enum


class ReviewStatus(str, Enum):
    """Variance review workflow states."""

    AI_DRAFT = "AI_DRAFT"
    ANALYST_REVIEWED = "ANALYST_REVIEWED"
    APPROVED = "APPROVED"
    ESCALATED = "ESCALATED"
    DISMISSED = "DISMISSED"
    AUTO_CLOSED = "AUTO_CLOSED"


class ViewType(str, Enum):
    """Time aggregation views."""

    MTD = "MTD"
    QTD = "QTD"
    YTD = "YTD"


class ComparisonBase(str, Enum):
    """Comparison bases for variance analysis."""

    BUDGET = "BUDGET"
    FORECAST = "FORECAST"
    PRIOR_YEAR = "PRIOR_YEAR"


class VarianceSign(str, Enum):
    """Variance sign convention.

    - natural: positive variance = favorable (revenue)
    - inverse: negative variance = favorable (costs)
    """

    NATURAL = "natural"
    INVERSE = "inverse"


class PLCategory(str, Enum):
    """P&L line item categories."""

    REVENUE = "Revenue"
    COGS = "COGS"
    OPEX = "OpEx"
    NON_OP = "NonOp"
    TAX = "Tax"


class NarrativeSource(str, Enum):
    """How a narrative was created."""

    GENERATED = "generated"
    SYNTHESIZED = "synthesized"
    EDITED = "edited"


class NarrativeLevel(str, Enum):
    """Narrative depth levels mapped to personas."""

    DETAIL = "detail"  # Analyst
    MIDLEVEL = "midlevel"  # BU Leader
    SUMMARY = "summary"  # CFO
    ONELINER = "oneliner"  # Dashboard
    BOARD = "board"  # Board (on-demand)


class PersonaType(str, Enum):
    """User persona types for RBAC and narrative filtering."""

    ANALYST = "analyst"
    BU_LEADER = "bu_leader"
    DIRECTOR = "director"
    CFO = "cfo"
    HR_FINANCE = "hr_finance"
    BOARD_VIEWER = "board_viewer"


class DecompositionMethod(str, Enum):
    """Variance decomposition methods by P&L category."""

    VOLUME_PRICE_MIX_FX = "vol_price_mix_fx"  # Revenue
    RATE_VOLUME_MIX = "rate_vol_mix"  # COGS
    RATE_VOLUME_TIMING_ONETIME = "rate_vol_timing_onetime"  # OpEx


class NettingCheckType(str, Enum):
    """Netting detection check types."""

    GROSS_OFFSET = "gross_offset"
    DISPERSION = "dispersion"
    DIRECTIONAL_SPLIT = "directional_split"
    CROSS_ACCOUNT = "cross_account"
    HIERARCHICAL_CASCADE = "hierarchical_cascade"  # Phase 2
    PERIOD_SHIFTED = "period_shifted"  # Phase 2


class TrendRuleType(str, Enum):
    """Trend detection rule types."""

    CONSECUTIVE_DIRECTION = "consecutive_direction"
    CUMULATIVE_YTD_BREACH = "cumulative_ytd_breach"
    MONOTONIC_ACCELERATION = "monotonic_acceleration"  # Phase 2
    REGRESSION_SLOPE = "regression_slope"  # Phase 2
