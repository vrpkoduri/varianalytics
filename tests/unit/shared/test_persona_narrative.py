"""Tests for persona-based narrative level selection."""

import pytest

from shared.config.persona_config import (
    DEFAULT_NARRATIVE_COLUMN,
    NARRATIVE_LEVEL_MAP,
    get_narrative_column,
    select_narrative,
)


class TestGetNarrativeColumn:
    """Verify persona → narrative column mapping."""

    def test_analyst_returns_detail(self):
        assert get_narrative_column("analyst") == "narrative_detail"

    def test_cfo_returns_summary(self):
        assert get_narrative_column("cfo") == "narrative_summary"

    def test_bu_leader_returns_midlevel(self):
        assert get_narrative_column("bu_leader") == "narrative_midlevel"

    def test_director_returns_midlevel(self):
        assert get_narrative_column("director") == "narrative_midlevel"

    def test_board_returns_board(self):
        assert get_narrative_column("board") == "narrative_board"

    def test_none_returns_default(self):
        assert get_narrative_column(None) == DEFAULT_NARRATIVE_COLUMN

    def test_unknown_persona_returns_default(self):
        assert get_narrative_column("unknown") == DEFAULT_NARRATIVE_COLUMN

    def test_case_insensitive(self):
        assert get_narrative_column("CFO") == "narrative_summary"
        assert get_narrative_column("Analyst") == "narrative_detail"


class TestSelectNarrative:
    """Verify narrative selection with fallback chain."""

    @pytest.fixture
    def full_row(self):
        return {
            "narrative_detail": "Detailed explanation of the variance",
            "narrative_midlevel": "Mid-level summary for BU leaders",
            "narrative_summary": "CFO executive summary",
            "narrative_oneliner": "Revenue up 5%",
            "narrative_board": "Strong quarter",
        }

    def test_analyst_gets_detail(self, full_row):
        assert select_narrative(full_row, "analyst") == "Detailed explanation of the variance"

    def test_cfo_gets_summary(self, full_row):
        assert select_narrative(full_row, "cfo") == "CFO executive summary"

    def test_bu_leader_gets_midlevel(self, full_row):
        assert select_narrative(full_row, "bu_leader") == "Mid-level summary for BU leaders"

    def test_board_gets_board(self, full_row):
        assert select_narrative(full_row, "board") == "Strong quarter"

    def test_fallback_when_preferred_missing(self):
        """If CFO's preferred level (summary) is missing, fall back to detail."""
        row = {"narrative_detail": "Detail only", "narrative_summary": None}
        assert select_narrative(row, "cfo") == "Detail only"

    def test_fallback_chain_order(self):
        """Walk the fallback chain: detail → midlevel → summary → oneliner."""
        row = {"narrative_oneliner": "One liner only"}
        assert select_narrative(row, "analyst") == "One liner only"

    def test_empty_string_skipped(self):
        """Empty strings are treated as missing — fall through to next level."""
        row = {"narrative_detail": "", "narrative_midlevel": "Mid-level text"}
        assert select_narrative(row, "analyst") == "Mid-level text"

    def test_nan_skipped(self):
        """NaN values are treated as missing."""
        row = {"narrative_detail": "nan", "narrative_midlevel": "Real text"}
        assert select_narrative(row, "analyst") == "Real text"

    def test_all_missing_returns_empty(self):
        """If no narrative levels have content, return empty string."""
        row = {"variance_amount": 5000}
        assert select_narrative(row, "cfo") == ""
