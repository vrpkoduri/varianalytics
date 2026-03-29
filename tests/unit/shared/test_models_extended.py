"""Extended unit tests for shared.models — workflow, API, and additional fact schemas."""

import pytest

from shared.models.api import (
    ChatMessage,
    DashboardSummary,
    ErrorResponse,
    FilterParams,
    HealthResponse,
    PaginationParams,
)
from shared.models.enums import ComparisonBase, ReviewStatus, ViewType
from shared.models.workflow import ApprovalAction, ReviewAction, ReviewQueueItem


@pytest.mark.unit
class TestHealthResponse:
    """Tests for health check response."""

    def test_default_status(self) -> None:
        resp = HealthResponse(service="gateway", version="0.1.0")
        assert resp.status == "ok"

    def test_custom_status(self) -> None:
        resp = HealthResponse(status="degraded", service="computation", version="0.1.0")
        assert resp.status == "degraded"


@pytest.mark.unit
class TestPaginationParams:
    """Tests for pagination validation."""

    def test_defaults(self) -> None:
        p = PaginationParams()
        assert p.page == 1
        assert p.page_size == 50

    def test_custom_values(self) -> None:
        p = PaginationParams(page=3, page_size=100)
        assert p.page == 3

    def test_page_minimum(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_page_size_maximum(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PaginationParams(page_size=1000)


@pytest.mark.unit
class TestFilterParams:
    """Tests for variance filter parameters."""

    def test_defaults(self) -> None:
        f = FilterParams()
        assert f.view == ViewType.MTD
        assert f.base == ComparisonBase.BUDGET
        assert f.period_id is None

    def test_all_filters(self) -> None:
        f = FilterParams(
            period_id="2026-06",
            bu_id="marsh",
            account_id="acct_revenue",
            view=ViewType.YTD,
            base=ComparisonBase.PRIOR_YEAR,
        )
        assert f.bu_id == "marsh"
        assert f.view == ViewType.YTD


@pytest.mark.unit
class TestReviewAction:
    """Tests for review action schema."""

    def test_confirm_action(self) -> None:
        action = ReviewAction(variance_id="var_001", action="confirm")
        assert action.action == "confirm"
        assert action.edited_narrative is None

    def test_edit_action_with_narrative(self) -> None:
        action = ReviewAction(
            variance_id="var_001",
            action="edit",
            edited_narrative="Updated: Revenue was higher due to new client wins.",
            hypothesis_feedback={"hyp_001": True, "hyp_002": False},
        )
        assert action.edited_narrative is not None
        assert action.hypothesis_feedback["hyp_001"] is True


@pytest.mark.unit
class TestApprovalAction:
    """Tests for bulk approval action schema."""

    def test_bulk_approve(self) -> None:
        action = ApprovalAction(
            variance_ids=["var_001", "var_002", "var_003"],
            action="approve",
        )
        assert len(action.variance_ids) == 3

    def test_hold_with_notes(self) -> None:
        action = ApprovalAction(
            variance_ids=["var_001"],
            action="hold",
            notes="Need to verify subcontractor cost allocation",
        )
        assert action.notes is not None


@pytest.mark.unit
class TestChatMessage:
    """Tests for chat message schema."""

    def test_simple_message(self) -> None:
        msg = ChatMessage(message="How did revenue perform?")
        assert msg.context is None
        assert msg.conversation_id is None

    def test_message_with_context(self) -> None:
        msg = ChatMessage(
            message="Drill down",
            context={"period_id": "2026-06", "bu_id": "marsh"},
            conversation_id="conv_123",
        )
        assert msg.context["bu_id"] == "marsh"


@pytest.mark.unit
class TestDashboardSummary:
    """Tests for dashboard summary card data."""

    def test_revenue_summary(self) -> None:
        summary = DashboardSummary(
            metric_name="Revenue",
            actual=1500000.0,
            comparator=1450000.0,
            variance=50000.0,
            variance_pct=3.45,
            trend_direction="up",
            review_status_counts={"APPROVED": 10, "AI_DRAFT": 3},
        )
        assert summary.variance == 50000.0
        assert summary.review_status_counts["APPROVED"] == 10
