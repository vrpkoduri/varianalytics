"""Integration tests for chat SSE streaming endpoints.

Tests the full HTTP flow: POST message then GET SSE stream.
Uses FastAPI TestClient with httpx for async SSE consumption.
"""

import json

import pytest
from fastapi.testclient import TestClient

from services.gateway.main import app


@pytest.mark.integration
class TestChatSSE:
    """Integration tests for chat message + SSE stream endpoints."""

    @pytest.fixture(autouse=True)
    def client(self) -> TestClient:
        """Create a test client with lifespan events."""
        with TestClient(app, raise_server_exceptions=False) as client:
            self.client = client
            yield client

    def test_post_message_returns_conversation_id(self) -> None:
        """POST /api/v1/chat/messages should return conversation_id and stream_url."""
        response = self.client.post(
            "/api/v1/chat/messages",
            json={"message": "How did revenue perform this quarter?"},
        )
        assert response.status_code == 201
        body = response.json()
        assert "conversation_id" in body
        assert "message_id" in body
        assert "stream_url" in body
        assert body["stream_url"].startswith("/api/v1/chat/stream/")

    def test_post_message_with_existing_conversation(self) -> None:
        """POST with an existing conversation_id should reuse it."""
        # Create first message
        r1 = self.client.post(
            "/api/v1/chat/messages",
            json={"message": "First message"},
        )
        cid = r1.json()["conversation_id"]

        # Send second message to same conversation
        r2 = self.client.post(
            "/api/v1/chat/messages",
            json={"message": "Second message", "conversation_id": cid},
        )
        assert r2.status_code == 201
        assert r2.json()["conversation_id"] == cid

    def test_post_message_with_context(self) -> None:
        """POST with filter context should succeed."""
        response = self.client.post(
            "/api/v1/chat/messages",
            json={
                "message": "Show me the P&L",
                "context": {"period_id": "2024-01", "bu_id": "bu_north"},
            },
        )
        assert response.status_code == 201

    def test_stream_returns_sse_events(self) -> None:
        """GET /api/v1/chat/stream/{id} should return SSE events.

        Verifies the placeholder agent emits: token, token, suggestion, done.
        """
        # Post message first
        r = self.client.post(
            "/api/v1/chat/messages",
            json={"message": "Hello agent"},
        )
        cid = r.json()["conversation_id"]

        # Consume SSE stream
        with self.client.stream("GET", f"/api/v1/chat/stream/{cid}") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            events = []
            for line in response.iter_lines():
                if line.startswith("event: "):
                    event_type = line[len("event: "):]
                elif line.startswith("data: "):
                    data = json.loads(line[len("data: "):])
                    events.append({"type": event_type, "data": data})

        # Verify placeholder agent response
        assert len(events) >= 3
        event_types = [e["type"] for e in events]
        assert "token" in event_types
        assert "suggestion" in event_types
        assert "done" in event_types

        # Verify token content
        token_events = [e for e in events if e["type"] == "token"]
        assert any("received" in e["data"]["text"].lower() for e in token_events)

        # Verify suggestions
        suggestion_events = [e for e in events if e["type"] == "suggestion"]
        assert len(suggestion_events[0]["data"]["suggestions"]) == 2

        # Verify done
        done_events = [e for e in events if e["type"] == "done"]
        assert done_events[0]["data"]["conversation_id"] == cid

    def test_stream_nonexistent_conversation_returns_404(self) -> None:
        """GET stream for unknown conversation should return 404."""
        response = self.client.get("/api/v1/chat/stream/nonexistent-id")
        assert response.status_code == 404

    def test_list_conversations(self) -> None:
        """GET /api/v1/chat/conversations should list created conversations."""
        # Create a conversation
        self.client.post(
            "/api/v1/chat/messages",
            json={"message": "Test message"},
        )

        response = self.client.get("/api/v1/chat/conversations")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1
        assert len(body["conversations"]) >= 1
        conv = body["conversations"][0]
        assert "conversation_id" in conv
        assert "title" in conv
        assert "created_at" in conv
        assert "message_count" in conv

    def test_delete_conversation(self) -> None:
        """DELETE /api/v1/chat/conversations/{id} should remove the conversation."""
        r = self.client.post(
            "/api/v1/chat/messages",
            json={"message": "To be deleted"},
        )
        cid = r.json()["conversation_id"]

        # Delete it
        response = self.client.delete(f"/api/v1/chat/conversations/{cid}")
        assert response.status_code == 204

        # Verify it's gone
        response = self.client.delete(f"/api/v1/chat/conversations/{cid}")
        assert response.status_code == 404

    def test_delete_nonexistent_conversation_returns_404(self) -> None:
        """DELETE unknown conversation should return 404."""
        response = self.client.delete("/api/v1/chat/conversations/nonexistent")
        assert response.status_code == 404
