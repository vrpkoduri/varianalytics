"""Playwright E2E tests for the Executive Summary landing page.

Tests that the page renders correctly for leadership personas
and is inaccessible to analyst/non-leadership roles.
Auto-skips if Docker stack is not running.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.browser.conftest import skip_no_stack, login_as, wait_for_dashboard


@skip_no_stack
@pytest.mark.playwright
class TestExecSummaryPage:
    """Browser-based Executive Summary page E2E tests."""

    def test_cfo_sees_exec_summary_tab(self, page: Page):
        """CFO sees Exec Summary tab in navigation."""
        login_as(page, "cfo")
        wait_for_dashboard(page)

        exec_tab = page.get_by_role("button", name="Exec Summary", exact=True)
        expect(exec_tab).to_be_visible()

    def test_director_sees_exec_summary_tab(self, page: Page):
        """Director sees Exec Summary tab in navigation."""
        login_as(page, "director")
        wait_for_dashboard(page)

        exec_tab = page.get_by_role("button", name="Exec Summary", exact=True)
        expect(exec_tab).to_be_visible()

    def test_admin_sees_exec_summary_tab(self, page: Page):
        """Admin sees Exec Summary tab in navigation."""
        login_as(page, "admin")
        wait_for_dashboard(page)

        exec_tab = page.get_by_role("button", name="Exec Summary", exact=True)
        expect(exec_tab).to_be_visible()

    def test_exec_page_loads_with_headline(self, page: Page):
        """Executive Summary page loads with a headline."""
        login_as(page, "cfo")
        wait_for_dashboard(page)

        page.get_by_role("button", name="Exec Summary", exact=True).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        assert "/executive" in page.url

        # Should show THE HEADLINE section
        headline_label = page.locator("text=THE HEADLINE")
        expect(headline_label).to_be_visible()

    def test_exec_page_has_section_narratives(self, page: Page):
        """Page shows section narrative cards (Revenue, Cost, Profitability)."""
        login_as(page, "cfo")
        wait_for_dashboard(page)

        page.get_by_role("button", name="Exec Summary", exact=True).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Should have section labels
        revenue_section = page.locator("text=REVENUE")
        expect(revenue_section.first).to_be_visible()

    def test_exec_page_has_profitability_gauges(self, page: Page):
        """Page shows profitability section with margin gauges."""
        login_as(page, "cfo")
        wait_for_dashboard(page)

        page.get_by_role("button", name="Exec Summary", exact=True).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        profitability = page.get_by_text("PROFITABILITY", exact=True)
        expect(profitability).to_be_visible()

    def test_exec_page_has_download_buttons(self, page: Page):
        """Page shows download buttons for Board Deck and Executive Flash."""
        login_as(page, "cfo")
        wait_for_dashboard(page)

        page.get_by_role("button", name="Exec Summary", exact=True).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        export_section = page.locator("text=EXPORT")
        expect(export_section).to_be_visible()

    def test_analyst_cannot_see_exec_tab(self, page: Page):
        """Analyst does NOT see Exec Summary tab."""
        login_as(page, "analyst")
        wait_for_dashboard(page)

        # Exec Summary tab should NOT be visible for analyst
        exec_tabs = page.locator("button:has-text('Exec Summary')")
        assert exec_tabs.count() == 0, "Analyst should not see Exec Summary tab"
