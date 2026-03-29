"""Live LLM integration tests. Only run when API key is available.

Skip with: pytest -m "not llm"
Run with: pytest -m llm tests/integration/test_llm_live.py -v
"""

import os

import pytest

from services.gateway.agents.intent import Intent, LLMIntentClassifier
from shared.llm.client import LLMClient
from shared.llm.narrative import NarrativeGenerator

pytestmark = [
    pytest.mark.integration,
    pytest.mark.llm,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY")
        and not os.environ.get("AZURE_OPENAI_API_KEY"),
        reason="No LLM API key configured",
    ),
]


@pytest.fixture
def llm_client() -> LLMClient:
    return LLMClient()


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_intent_classification(llm_client: LLMClient):
    """Real LLM call to classify a revenue question."""
    classifier = LLMIntentClassifier(llm_client)
    intent, entities = await classifier.classify("How did revenue perform this quarter?")

    assert intent == Intent.REVENUE_OVERVIEW


# ---------------------------------------------------------------------------
# Narrative generation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_narrative_generation(llm_client: LLMClient):
    """Real LLM call to generate a revenue narrative."""
    gen = NarrativeGenerator(llm_client)

    sample_data = {
        "actual": 5_000_000,
        "comparator": 4_800_000,
        "variance": 200_000,
        "pct": "+4.2%",
        "top_variances": [
            {"name": "Marsh", "variance": 150_000, "pct": "+6.0%"},
        ],
    }

    result = await gen.generate_complete(
        "revenue_agent",
        Intent.REVENUE_OVERVIEW,
        sample_data,
    )

    assert isinstance(result, str)
    assert len(result) > 50  # Should be a meaningful narrative


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_streaming_response(llm_client: LLMClient):
    """Real streaming call — collect all chunks and verify non-empty."""
    messages = [
        {"role": "system", "content": "You are a helpful financial analyst."},
        {"role": "user", "content": "Summarise revenue performance in one sentence."},
    ]

    chunks: list[str] = []
    async for chunk in llm_client.stream("chat_response", messages):
        chunks.append(chunk)

    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert len(full_text) > 10
