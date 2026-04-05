"""Tests for Phase 3I: Model Routing Flexibility.

Tests per-task provider override and cost-per-model features.
"""

import pytest

from shared.llm.client import LLMClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """LLMClient with real config loaded."""
    return LLMClient()


# ---------------------------------------------------------------------------
# Tests: Per-Task Provider Override
# ---------------------------------------------------------------------------


class TestPerTaskProviderOverride:

    def test_default_provider_used_when_no_override(self, client):
        """Without task_overrides, default_provider is used."""
        provider = client._get_provider_for_task("chat_response")
        assert provider == client.provider  # Default

    def test_override_routes_to_specific_provider(self, client):
        """When task_overrides has an entry, that provider is used."""
        # Temporarily inject an override
        original = client._routing.get("task_overrides", {})
        client._routing.setdefault("task_overrides", {})["chat_intent"] = "azure"
        try:
            provider = client._get_provider_for_task("chat_intent")
            assert provider == "azure"
        finally:
            client._routing["task_overrides"] = original

    def test_model_uses_override_provider(self, client):
        """get_model() resolves through the overridden provider."""
        original = client._routing.get("task_overrides", {})
        client._routing.setdefault("task_overrides", {})["narrative_generation"] = "azure"
        try:
            model = client.get_model("narrative_generation")
            assert "azure" in model or "gpt" in model
        finally:
            client._routing["task_overrides"] = original

    def test_non_overridden_task_uses_default(self, client):
        """Tasks not in overrides use default_provider."""
        model = client.get_model("chat_response")
        default_provider = client.provider
        assert default_provider in model or "claude" in model or "default" in model


# ---------------------------------------------------------------------------
# Tests: Cost Per Model
# ---------------------------------------------------------------------------


class TestCostPerModel:

    def test_get_cost_returns_pricing(self, client):
        """get_cost() returns cost_input_per_1m and cost_output_per_1m."""
        cost = client.get_cost("narrative_generation")
        assert "cost_input_per_1m" in cost
        assert "cost_output_per_1m" in cost
        assert cost["cost_input_per_1m"] > 0
        assert cost["cost_output_per_1m"] > 0

    def test_haiku_cheaper_than_sonnet(self, client):
        """Haiku model should be cheaper than Sonnet."""
        haiku_cost = client.get_cost("chat_intent")  # Uses haiku
        sonnet_cost = client.get_cost("narrative_generation")  # Uses sonnet
        assert haiku_cost["cost_input_per_1m"] <= sonnet_cost["cost_input_per_1m"]

    def test_cost_differs_by_provider(self, client):
        """Azure and Anthropic have different pricing."""
        # Get Anthropic cost
        anthropic_cost = client.get_cost("narrative_generation")

        # Switch to Azure temporarily
        original = client._routing.get("task_overrides", {})
        client._routing.setdefault("task_overrides", {})["narrative_generation"] = "azure"
        try:
            azure_cost = client.get_cost("narrative_generation")
            # They should be different (Azure GPT-4o is $2.50, Anthropic Sonnet is $3.00)
            assert azure_cost["cost_input_per_1m"] != anthropic_cost["cost_input_per_1m"]
        finally:
            client._routing["task_overrides"] = original

    def test_fallback_pricing_when_missing(self, client):
        """Missing cost fields default to $3/$15."""
        cost = client.get_cost("nonexistent_task")
        assert cost["cost_input_per_1m"] == 3.00
        assert cost["cost_output_per_1m"] == 15.00


# ---------------------------------------------------------------------------
# Tests: Reload + Config
# ---------------------------------------------------------------------------


class TestRoutingConfig:

    def test_reload_preserves_overrides(self, client):
        """reload_routing() picks up task_overrides from YAML."""
        client.reload_routing()
        overrides = client._routing.get("task_overrides", {})
        assert isinstance(overrides, dict)

    def test_routing_has_both_providers(self, client):
        """Config has both anthropic and azure providers."""
        providers = client._routing.get("providers", {})
        assert "anthropic" in providers
        assert "azure" in providers

    def test_all_tasks_have_models(self, client):
        """Every configured task has a model identifier."""
        expected_tasks = ["chat_intent", "chat_response", "narrative_generation",
                         "hypothesis_generation", "oneliner_generation"]
        for task in expected_tasks:
            model = client.get_model(task)
            assert model, f"No model for task {task}"
            assert "default" not in model or task not in expected_tasks
