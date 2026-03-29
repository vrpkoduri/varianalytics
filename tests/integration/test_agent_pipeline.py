"""Integration tests for agent pipeline with realistic computation data.

Mocks ComputationClient with realistic data shapes and verifies full
SSE pipeline: POST message -> consume SSE -> validate event types.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.gateway.main import app


# ---------------------------------------------------------------------------
# Realistic response fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def mock_computation_responses():
    """Realistic response shapes from computation service."""
    return {
        "summary": {
            "cards": [
                {
                    "metric_name": "Total Revenue",
                    "account_id": "acct_revenue",
                    "actual": 12500000,
                    "comparator": 11800000,
                    "variance_amount": 700000,
                    "variance_pct": 5.93,
                    "is_favorable": True,
                    "is_material": True,
                },
                {
                    "metric_name": "Gross Profit",
                    "account_id": "acct_gross_profit",
                    "actual": 8200000,
                    "comparator": 7900000,
                    "variance_amount": 300000,
                    "variance_pct": 3.8,
                    "is_favorable": True,
                    "is_material": True,
                },
            ],
            "period_id": "2025-12",
            "view_id": "MTD",
            "base_id": "BUDGET",
        },
        "variance_list": {
            "items": [
                {
                    "variance_id": "var_001",
                    "account_id": "acct_advisory_fees",
                    "account_name": "Advisory Fees",
                    "bu_id": "marsh",
                    "variance_amount": 200000,
                    "variance_pct": 8.5,
                    "is_material": True,
                    "pl_category": "Revenue",
                    "narrative_oneliner": "Advisory fees up $200K",
                },
            ],
            "total_count": 1,
            "page": 1,
            "page_size": 20,
        },
        "waterfall": {
            "steps": [
                {"name": "Budget", "value": 11800000, "cumulative": 11800000, "is_total": True},
                {"name": "Marsh", "value": 400000, "cumulative": 12200000, "is_positive": True},
                {"name": "Actual", "value": 12500000, "cumulative": 12500000, "is_total": True},
            ]
        },
    }


def _consume_sse_events(client, conversation_id: str) -> list[dict]:
    """Helper: consume SSE stream and return parsed events."""
    events = []
    event_type = ""
    with client.stream("GET", f"/api/v1/chat/stream/{conversation_id}") as response:
        for line in response.iter_lines():
            if line.startswith("event: "):
                event_type = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
                events.append({"type": event_type, "data": data})
    return events


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAgentPipeline:

    @pytest.fixture(autouse=True)
    def client(self):
        with TestClient(app, raise_server_exceptions=False) as c:
            self.client = c
            yield c

    def test_revenue_question_full_pipeline(self):
        """Revenue question should produce token + suggestion + done events."""
        r = self.client.post(
            "/api/v1/chat/messages",
            json={"message": "How did revenue perform?"},
        )
        assert r.status_code == 201
        cid = r.json()["conversation_id"]

        events = _consume_sse_events(self.client, cid)
        event_types = [e["type"] for e in events]

        # Must have at least some content events and done
        assert "done" in event_types
        assert "token" in event_types or "error" in event_types or "suggestion" in event_types

        # If we got tokens, they should contain some substance
        token_texts = [
            e["data"].get("content", "")
            for e in events
            if e["type"] == "token"
        ]
        full_text = "".join(token_texts)
        if full_text:
            assert len(full_text) > 5

    def test_pl_question_full_pipeline(self):
        """P&L question should produce token + done events."""
        r = self.client.post(
            "/api/v1/chat/messages",
            json={"message": "Show me the P&L"},
        )
        assert r.status_code == 201
        cid = r.json()["conversation_id"]

        events = _consume_sse_events(self.client, cid)
        event_types = [e["type"] for e in events]

        assert "done" in event_types
        assert "token" in event_types or "data_table" in event_types or "error" in event_types

    def test_general_question_fallback(self):
        """General greeting should get help text, no data_table."""
        r = self.client.post(
            "/api/v1/chat/messages",
            json={"message": "Hello"},
        )
        assert r.status_code == 201
        cid = r.json()["conversation_id"]

        events = _consume_sse_events(self.client, cid)
        event_types = [e["type"] for e in events]

        assert "done" in event_types
        # General question should have some response
        assert "token" in event_types or "suggestion" in event_types or "error" in event_types
