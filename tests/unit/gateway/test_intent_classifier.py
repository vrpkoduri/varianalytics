"""Tests for KeywordIntentClassifier — intent classification and entity extraction."""

from __future__ import annotations

import pytest

from services.gateway.agents.intent import (
    ExtractedEntities,
    Intent,
    KeywordIntentClassifier,
)


@pytest.fixture
def classifier() -> KeywordIntentClassifier:
    return KeywordIntentClassifier()


# ---------------------------------------------------------------------------
# Intent classification tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_revenue_overview(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("How did revenue perform?")
    assert intent == Intent.REVENUE_OVERVIEW


@pytest.mark.unit
def test_revenue_sales_keyword(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("What are the sales numbers?")
    assert intent == Intent.REVENUE_OVERVIEW


@pytest.mark.unit
def test_pl_summary(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("Show me the P&L")
    assert intent == Intent.PL_SUMMARY


@pytest.mark.unit
def test_income_statement(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("Pull up the income statement")
    assert intent == Intent.PL_SUMMARY


@pytest.mark.unit
def test_waterfall(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("Show revenue waterfall by BU")
    assert intent == Intent.WATERFALL


@pytest.mark.unit
def test_heatmap(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("Show me the variance heatmap")
    assert intent == Intent.HEATMAP


@pytest.mark.unit
def test_trend(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("What's the revenue trend?")
    assert intent == Intent.TREND


@pytest.mark.unit
def test_decomposition(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("Break down the revenue variance")
    assert intent == Intent.DECOMPOSITION


@pytest.mark.unit
def test_review(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("What needs review?")
    assert intent == Intent.REVIEW_STATUS


@pytest.mark.unit
def test_netting(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("Are there any netting issues?")
    assert intent == Intent.NETTING


@pytest.mark.unit
def test_drill_down(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("Drill into APAC")
    assert intent == Intent.DRILL_DOWN


@pytest.mark.unit
def test_general_fallback(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("Tell me a joke")
    assert intent == Intent.GENERAL


@pytest.mark.unit
def test_case_insensitive(classifier: KeywordIntentClassifier):
    intent, _ = classifier.classify("SHOW ME THE P&L")
    assert intent == Intent.PL_SUMMARY


# ---------------------------------------------------------------------------
# Entity extraction tests — Business Unit
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_entity_bu_marsh(classifier: KeywordIntentClassifier):
    _, entities = classifier.classify("How did Marsh perform?")
    assert entities.bu_id == "marsh"


@pytest.mark.unit
def test_entity_bu_guy_carpenter(classifier: KeywordIntentClassifier):
    _, entities = classifier.classify("Guy Carpenter revenue")
    assert entities.bu_id == "guy_carpenter"


# ---------------------------------------------------------------------------
# Entity extraction tests — Period
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_entity_period_month(classifier: KeywordIntentClassifier):
    _, entities = classifier.classify("March 2026 revenue")
    assert entities.period_id == "2026-03"


@pytest.mark.unit
def test_entity_period_format(classifier: KeywordIntentClassifier):
    _, entities = classifier.classify("2026-06 P&L")
    assert entities.period_id == "2026-06"


# ---------------------------------------------------------------------------
# Entity extraction tests — Account
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_entity_account_ebitda(classifier: KeywordIntentClassifier):
    _, entities = classifier.classify("EBITDA trend")
    assert entities.account_id == "acct_ebitda"


@pytest.mark.unit
def test_entity_account_revenue(classifier: KeywordIntentClassifier):
    _, entities = classifier.classify("revenue breakdown")
    assert entities.account_id in ("acct_revenue", "acct_gross_revenue")


# ---------------------------------------------------------------------------
# UI context defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ui_context_defaults(classifier: KeywordIntentClassifier):
    """When no entities in the message, ui_context values are used."""
    ui_context = {
        "period_id": "2026-01",
        "bu_id": "mercer",
        "view_id": "QTD",
        "base_id": "FORECAST",
    }
    _, entities = classifier.classify("Tell me a joke", ui_context=ui_context)
    assert entities.period_id == "2026-01"
    assert entities.bu_id == "mercer"
    assert entities.view_id == "QTD"
    assert entities.base_id == "FORECAST"
