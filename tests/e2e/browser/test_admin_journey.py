"""Admin E2E journey — admin panel tabs and content.

Tests the admin panel end-to-end in a real browser.
Auto-skips if Docker stack is not running.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.browser.conftest import skip_no_stack, login_as, wait_for_dashboard


@skip_no_stack
@pytest.mark.playwright
class TestAdminJourney:
    """Browser-based admin panel E2E tests."""

    def test_admin_sees_admin_tab(self, page: Page):
        """Admin user sees Admin tab in navigation."""
        login_as(page, "admin")
        wait_for_dashboard(page)

        admin_tab = page.get_by_role("button", name="Admin", exact=True)
        expect(admin_tab).to_be_visible()

    def test_admin_page_loads(self, page: Page):
        """Admin page loads with tabbed interface."""
        login_as(page, "admin")
        wait_for_dashboard(page)

        page.get_by_role("button", name="Admin", exact=True).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/admin" in page.url

        # Should show at least the Thresholds tab label
        thresholds_tab = page.get_by_role("button", name="Thresholds", exact=True)
        expect(thresholds_tab).to_be_visible()

    def test_admin_has_users_tab(self, page: Page):
        """Admin panel has Users & Roles tab."""
        login_as(page, "admin")
        wait_for_dashboard(page)

        page.get_by_role("button", name="Admin", exact=True).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        users_tab = page.locator("text=Users & Roles")
        expect(users_tab).to_be_visible()
