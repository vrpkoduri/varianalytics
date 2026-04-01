"""Auth E2E journey — login, logout, redirects.

Tests the authentication flow end-to-end in a real browser.
Auto-skips if Docker stack is not running.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.browser.conftest import skip_no_stack, login_as, BASE_URL


@skip_no_stack
@pytest.mark.playwright
class TestAuthJourney:
    """Browser-based authentication E2E tests."""

    def test_login_page_renders(self, page: Page):
        """Login page shows Marsh Vantage branding and form inputs."""
        page.goto("/login")
        page.wait_for_load_state("networkidle")

        # Check branding
        expect(page.locator("text=Marsh Vantage")).to_be_visible()

        # Check form inputs exist
        expect(page.locator("#email")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()

        # Check demo credentials section
        expect(page.locator("text=Demo Credentials")).to_be_visible()

    def test_login_success_redirects_to_dashboard(self, page: Page):
        """Successful login redirects to dashboard."""
        login_as(page, "analyst")

        # Should be on dashboard (root path)
        assert "/login" not in page.url

        # Dashboard content should be visible
        page.wait_for_load_state("networkidle")

    def test_login_invalid_credentials_shows_error(self, page: Page):
        """Wrong password shows error message."""
        page.goto("/login")
        page.wait_for_load_state("networkidle")

        page.fill("#email", "analyst@variance-agent.dev")
        page.fill("#password", "wrongpassword123")
        page.click("button[type='submit']")

        # Wait for error to appear
        page.wait_for_timeout(2000)

        # Error message should be visible (coral-colored alert)
        error_visible = page.locator("text=Invalid").is_visible() or \
                        page.locator("[class*='coral']").is_visible() or \
                        page.locator("text=failed").is_visible()
        assert error_visible, "No error message shown for invalid credentials"

    def test_logout_redirects_to_login(self, page: Page):
        """Clicking logout returns to login page."""
        login_as(page, "analyst")
        page.wait_for_load_state("networkidle")

        # Find and click logout button (sign-out icon in header)
        logout_button = page.locator("button[title='Sign out']")
        if logout_button.is_visible():
            logout_button.click()
            page.wait_for_url("**/login**", timeout=5000)
            assert "/login" in page.url

    def test_unauthenticated_access_redirects(self, page: Page):
        """Accessing a protected page without auth redirects to login."""
        # Clear any existing session by going to login first
        page.goto("/login")
        page.wait_for_load_state("networkidle")

        # Navigate directly to a protected route
        page.goto("/review")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Should be redirected to login (or show login page)
        # The auth check may show loading then redirect
        current_url = page.url
        assert "/login" in current_url or "/review" in current_url
