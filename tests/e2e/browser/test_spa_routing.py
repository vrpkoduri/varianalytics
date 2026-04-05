"""SPA routing E2E tests — verify direct URL navigation and page reload.

Each test navigates directly to a route, verifies content loads, then
reloads the page and verifies it still loads (proving the SPA catch-all
routing fix works for all 8 pages).

Auto-skips if Docker stack is not running.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.browser.conftest import skip_no_stack, login_as, BASE_URL


@skip_no_stack
@pytest.mark.playwright
class TestSPARouting:
    """Direct-URL navigation and reload for every SPA route."""

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _assert_page_loaded(page: Page, timeout: int = 10_000) -> None:
        """Assert the page has meaningful content (not a blank 404)."""
        page.wait_for_load_state("networkidle")
        # Every authenticated page has a <header> and at least one visible element
        header = page.locator("header")
        expect(header).to_be_visible(timeout=timeout)

    # ------------------------------------------------------------------ #
    # Dashboard (/)
    # ------------------------------------------------------------------ #

    def test_direct_url_dashboard(self, page: Page):
        """Navigate directly to / — dashboard loads and survives reload."""
        login_as(page, "analyst")
        page.goto("/")
        self._assert_page_loaded(page)

        page.reload()
        self._assert_page_loaded(page)

    # ------------------------------------------------------------------ #
    # Executive (/executive)
    # ------------------------------------------------------------------ #

    def test_direct_url_executive(self, page: Page):
        """Navigate directly to /executive — page loads and survives reload."""
        login_as(page, "cfo")
        page.goto("/executive")
        self._assert_page_loaded(page)

        page.reload()
        self._assert_page_loaded(page)

    # ------------------------------------------------------------------ #
    # P&L (/pl)
    # ------------------------------------------------------------------ #

    def test_direct_url_pl(self, page: Page):
        """Navigate directly to /pl — P&L view loads and survives reload."""
        login_as(page, "analyst")
        page.goto("/pl")
        self._assert_page_loaded(page)

        page.reload()
        self._assert_page_loaded(page)

    # ------------------------------------------------------------------ #
    # Chat (/chat)
    # ------------------------------------------------------------------ #

    def test_direct_url_chat(self, page: Page):
        """Navigate directly to /chat — chat view loads and survives reload."""
        login_as(page, "analyst")
        page.goto("/chat")
        self._assert_page_loaded(page)

        page.reload()
        self._assert_page_loaded(page)

    # ------------------------------------------------------------------ #
    # Review (/review)
    # ------------------------------------------------------------------ #

    def test_direct_url_review(self, page: Page):
        """Navigate directly to /review — review queue loads and survives reload."""
        login_as(page, "analyst")
        page.goto("/review")
        self._assert_page_loaded(page)

        page.reload()
        self._assert_page_loaded(page)

    # ------------------------------------------------------------------ #
    # Approval (/approval)
    # ------------------------------------------------------------------ #

    def test_direct_url_approval(self, page: Page):
        """Navigate directly to /approval — approval queue loads and survives reload."""
        login_as(page, "director")
        page.goto("/approval")
        self._assert_page_loaded(page)

        page.reload()
        self._assert_page_loaded(page)

    # ------------------------------------------------------------------ #
    # Reports (/reports)
    # ------------------------------------------------------------------ #

    def test_direct_url_reports(self, page: Page):
        """Navigate directly to /reports — reports page loads and survives reload."""
        login_as(page, "analyst")
        page.goto("/reports")
        self._assert_page_loaded(page)

        page.reload()
        self._assert_page_loaded(page)

    # ------------------------------------------------------------------ #
    # Admin (/admin)
    # ------------------------------------------------------------------ #

    def test_direct_url_admin(self, page: Page):
        """Navigate directly to /admin — admin page loads and survives reload."""
        login_as(page, "admin")
        page.goto("/admin")
        self._assert_page_loaded(page)

        page.reload()
        self._assert_page_loaded(page)
