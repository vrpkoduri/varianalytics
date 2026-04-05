"""Unit tests for the KeywordIntentClassifier.

Verifies that keyword patterns map user messages to the correct
Intent enum values, and that entity extraction pulls structured
fields (e.g. bu_id) from natural language.
"""

from __future__ import annotations

import pytest

from services.gateway.agents.intent import Intent, KeywordIntentClassifier


@pytest.fixture()
def classifier() -> KeywordIntentClassifier:
    return KeywordIntentClassifier()


# ---------------------------------------------------------------------------
# Intent classification tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKeywordIntentClassification:
    """Verify keyword → Intent mapping for common user messages."""

    def test_top_variances_maps_to_revenue_overview(self, classifier: KeywordIntentClassifier) -> None:
        intent, _ = classifier.classify("Top variances?")
        assert intent is Intent.REVENUE_OVERVIEW

    def test_biggest_variance_maps_to_revenue_overview(self, classifier: KeywordIntentClassifier) -> None:
        intent, _ = classifier.classify("What are the biggest variances?")
        assert intent is Intent.REVENUE_OVERVIEW

    def test_revenue_performance_maps_to_revenue_overview(self, classifier: KeywordIntentClassifier) -> None:
        intent, _ = classifier.classify("How did revenue perform?")
        assert intent is Intent.REVENUE_OVERVIEW

    def test_executive_summary_maps_to_revenue_overview(self, classifier: KeywordIntentClassifier) -> None:
        intent, _ = classifier.classify("Executive summary")
        assert intent is Intent.REVENUE_OVERVIEW

    def test_show_pl_maps_to_pl_summary(self, classifier: KeywordIntentClassifier) -> None:
        intent, _ = classifier.classify("Show me the P&L")
        assert intent is Intent.PL_SUMMARY

    def test_ebitda_bridge_maps_to_waterfall(self, classifier: KeywordIntentClassifier) -> None:
        intent, _ = classifier.classify("EBITDA bridge")
        assert intent is Intent.WATERFALL

    def test_emerging_risks_maps_to_trend(self, classifier: KeywordIntentClassifier) -> None:
        intent, _ = classifier.classify("emerging risks")
        assert intent is Intent.TREND

    def test_what_needs_review_maps_to_review(self, classifier: KeywordIntentClassifier) -> None:
        intent, _ = classifier.classify("What needs review?")
        assert intent is Intent.REVIEW_STATUS

    def test_unrecognized_falls_to_general(self, classifier: KeywordIntentClassifier) -> None:
        intent, _ = classifier.classify("Hello")
        assert intent is Intent.GENERAL


# ---------------------------------------------------------------------------
# Entity extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKeywordEntityExtraction:
    """Verify entity extraction from user messages."""

    def test_entity_extraction_bu(self, classifier: KeywordIntentClassifier) -> None:
        """'How is Marsh revenue?' should extract bu_id='marsh'."""
        _, entities = classifier.classify("How is Marsh revenue?")
        assert entities.bu_id == "marsh"
