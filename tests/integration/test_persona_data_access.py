"""Integration tests for persona-based data filtering.

Tests that each persona sees only the data they should:
- CFO sees only APPROVED variances (summary level)
- BU Leader sees only own BU (REVIEWED + APPROVED, midlevel)
- Board Viewer sees only APPROVED (board + summary)
- HR Finance sees only HC domain
- Analyst sees all
"""

import pytest
from shared.auth.rbac import RBACService
from shared.models.enums import PersonaType, NarrativeLevel


@pytest.fixture
def rbac() -> RBACService:
    return RBACService()


@pytest.fixture
def sample_variances() -> list[dict]:
    """Mixed variance data for filtering tests."""
    return [
        {"variance_id": "v1", "status": "AI_DRAFT", "bu_id": "BU001", "account_name": "Revenue - Consulting", "narrative_level": "detail"},
        {"variance_id": "v2", "status": "ANALYST_REVIEWED", "bu_id": "BU001", "account_name": "Revenue - Advisory", "narrative_level": "detail"},
        {"variance_id": "v3", "status": "APPROVED", "bu_id": "BU001", "account_name": "Revenue - Brokerage", "narrative_level": "summary"},
        {"variance_id": "v4", "status": "APPROVED", "bu_id": "BU002", "account_name": "Revenue - Consulting", "narrative_level": "summary"},
        {"variance_id": "v5", "status": "AI_DRAFT", "bu_id": "BU002", "account_name": "Salaries & Wages", "narrative_level": "detail"},
        {"variance_id": "v6", "status": "APPROVED", "bu_id": "BU001", "account_name": "Salaries & Wages", "narrative_level": "midlevel"},
        {"variance_id": "v7", "status": "APPROVED", "bu_id": "BU001", "account_name": "Employee Benefits", "narrative_level": "board"},
        {"variance_id": "v8", "status": "ESCALATED", "bu_id": "BU001", "account_name": "Travel & Entertainment", "narrative_level": "detail"},
    ]


class TestCFODataAccess:
    """CFO sees only APPROVED items, summary level."""

    def test_cfo_only_sees_approved(self, rbac: RBACService, sample_variances):
        filtered = rbac.filter_variances_by_persona(sample_variances, "cfo", ["ALL"])
        assert all(v["status"] == "APPROVED" for v in filtered)
        assert len(filtered) == 4

    def test_cfo_narrative_levels(self, rbac: RBACService):
        levels = rbac.get_narrative_levels("cfo")
        assert NarrativeLevel.SUMMARY in levels
        assert NarrativeLevel.DETAIL not in levels
        assert NarrativeLevel.BOARD not in levels

    def test_cfo_primary_level_is_summary(self, rbac: RBACService):
        assert rbac.get_primary_narrative_level("cfo") == NarrativeLevel.SUMMARY


class TestBULeaderDataAccess:
    """BU Leader sees only own BU, REVIEWED + APPROVED."""

    def test_bu_leader_scoped_to_bu(self, rbac: RBACService, sample_variances):
        filtered = rbac.filter_variances_by_persona(sample_variances, "bu_leader", ["BU001"])
        # Only BU001 items with ANALYST_REVIEWED or APPROVED status
        for v in filtered:
            assert v["bu_id"] == "BU001"
            assert v["status"] in ("ANALYST_REVIEWED", "APPROVED")

    def test_bu_leader_excludes_drafts(self, rbac: RBACService, sample_variances):
        filtered = rbac.filter_variances_by_persona(sample_variances, "bu_leader", ["BU001"])
        assert not any(v["status"] == "AI_DRAFT" for v in filtered)

    def test_bu_leader_narrative_level(self, rbac: RBACService):
        assert rbac.get_primary_narrative_level("bu_leader") == NarrativeLevel.MIDLEVEL


class TestBoardViewerDataAccess:
    """Board viewer sees only APPROVED, board + summary levels."""

    def test_board_viewer_only_approved(self, rbac: RBACService, sample_variances):
        filtered = rbac.filter_variances_by_persona(sample_variances, "board_viewer", ["ALL"])
        assert all(v["status"] == "APPROVED" for v in filtered)

    def test_board_viewer_narrative_levels(self, rbac: RBACService):
        levels = rbac.get_narrative_levels("board_viewer")
        assert set(levels) == {NarrativeLevel.BOARD, NarrativeLevel.SUMMARY}


class TestHRFinanceDataAccess:
    """HR Finance sees only HC domain accounts."""

    def test_hr_finance_only_hc_accounts(self, rbac: RBACService, sample_variances):
        filtered = rbac.filter_variances_by_persona(sample_variances, "hr_finance", ["ALL"])
        for v in filtered:
            assert v["account_name"] in ("Salaries & Wages", "Employee Benefits")

    def test_hr_finance_excludes_revenue(self, rbac: RBACService, sample_variances):
        filtered = rbac.filter_variances_by_persona(sample_variances, "hr_finance", ["ALL"])
        assert not any("Revenue" in v["account_name"] for v in filtered)


class TestAnalystDataAccess:
    """Analyst sees everything."""

    def test_analyst_sees_all_statuses(self, rbac: RBACService, sample_variances):
        filtered = rbac.filter_variances_by_persona(sample_variances, "analyst", ["ALL"])
        assert len(filtered) == len(sample_variances)

    def test_analyst_all_bu_scope(self, rbac: RBACService, sample_variances):
        filtered = rbac.filter_variances_by_persona(sample_variances, "analyst", ["ALL"])
        bus = {v["bu_id"] for v in filtered}
        assert "BU001" in bus
        assert "BU002" in bus


class TestNarrativeFiltering:
    """Tests for narrative level filtering."""

    def test_analyst_narrative_includes_detail(self, rbac: RBACService):
        narratives = [
            {"narrative_level": "detail", "text": "Detail narrative"},
            {"narrative_level": "midlevel", "text": "Midlevel narrative"},
            {"narrative_level": "board", "text": "Board narrative"},
        ]
        filtered = rbac.filter_narratives_by_level(narratives, "analyst")
        levels = {n["narrative_level"] for n in filtered}
        assert "detail" in levels
        assert "board" not in levels

    def test_cfo_narrative_excludes_detail(self, rbac: RBACService):
        narratives = [
            {"narrative_level": "detail", "text": "Detail"},
            {"narrative_level": "summary", "text": "Summary"},
        ]
        filtered = rbac.filter_narratives_by_level(narratives, "cfo")
        assert len(filtered) == 1
        assert filtered[0]["narrative_level"] == "summary"

    def test_board_narrative_includes_board(self, rbac: RBACService):
        narratives = [
            {"narrative_level": "board", "text": "Board"},
            {"narrative_level": "summary", "text": "Summary"},
            {"narrative_level": "detail", "text": "Detail"},
        ]
        filtered = rbac.filter_narratives_by_level(narratives, "board_viewer")
        levels = {n["narrative_level"] for n in filtered}
        assert levels == {"board", "summary"}


class TestCombinedFiltering:
    """Tests combining BU scope + persona status filtering."""

    def test_bu_leader_bu001_reviewed_only(self, rbac: RBACService, sample_variances):
        """BU Leader for BU001 sees only BU001 items with REVIEWED/APPROVED."""
        filtered = rbac.filter_variances_by_persona(sample_variances, "bu_leader", ["BU001"])
        for v in filtered:
            assert v["bu_id"] == "BU001"
            assert v["status"] in ("ANALYST_REVIEWED", "APPROVED")
        # Should have: v2 (REVIEWED, BU001), v3 (APPROVED, BU001), v6 (APPROVED, BU001), v7 (APPROVED, BU001)
        assert len(filtered) == 4

    def test_hr_finance_scoped_to_bu(self, rbac: RBACService, sample_variances):
        """HR Finance scoped to BU001 sees only BU001 HC accounts."""
        filtered = rbac.filter_variances_by_persona(sample_variances, "hr_finance", ["BU001"])
        for v in filtered:
            assert v["bu_id"] == "BU001"
            assert v["account_name"] in ("Salaries & Wages", "Employee Benefits")
