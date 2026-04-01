"""Unit tests for RBAC service (shared/auth/rbac.py).

Tests persona-narrative mapping, status filtering, BU scope checks,
variance filtering, and persona resolution.
"""

import pytest
from shared.auth.rbac import RBACService
from shared.models.enums import NarrativeLevel, PersonaType


@pytest.fixture
def rbac() -> RBACService:
    """Create an RBAC service instance."""
    return RBACService()


class TestNarrativeLevelMapping:
    """Tests for persona → narrative level mapping."""

    def test_analyst_gets_detail_level(self, rbac: RBACService):
        """Analyst's primary level is detail."""
        assert rbac.get_primary_narrative_level("analyst") == NarrativeLevel.DETAIL

    def test_cfo_gets_summary_level(self, rbac: RBACService):
        """CFO's primary level is summary."""
        assert rbac.get_primary_narrative_level("cfo") == NarrativeLevel.SUMMARY

    def test_board_viewer_gets_board_level(self, rbac: RBACService):
        """Board viewer's primary level is board."""
        assert rbac.get_primary_narrative_level("board_viewer") == NarrativeLevel.BOARD

    def test_bu_leader_gets_midlevel(self, rbac: RBACService):
        """BU leader's primary level is midlevel."""
        assert rbac.get_primary_narrative_level("bu_leader") == NarrativeLevel.MIDLEVEL

    def test_analyst_sees_all_levels_except_board(self, rbac: RBACService):
        """Analyst can see detail, midlevel, summary, oneliner (not board)."""
        levels = rbac.get_narrative_levels("analyst")
        assert NarrativeLevel.DETAIL in levels
        assert NarrativeLevel.MIDLEVEL in levels
        assert NarrativeLevel.SUMMARY in levels
        assert NarrativeLevel.BOARD not in levels

    def test_board_viewer_sees_only_board_and_summary(self, rbac: RBACService):
        """Board viewer sees only board + summary."""
        levels = rbac.get_narrative_levels("board_viewer")
        assert set(levels) == {NarrativeLevel.BOARD, NarrativeLevel.SUMMARY}

    def test_unknown_persona_defaults_to_detail(self, rbac: RBACService):
        """Unknown persona defaults to detail level."""
        level = rbac.get_primary_narrative_level("unknown_role")
        assert level == NarrativeLevel.DETAIL


class TestStatusFiltering:
    """Tests for persona → allowed review statuses."""

    def test_analyst_sees_all_statuses(self, rbac: RBACService):
        """Analyst sees all review statuses."""
        statuses = rbac.get_allowed_statuses("analyst")
        assert "AI_DRAFT" in statuses
        assert "ANALYST_REVIEWED" in statuses
        assert "APPROVED" in statuses

    def test_cfo_sees_only_approved(self, rbac: RBACService):
        """CFO sees only APPROVED."""
        statuses = rbac.get_allowed_statuses("cfo")
        assert statuses == ["APPROVED"]

    def test_bu_leader_sees_reviewed_and_approved(self, rbac: RBACService):
        """BU leader sees ANALYST_REVIEWED and APPROVED."""
        statuses = rbac.get_allowed_statuses("bu_leader")
        assert "ANALYST_REVIEWED" in statuses
        assert "APPROVED" in statuses
        assert "AI_DRAFT" not in statuses

    def test_board_viewer_sees_only_approved(self, rbac: RBACService):
        """Board viewer sees only APPROVED."""
        statuses = rbac.get_allowed_statuses("board_viewer")
        assert statuses == ["APPROVED"]


class TestBUScope:
    """Tests for BU scope access checks."""

    def test_all_scope_allows_any_bu(self, rbac: RBACService):
        """'ALL' scope allows access to any BU."""
        assert rbac.check_bu_access(["ALL"], "BU001") is True
        assert rbac.check_bu_access(["ALL"], "BU999") is True

    def test_specific_scope_allows_matching_bu(self, rbac: RBACService):
        """Specific BU scope allows access to matching BU."""
        assert rbac.check_bu_access(["BU001", "BU002"], "BU001") is True

    def test_specific_scope_denies_non_matching_bu(self, rbac: RBACService):
        """Specific BU scope denies access to non-matching BU."""
        assert rbac.check_bu_access(["BU001"], "BU002") is False


class TestVarianceFiltering:
    """Tests for filtering variances by persona and BU scope."""

    def test_cfo_filters_out_drafts(self, rbac: RBACService):
        """CFO filtering removes AI_DRAFT variances."""
        variances = [
            {"status": "AI_DRAFT", "bu_id": "BU001"},
            {"status": "APPROVED", "bu_id": "BU001"},
        ]
        filtered = rbac.filter_variances_by_persona(variances, "cfo", ["ALL"])
        assert len(filtered) == 1
        assert filtered[0]["status"] == "APPROVED"

    def test_bu_scope_filters_bu(self, rbac: RBACService):
        """BU scope filtering removes variances from other BUs."""
        variances = [
            {"status": "APPROVED", "bu_id": "BU001"},
            {"status": "APPROVED", "bu_id": "BU002"},
        ]
        filtered = rbac.filter_variances_by_persona(variances, "analyst", ["BU001"])
        assert len(filtered) == 1
        assert filtered[0]["bu_id"] == "BU001"

    def test_all_scope_keeps_all_bus(self, rbac: RBACService):
        """ALL scope keeps variances from all BUs."""
        variances = [
            {"status": "APPROVED", "bu_id": "BU001"},
            {"status": "APPROVED", "bu_id": "BU002"},
        ]
        filtered = rbac.filter_variances_by_persona(variances, "analyst", ["ALL"])
        assert len(filtered) == 2

    def test_hr_finance_filters_by_domain(self, rbac: RBACService):
        """HR Finance filtering keeps only HC domain accounts."""
        variances = [
            {"status": "APPROVED", "bu_id": "BU001", "account_name": "Salaries & Wages"},
            {"status": "APPROVED", "bu_id": "BU001", "account_name": "Revenue - Consulting"},
        ]
        filtered = rbac.filter_variances_by_persona(variances, "hr_finance", ["ALL"])
        assert len(filtered) == 1
        assert filtered[0]["account_name"] == "Salaries & Wages"


class TestPersonaResolution:
    """Tests for resolving persona from role list."""

    def test_single_analyst_role(self, rbac: RBACService):
        """Single analyst role resolves to analyst persona."""
        assert rbac.resolve_persona(["analyst"]) == PersonaType.ANALYST

    def test_admin_takes_priority(self, rbac: RBACService):
        """Admin role takes highest priority."""
        assert rbac.resolve_persona(["analyst", "admin"]) == PersonaType.ANALYST  # admin maps to analyst persona

    def test_cfo_over_director(self, rbac: RBACService):
        """CFO outranks director."""
        assert rbac.resolve_persona(["director", "cfo"]) == PersonaType.CFO

    def test_empty_roles_defaults_to_analyst(self, rbac: RBACService):
        """Empty role list defaults to analyst."""
        assert rbac.resolve_persona([]) == PersonaType.ANALYST

    def test_role_to_persona_mapping(self, rbac: RBACService):
        """Each role maps to expected persona."""
        assert rbac.get_persona_for_role("analyst") == PersonaType.ANALYST
        assert rbac.get_persona_for_role("cfo") == PersonaType.CFO
        assert rbac.get_persona_for_role("board_viewer") == PersonaType.BOARD_VIEWER
