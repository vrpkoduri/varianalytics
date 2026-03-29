"""Intent classification and entity extraction for chat messages.

Uses keyword/regex patterns to classify user intent and extract
structured entities (period, BU, account, etc.) from natural language.
This is the Sprint 1 deterministic classifier; replaced by LLM-based
classification in SD-14.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Intent(str, Enum):
    """Supported user intent categories."""

    REVENUE_OVERVIEW = "revenue_overview"
    VARIANCE_DETAIL = "variance_detail"
    PL_SUMMARY = "pl_summary"
    WATERFALL = "waterfall"
    HEATMAP = "heatmap"
    TREND = "trend"
    DRILL_DOWN = "drill_down"
    DECOMPOSITION = "decomposition"
    REVIEW_STATUS = "review_status"
    NETTING = "netting"
    GENERAL = "general"


@dataclass
class ExtractedEntities:
    """Entities extracted from a user message."""

    period_id: Optional[str] = None
    bu_id: Optional[str] = None
    account_id: Optional[str] = None
    variance_id: Optional[str] = None
    dimension: Optional[str] = None
    view_id: str = "MTD"
    base_id: str = "BUDGET"


class KeywordIntentClassifier:
    """Classifies user messages using regex patterns and keyword matching.

    Patterns are evaluated in order of specificity (most specific first).
    Entity extraction runs independently of intent classification.
    """

    # Ordered by specificity — most specific patterns first
    _PATTERNS: list[tuple[Intent, re.Pattern]] = [
        (Intent.DECOMPOSITION, re.compile(
            r"decompos|break\s*down|breakdown|vol\s*price|vol.*mix|price.*mix|driver",
            re.IGNORECASE,
        )),
        (Intent.NETTING, re.compile(
            r"netting|offset|cancel\s*out",
            re.IGNORECASE,
        )),
        (Intent.REVIEW_STATUS, re.compile(
            r"review|queue|pending|draft|approv",
            re.IGNORECASE,
        )),
        (Intent.WATERFALL, re.compile(
            r"waterfall|bridge|walk",
            re.IGNORECASE,
        )),
        (Intent.HEATMAP, re.compile(
            r"heatmap|heat\s*map|geo\s*variance|matrix",
            re.IGNORECASE,
        )),
        (Intent.TREND, re.compile(
            r"trend|trailing|historical|month\s*over\s*month|mom\b",
            re.IGNORECASE,
        )),
        (Intent.PL_SUMMARY, re.compile(
            r"p\s*&\s*l|p\s+and\s+l|income\s+statement|profit\s*loss|profit\s+and\s+loss",
            re.IGNORECASE,
        )),
        (Intent.VARIANCE_DETAIL, re.compile(
            r"variance\s+detail|tell\s+me\s+about|explain\b|why\b",
            re.IGNORECASE,
        )),
        (Intent.DRILL_DOWN, re.compile(
            r"drill|dig\s+into|deep\s+dive",
            re.IGNORECASE,
        )),
        (Intent.REVENUE_OVERVIEW, re.compile(
            r"revenue|sales|top\s*line|booking",
            re.IGNORECASE,
        )),
    ]

    # Business unit name → canonical ID
    _BU_MAP: dict[str, str] = {
        "marsh": "marsh",
        "mercer": "mercer",
        "guy carpenter": "guy_carpenter",
        "oliver wyman": "oliver_wyman",
        "mmc corporate": "mmc_corporate",
        "corporate": "mmc_corporate",
    }

    # Account keyword → canonical account ID
    _ACCOUNT_MAP: dict[str, str] = {
        "revenue": "acct_revenue",
        "gross revenue": "acct_gross_revenue",
        "cogs": "acct_cogs",
        "cost of goods": "acct_cogs",
        "cost of sales": "acct_cogs",
        "opex": "acct_opex",
        "operating expense": "acct_opex",
        "operating expenses": "acct_opex",
        "ebitda": "acct_ebitda",
        "gross profit": "acct_gross_profit",
        "net income": "acct_net_income",
        "ebit": "acct_ebit",
    }

    # Month names → two-digit month strings
    _MONTH_MAP: dict[str, str] = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }

    # Dimension keywords
    _DIMENSION_MAP: dict[str, str] = {
        "geography": "geo",
        "geo": "geo",
        "segment": "segment",
        "lob": "lob",
        "line of business": "lob",
        "cost center": "costcenter",
        "cost centre": "costcenter",
        "costcenter": "costcenter",
    }

    # View keywords
    _VIEW_PATTERNS: dict[str, re.Pattern] = {
        "YTD": re.compile(r"\bytd\b|year\s*to\s*date", re.IGNORECASE),
        "QTD": re.compile(r"\bqtd\b|quarter\s*to\s*date", re.IGNORECASE),
    }

    # Base comparison keywords
    _BASE_PATTERNS: dict[str, re.Pattern] = {
        "FORECAST": re.compile(r"\bforecast\b|\bfc\b", re.IGNORECASE),
        "PY": re.compile(r"\bprior\s*year\b|\bpy\b|\blast\s*year\b|\byoy\b", re.IGNORECASE),
    }

    # Period patterns
    _PERIOD_YYYY_MM = re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])\b")
    _PERIOD_MONTH_YEAR = re.compile(
        r"\b(january|february|march|april|may|june|july|august|september|"
        r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)"
        r"\s+(20\d{2})\b",
        re.IGNORECASE,
    )
    _PERIOD_QUARTER = re.compile(r"\bQ([1-4])\s+(20\d{2})\b", re.IGNORECASE)

    # Variance ID pattern (e.g. "var_abc123")
    _VARIANCE_ID = re.compile(r"\b(var_[a-zA-Z0-9_]+)\b")

    def classify(
        self,
        message: str,
        ui_context: dict | None = None,
    ) -> tuple[Intent, ExtractedEntities]:
        """Classify intent and extract entities from a user message.

        Args:
            message: Raw user chat message.
            ui_context: Optional dict with current UI filter state
                (period_id, bu_id, view_id, base_id) used as defaults.

        Returns:
            Tuple of (Intent, ExtractedEntities).
        """
        intent = self._classify_intent(message)
        entities = self._extract_entities(message, ui_context)
        return intent, entities

    def _classify_intent(self, message: str) -> Intent:
        """Match the first pattern that hits."""
        for intent, pattern in self._PATTERNS:
            if pattern.search(message):
                return intent
        return Intent.GENERAL

    def _extract_entities(
        self,
        message: str,
        ui_context: dict | None = None,
    ) -> ExtractedEntities:
        """Extract structured entities from the message text."""
        entities = ExtractedEntities()
        msg_lower = message.lower()

        # --- Period ---
        entities.period_id = self._extract_period(message)

        # --- Business Unit ---
        entities.bu_id = self._extract_bu(msg_lower)

        # --- Account ---
        entities.account_id = self._extract_account(msg_lower)

        # --- Variance ID ---
        m = self._VARIANCE_ID.search(message)
        if m:
            entities.variance_id = m.group(1)

        # --- Dimension ---
        entities.dimension = self._extract_dimension(msg_lower)

        # --- View (MTD/QTD/YTD) ---
        for view_id, pattern in self._VIEW_PATTERNS.items():
            if pattern.search(message):
                entities.view_id = view_id
                break

        # --- Base (BUDGET/FORECAST/PY) ---
        for base_id, pattern in self._BASE_PATTERNS.items():
            if pattern.search(message):
                entities.base_id = base_id
                break

        # --- Apply UI context defaults for missing fields ---
        if ui_context:
            if entities.period_id is None and "period_id" in ui_context:
                entities.period_id = ui_context["period_id"]
            if entities.bu_id is None and "bu_id" in ui_context:
                entities.bu_id = ui_context["bu_id"]
            if entities.view_id == "MTD" and "view_id" in ui_context:
                # Only override if user didn't explicitly set a view
                if not any(p.search(message) for p in self._VIEW_PATTERNS.values()):
                    entities.view_id = ui_context["view_id"]
            if entities.base_id == "BUDGET" and "base_id" in ui_context:
                if not any(p.search(message) for p in self._BASE_PATTERNS.values()):
                    entities.base_id = ui_context["base_id"]

        return entities

    def _extract_period(self, message: str) -> str | None:
        """Extract period_id in YYYY-MM format."""
        # Try YYYY-MM first
        m = self._PERIOD_YYYY_MM.search(message)
        if m:
            return f"{m.group(1)}-{m.group(2)}"

        # Try "Month YYYY"
        m = self._PERIOD_MONTH_YEAR.search(message)
        if m:
            month_str = m.group(1).lower()
            month_num = self._MONTH_MAP.get(month_str)
            if month_num:
                return f"{m.group(2)}-{month_num}"

        # Try "Q1 2026" — map to first month of quarter
        m = self._PERIOD_QUARTER.search(message)
        if m:
            quarter = int(m.group(1))
            first_month = (quarter - 1) * 3 + 1
            return f"{m.group(2)}-{first_month:02d}"

        return None

    def _extract_bu(self, msg_lower: str) -> str | None:
        """Extract business unit ID from message."""
        # Check multi-word BU names first (longest match)
        for name in sorted(self._BU_MAP, key=len, reverse=True):
            if name in msg_lower:
                return self._BU_MAP[name]
        return None

    def _extract_account(self, msg_lower: str) -> str | None:
        """Extract account ID from message."""
        # Check multi-word account names first (longest match)
        for name in sorted(self._ACCOUNT_MAP, key=len, reverse=True):
            if name in msg_lower:
                return self._ACCOUNT_MAP[name]
        return None

    def _extract_dimension(self, msg_lower: str) -> str | None:
        """Extract dimension from message."""
        for name in sorted(self._DIMENSION_MAP, key=len, reverse=True):
            if name in msg_lower:
                return self._DIMENSION_MAP[name]
        return None
