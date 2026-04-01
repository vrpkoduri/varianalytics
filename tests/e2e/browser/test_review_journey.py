"""Review + Approval E2E journey — review queue, edit, approve.

Tests the review and approval workflow end-to-end in a real browser.
Auto-skips if Docker stack is not running.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.browser.conftest import skip_no_stack, login_as, wait_for_dashboard


@skip_no_stack
@pytest.mark.playwright
class TestReviewJourney:
    """Browser-based review workflow E2E tests."""

    def test_analyst_sees_review_tab(self, page: Page):
        """Analyst sees Review tab in navigation."""
        login_as(page, "analyst")
        wait_for_dashboard(page)

        review_tab = page.get_by_role("button", name="Review", exact=True)
        expect(review_tab).to_be_visible()

    def test_review_page_loads(self, page: Page):
        """Navigating to /review shows the review queue."""
        login_as(page, "analyst")
        wait_for_dashboard(page)

        page.click("text=Review")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/review" in page.url

    def test_director_sees_approvals_tab(self, page: Page):
        """Director sees Approvals tab in navigation."""
        login_as(page, "director")
        wait_for_dashboard(page)

        approval_tab = page.locator("text=Approvals")
        expect(approval_tab).to_be_visible()

    def test_approval_page_loads(self, page: Page):
        """Navigating to /approval shows the approval queue."""
        login_as(page, "director")
        wait_for_dashboard(page)

        page.click("text=Approvals")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/approval" in page.url

    def test_reports_tab_navigates(self, page: Page):
        """Reports tab navigates to /reports."""
        login_as(page, "analyst")
        wait_for_dashboard(page)

        page.click("text=Reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/reports" in page.url
