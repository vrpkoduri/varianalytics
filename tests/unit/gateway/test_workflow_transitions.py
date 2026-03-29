"""Workflow state machine transition tests.

Tests all valid and invalid status transitions in the ReviewStore,
covering the full lifecycle from AI_DRAFT through APPROVED, including
escalation and rejection recovery paths.
"""

import pytest

from shared.data.review_store import ReviewStore


@pytest.fixture()
def store() -> ReviewStore:
    """Create a fresh ReviewStore for each test."""
    return ReviewStore()


def _get_draft_id(store: ReviewStore) -> str:
    """Get a variance_id that is currently in AI_DRAFT status."""
    queue = store.get_review_queue(status_filter="AI_DRAFT", page_size=1)
    items = queue["items"]
    if not items:
        pytest.skip("No AI_DRAFT items available in review store")
    return items[0]["variance_id"]


# ---------------------------------------------------------------------------
# Valid transitions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidTransitions:
    """Tests that valid workflow transitions succeed correctly."""

    def test_valid_transition_approve(self, store: ReviewStore) -> None:
        """AI_DRAFT -> approve -> ANALYST_REVIEWED."""
        vid = _get_draft_id(store)
        result = store.submit_review_action(vid, "approve")
        assert result["new_status"] == "ANALYST_REVIEWED"

    def test_valid_transition_escalate(self, store: ReviewStore) -> None:
        """AI_DRAFT -> escalate -> ESCALATED."""
        vid = _get_draft_id(store)
        result = store.submit_review_action(vid, "escalate")
        assert result["new_status"] == "ESCALATED"

    def test_valid_transition_dismiss(self, store: ReviewStore) -> None:
        """AI_DRAFT -> dismiss -> DISMISSED."""
        vid = _get_draft_id(store)
        result = store.submit_review_action(vid, "dismiss")
        assert result["new_status"] == "DISMISSED"

    def test_valid_transition_escalated_to_reviewed(self, store: ReviewStore) -> None:
        """ESCALATED -> approve -> ANALYST_REVIEWED."""
        vid = _get_draft_id(store)
        # First escalate
        store.submit_review_action(vid, "escalate")
        # Then approve from ESCALATED
        result = store.submit_review_action(vid, "approve")
        assert result["new_status"] == "ANALYST_REVIEWED"

    def test_valid_transition_dismissed_to_draft(self, store: ReviewStore) -> None:
        """DISMISSED -> director_reject -> AI_DRAFT (reopen path)."""
        vid = _get_draft_id(store)
        # Dismiss first
        store.submit_review_action(vid, "dismiss")
        # director_reject maps to AI_DRAFT, DISMISSED -> AI_DRAFT is valid
        result = store.submit_review_action(vid, "director_reject")
        assert result["new_status"] == "AI_DRAFT"

    def test_edit_action_same_as_approve(self, store: ReviewStore) -> None:
        """AI_DRAFT -> edit -> ANALYST_REVIEWED (edit implies review)."""
        vid = _get_draft_id(store)
        result = store.submit_review_action(
            vid, "edit", edited_narrative="Updated narrative text"
        )
        assert result["new_status"] == "ANALYST_REVIEWED"


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInvalidTransitions:
    """Tests that invalid workflow transitions raise ValueError."""

    def test_terminal_approved_cannot_transition(self, store: ReviewStore) -> None:
        """APPROVED is terminal: no further transitions allowed."""
        vid = _get_draft_id(store)
        # Walk to APPROVED: AI_DRAFT -> approve -> ANALYST_REVIEWED -> director_approve -> APPROVED
        store.submit_review_action(vid, "approve")
        store.submit_review_action(vid, "director_approve")
        # Now try any action from APPROVED
        with pytest.raises(ValueError, match="Cannot transition"):
            store.submit_review_action(vid, "approve")

    def test_invalid_ai_draft_to_approved(self, store: ReviewStore) -> None:
        """AI_DRAFT cannot go directly to APPROVED via director_approve."""
        vid = _get_draft_id(store)
        with pytest.raises(ValueError, match="Cannot transition"):
            store.submit_review_action(vid, "director_approve")

    def test_invalid_analyst_reviewed_to_dismissed(self, store: ReviewStore) -> None:
        """ANALYST_REVIEWED cannot transition to DISMISSED."""
        vid = _get_draft_id(store)
        store.submit_review_action(vid, "approve")  # -> ANALYST_REVIEWED
        with pytest.raises(ValueError, match="Cannot transition"):
            store.submit_review_action(vid, "dismiss")


# ---------------------------------------------------------------------------
# Full lifecycle paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLifecyclePaths:
    """Tests complete workflow lifecycles from start to finish."""

    def test_full_happy_path_lifecycle(self, store: ReviewStore) -> None:
        """AI_DRAFT -> approve -> ANALYST_REVIEWED -> director_approve -> APPROVED."""
        vid = _get_draft_id(store)

        r1 = store.submit_review_action(vid, "approve", comment="Looks good")
        assert r1["new_status"] == "ANALYST_REVIEWED"

        r2 = store.submit_review_action(vid, "director_approve", comment="Approved by director")
        assert r2["new_status"] == "APPROVED"

    def test_escalation_recovery_path(self, store: ReviewStore) -> None:
        """AI_DRAFT -> escalate -> ESCALATED -> approve -> ANALYST_REVIEWED -> director_approve -> APPROVED."""
        vid = _get_draft_id(store)

        r1 = store.submit_review_action(vid, "escalate")
        assert r1["new_status"] == "ESCALATED"

        r2 = store.submit_review_action(vid, "approve")
        assert r2["new_status"] == "ANALYST_REVIEWED"

        r3 = store.submit_review_action(vid, "director_approve")
        assert r3["new_status"] == "APPROVED"

    def test_edited_narrative_stored(self, store: ReviewStore) -> None:
        """After edit action, the edited_narrative field is populated in the store."""
        vid = _get_draft_id(store)
        narrative_text = "This is the analyst's edited narrative explaining the variance."

        store.submit_review_action(vid, "edit", edited_narrative=narrative_text)

        # Verify the narrative was stored
        mask = store._review_status["variance_id"] == vid
        stored_narrative = store._review_status.loc[mask, "edited_narrative"].iloc[0]
        assert stored_narrative == narrative_text
