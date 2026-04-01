"""Shared Playwright E2E test fixtures.

Provides browser page setup, auto-skip when Docker stack not running,
and reusable login/navigation helpers.

All tests auto-skip if the frontend is not reachable at BASE_URL.
"""

import os
import urllib.request
import urllib.error

import pytest
from playwright.sync_api import Page, expect

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:80")

# Demo credentials
CREDENTIALS = {
    "admin": ("admin@variance-agent.dev", "password123"),
    "analyst": ("analyst@variance-agent.dev", "password123"),
    "director": ("director@variance-agent.dev", "password123"),
    "cfo": ("cfo@variance-agent.dev", "password123"),
    "bu_leader": ("bu.leader@variance-agent.dev", "password123"),
    "board": ("board@variance-agent.dev", "password123"),
}


# ---------------------------------------------------------------------------
# Auto-skip if stack not running
# ---------------------------------------------------------------------------

def _stack_available() -> bool:
    """Check if the frontend is reachable."""
    try:
        urllib.request.urlopen(BASE_URL, timeout=3)
        return True
    except (urllib.error.URLError, OSError):
        return False


STACK_AVAILABLE = _stack_available()

skip_no_stack = pytest.mark.skipif(
    not STACK_AVAILABLE,
    reason=f"Docker stack not available at {BASE_URL}",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def browser_context_args():
    """Configure browser: headless, viewport, base URL."""
    return {
        "viewport": {"width": 1440, "height": 900},
        "base_url": BASE_URL,
        "ignore_https_errors": True,
    }


# ---------------------------------------------------------------------------
# Login helper
# ---------------------------------------------------------------------------

def login_as(page: Page, persona: str = "analyst") -> None:
    """Navigate to login page and sign in as a specific persona.

    Args:
        page: Playwright Page object.
        persona: Key into CREDENTIALS dict (e.g. 'analyst', 'admin', 'cfo').
    """
    email, password = CREDENTIALS[persona]

    page.goto("/login")
    page.wait_for_load_state("networkidle")

    # Fill login form
    page.fill("#email", email)
    page.fill("#password", password)

    # Click submit
    page.click("button[type='submit']")

    # Wait for SPA navigation — React Router changes URL client-side.
    # Poll until we're no longer on /login.
    page.wait_for_timeout(2000)
    for _ in range(15):
        if "/login" not in page.url:
            break
        page.wait_for_timeout(500)

    page.wait_for_load_state("networkidle")


def wait_for_dashboard(page: Page) -> None:
    """Wait for the dashboard to fully load."""
    page.wait_for_load_state("networkidle")
    # Wait for at least one KPI card or section-label to appear
    page.wait_for_selector(".section-label, .glass-card", timeout=10000)
