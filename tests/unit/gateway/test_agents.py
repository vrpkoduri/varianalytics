"""Unit tests for gateway agents (intent classification, orchestration, tools).

Tests the keyword intent classifier patterns and entity extraction.
"""

import pytest
from services.gateway.agents.intent import (
    Intent,
    KeywordIntentClassifier,
    ExtractedEntities,
)


@pytest.fixture
def classifier() -> KeywordIntentClassifier:
    return KeywordIntentClassifier()


class TestKeywordIntentClassification:
    """Tests for KeywordIntentClassifier pattern matching."""

    def test_revenue_question(self, classifier):
        intent, _ = classifier.classify("How did revenue perform this quarter?")
        assert intent == Intent.REVENUE_OVERVIEW

    def test_pl_question(self, classifier):
        intent, _ = classifier.classify("Show me the P&L statement")
        assert intent == Intent.PL_SUMMARY

    def test_waterfall_question(self, classifier):
        intent, _ = classifier.classify("Show me the waterfall chart")
        assert intent == Intent.WATERFALL

    def test_heatmap_question(self, classifier):
        intent, _ = classifier.classify("Show the geographic heatmap")
        assert intent == Intent.HEATMAP

    def test_trend_question(self, classifier):
        intent, _ = classifier.classify("What are the trailing trends?")
        assert intent == Intent.TREND

    def test_decomposition_question(self, classifier):
        intent, _ = classifier.classify("Break down the volume and price drivers")
        assert intent == Intent.DECOMPOSITION

    def test_netting_question(self, classifier):
        intent, _ = classifier.classify("Are there any netting offsets?")
        assert intent == Intent.NETTING

    def test_review_question(self, classifier):
        intent, _ = classifier.classify("What's pending in the review queue?")
        assert intent == Intent.REVIEW_STATUS

    def test_general_fallback(self, classifier):
        intent, _ = classifier.classify("Hello, how are you?")
        assert intent == Intent.GENERAL

    def test_case_insensitive(self, classifier):
        intent, _ = classifier.classify("SHOW ME THE WATERFALL")
        assert intent == Intent.WATERFALL


class TestEntityExtraction:
    """Tests for entity extraction from user messages."""

    def test_entities_returned(self, classifier):
        _, entities = classifier.classify("How did revenue perform?")
        assert isinstance(entities, ExtractedEntities)

    def test_default_view_is_mtd(self, classifier):
        _, entities = classifier.classify("Show revenue")
        assert entities.view_id == "MTD"

    def test_default_base_is_budget(self, classifier):
        _, entities = classifier.classify("Show revenue")
        assert entities.base_id == "BUDGET"
