"""RBAC (Role-Based Access Control) service.

Provides persona-to-narrative mapping, BU scope resolution, and
data filtering based on user persona. Works with the DB-stored
roles and permissions from UserStore.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from shared.models.enums import NarrativeLevel, PersonaType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Persona → Narrative Level mapping
# ---------------------------------------------------------------------------

PERSONA_NARRATIVE_MAP: dict[str, list[str]] = {
    PersonaType.ANALYST: [
        NarrativeLevel.DETAIL,
        NarrativeLevel.MIDLEVEL,
        NarrativeLevel.SUMMARY,
        NarrativeLevel.ONELINER,
    ],
    PersonaType.BU_LEADER: [
        NarrativeLevel.MIDLEVEL,
        NarrativeLevel.SUMMARY,
        NarrativeLevel.ONELINER,
    ],
    PersonaType.DIRECTOR: [
        NarrativeLevel.MIDLEVEL,
        NarrativeLevel.SUMMARY,
        NarrativeLevel.ONELINER,
    ],
    PersonaType.CFO: [
        NarrativeLevel.SUMMARY,
        NarrativeLevel.ONELINER,
    ],
    PersonaType.HR_FINANCE: [
        NarrativeLevel.DETAIL,
        NarrativeLevel.MIDLEVEL,
        NarrativeLevel.ONELINER,
    ],
    PersonaType.BOARD_VIEWER: [
        NarrativeLevel.BOARD,
        NarrativeLevel.SUMMARY,
    ],
}

# Persona → Allowed review statuses
PERSONA_STATUS_MAP: dict[str, list[str]] = {
    PersonaType.ANALYST: [
        "AI_DRAFT",
        "ANALYST_REVIEWED",
        "APPROVED",
        "ESCALATED",
        "DISMISSED",
        "AUTO_CLOSED",
    ],
    PersonaType.BU_LEADER: ["ANALYST_REVIEWED", "APPROVED"],
    PersonaType.DIRECTOR: ["ANALYST_REVIEWED", "APPROVED"],
    PersonaType.CFO: ["APPROVED"],
    PersonaType.HR_FINANCE: [
        "AI_DRAFT",
        "ANALYST_REVIEWED",
        "APPROVED",
    ],
    PersonaType.BOARD_VIEWER: ["APPROVED"],
}

# HR Finance domain accounts (Headcount / Compensation / Benefits)
HR_FINANCE_ACCOUNTS: set[str] = {
    "Salaries & Wages",
    "Employee Benefits",
    "Contractor Costs",
    "Training & Development",
    "Recruitment",
    "Headcount",
}

# Role → Persona mapping (primary persona for a role)
ROLE_PERSONA_MAP: dict[str, str] = {
    "analyst": PersonaType.ANALYST,
    "bu_leader": PersonaType.BU_LEADER,
    "director": PersonaType.DIRECTOR,
    "cfo": PersonaType.CFO,
    "hr_finance": PersonaType.HR_FINANCE,
    "board_viewer": PersonaType.BOARD_VIEWER,
    "admin": PersonaType.ANALYST,  # Admin gets full analyst view
}


# ---------------------------------------------------------------------------
# RBACService
# ---------------------------------------------------------------------------

class RBACService:
    """Role-Based Access Control service.

    Provides persona-based filtering for narratives, review statuses,
    BU scope, and domain-specific access rules.
    """

    def get_narrative_levels(self, persona: str) -> list[str]:
        """Get allowed narrative levels for a persona.

        Args:
            persona: PersonaType value (e.g. 'analyst', 'cfo').

        Returns:
            List of allowed NarrativeLevel values.
        """
        return PERSONA_NARRATIVE_MAP.get(persona, [NarrativeLevel.DETAIL])

    def get_primary_narrative_level(self, persona: str) -> str:
        """Get the primary (preferred) narrative level for a persona.

        Args:
            persona: PersonaType value.

        Returns:
            Single NarrativeLevel value.
        """
        levels = self.get_narrative_levels(persona)
        return levels[0] if levels else NarrativeLevel.DETAIL

    def get_allowed_statuses(self, persona: str) -> list[str]:
        """Get allowed review statuses for a persona.

        Args:
            persona: PersonaType value.

        Returns:
            List of ReviewStatus values the persona can see.
        """
        return PERSONA_STATUS_MAP.get(persona, ["AI_DRAFT"])

    def get_persona_for_role(self, role: str) -> str:
        """Map a role name to its primary persona type.

        Args:
            role: Role name (e.g. 'analyst', 'cfo').

        Returns:
            PersonaType value.
        """
        return ROLE_PERSONA_MAP.get(role, PersonaType.ANALYST)

    def resolve_persona(self, roles: list[str]) -> str:
        """Resolve the primary persona from a list of roles.

        Picks the highest-privilege persona. Priority:
        admin > cfo > director > bu_leader > analyst > hr_finance > board_viewer

        Args:
            roles: List of role names.

        Returns:
            Primary PersonaType value.
        """
        priority = [
            "admin",
            "cfo",
            "director",
            "bu_leader",
            "analyst",
            "hr_finance",
            "board_viewer",
        ]
        for role in priority:
            if role in roles:
                return self.get_persona_for_role(role)
        return PersonaType.ANALYST

    def filter_variances_by_persona(
        self,
        variances: list[dict[str, Any]],
        persona: str,
        bu_scope: list[str],
    ) -> list[dict[str, Any]]:
        """Filter variance records based on persona and BU scope.

        Args:
            variances: List of variance dicts with 'status', 'bu_id', 'account_name' keys.
            persona: PersonaType value.
            bu_scope: List of accessible BU IDs (or ["ALL"]).

        Returns:
            Filtered list of variances.
        """
        allowed_statuses = self.get_allowed_statuses(persona)
        result = []

        for v in variances:
            # Status filter
            if v.get("status") and v["status"] not in allowed_statuses:
                continue

            # BU scope filter
            if "ALL" not in bu_scope:
                v_bu = v.get("bu_id") or v.get("business_unit_id")
                if v_bu and v_bu not in bu_scope:
                    continue

            # HR Finance domain filter
            if persona == PersonaType.HR_FINANCE:
                account = v.get("account_name", "")
                if account and account not in HR_FINANCE_ACCOUNTS:
                    continue

            result.append(v)

        return result

    def filter_narratives_by_level(
        self,
        narratives: list[dict[str, Any]],
        persona: str,
    ) -> list[dict[str, Any]]:
        """Filter narratives to only include levels allowed for the persona.

        Args:
            narratives: List of narrative dicts with 'narrative_level' key.
            persona: PersonaType value.

        Returns:
            Filtered list of narratives.
        """
        allowed_levels = self.get_narrative_levels(persona)
        return [
            n for n in narratives
            if n.get("narrative_level", "detail") in allowed_levels
        ]

    def check_bu_access(
        self,
        bu_scope: list[str],
        target_bu: str,
    ) -> bool:
        """Check if user's BU scope includes the target BU.

        Args:
            bu_scope: User's accessible BU IDs.
            target_bu: BU being accessed.

        Returns:
            True if access is allowed.
        """
        return "ALL" in bu_scope or target_bu in bu_scope

    def is_hr_finance_account(self, account_name: str) -> bool:
        """Check if an account belongs to the HR Finance domain."""
        return account_name in HR_FINANCE_ACCOUNTS
