"""Tests for narrative accuracy guardrails and confidence scoring.

Validates the numerical validation function and confidence computation.
"""

import pytest

from services.computation.engine.pass5_narrative import (
    _validate_narrative_numbers,
    _compute_narrative_confidence,
)


class TestNumericalValidation:
    """Tests for _validate_narrative_numbers()."""

    def test_valid_narrative_accepted(self):
        """Narrative with correct amounts passes validation."""
        narrative = "Revenue increased by $298 (+0.9%) vs Budget."
        var_dict = {"variance_amount": 298, "variance_pct": 0.9}
        assert _validate_narrative_numbers(narrative, var_dict) is True

    def test_hallucination_rejected(self):
        """Narrative with 10x the actual amount is rejected."""
        narrative = "Revenue increased by $50,000 (+45%) vs Budget."
        var_dict = {"variance_amount": 298, "variance_pct": 0.9}
        assert _validate_narrative_numbers(narrative, var_dict) is False

    def test_zero_variance_always_valid(self):
        """Zero variance amount → always valid (no division risk)."""
        narrative = "Revenue was flat at $0."
        var_dict = {"variance_amount": 0}
        assert _validate_narrative_numbers(narrative, var_dict) is True

    def test_thousands_suffix_parsed(self):
        """$50K should be parsed as $50,000."""
        narrative = "Revenue decreased by $50K vs Budget."
        var_dict = {"variance_amount": 45000}
        assert _validate_narrative_numbers(narrative, var_dict) is True  # 50K/45K < 2x

    def test_millions_suffix_parsed(self):
        """$2M should be parsed as $2,000,000."""
        narrative = "Total variance of $2M driven by volume."
        var_dict = {"variance_amount": 100000}
        # $2M / $100K = 20x → hallucination
        assert _validate_narrative_numbers(narrative, var_dict) is False


class TestConfidenceScoring:
    """Tests for _compute_narrative_confidence()."""

    def test_no_decomposition_low_confidence(self):
        """No decomposition data → 0.3 confidence."""
        var_dict = {"variance_id": "test-123"}
        context_maps = {"decomposition": {}}
        assert _compute_narrative_confidence(var_dict, context_maps) == 0.3

    def test_fallback_decomposition_medium_confidence(self):
        """Fallback decomposition → 0.6 confidence."""
        var_dict = {"variance_id": "test-123", "variance_amount": 1000}
        context_maps = {"decomposition": {"test-123": {"is_fallback": True, "residual": 100}}}
        assert _compute_narrative_confidence(var_dict, context_maps) == 0.6

    def test_real_decomposition_high_confidence(self):
        """Real decomposition (not fallback) → 0.9 confidence."""
        var_dict = {"variance_id": "test-123", "variance_amount": 1000}
        context_maps = {"decomposition": {"test-123": {"is_fallback": False, "residual": 50}}}
        assert _compute_narrative_confidence(var_dict, context_maps) == 0.9

    def test_high_residual_low_confidence(self):
        """Fallback with >40% residual → 0.3 confidence."""
        var_dict = {"variance_id": "test-123", "variance_amount": 1000}
        context_maps = {"decomposition": {"test-123": {"is_fallback": True, "residual": 500}}}
        assert _compute_narrative_confidence(var_dict, context_maps) == 0.3
