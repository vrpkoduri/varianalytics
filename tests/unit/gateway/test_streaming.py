"""Unit tests for SSE streaming infrastructure.

Tests event serialisation, StreamingContext emit/iterate lifecycle,
and ConversationManager CRUD operations.
"""

import asyncio
import json

import pytest

from services.gateway.streaming.context import StreamingContext
from services.gateway.streaming.events import (
    ConfidenceEvent,
    DataTableEvent,
    DoneEvent,
    ErrorEvent,
    MiniChartEvent,
    NettingAlertEvent,
    ReviewStatusEvent,
    SSEEvent,
    SSEEventType,
    SuggestionEvent,
    TokenEvent,
)
from services.gateway.streaming.manager import ConversationManager


# ---------------------------------------------------------------------------
# Event serialisation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSSEEventSerialisation:
    """Verify SSE wire-format output for each event type."""

    def test_token_event_serialisation(self) -> None:
        event = SSEEvent(
            event_type=SSEEventType.TOKEN,
            data=TokenEvent(text="Hello"),
        )
        sse = event.to_sse()
        assert sse.startswith("event: token\n")
        assert "data: " in sse
        assert sse.endswith("\n\n")
        payload = json.loads(sse.split("data: ", 1)[1].strip())
        assert payload["text"] == "Hello"

    def test_data_table_event_serialisation(self) -> None:
        event = SSEEvent(
            event_type=SSEEventType.DATA_TABLE,
            data=DataTableEvent(
                title="Revenue by Region",
                columns=["Region", "Actual", "Budget", "Variance"],
                rows=[
                    ["Americas", 1200000, 1100000, 100000],
                    ["EMEA", 800000, 850000, -50000],
                ],
                footer="Total variance: $50,000 F",
            ),
        )
        sse = event.to_sse()
        assert sse.startswith("event: data_table\n")
        payload = json.loads(sse.split("data: ", 1)[1].strip())
        assert payload["title"] == "Revenue by Region"
        assert len(payload["columns"]) == 4
        assert len(payload["rows"]) == 2
        assert payload["footer"] == "Total variance: $50,000 F"

    def test_mini_chart_event_serialisation(self) -> None:
        event = SSEEvent(
            event_type=SSEEventType.MINI_CHART,
            data=MiniChartEvent(
                chart_type="bar",
                title="Revenue Trend",
                data=[{"month": "Jan", "value": 100}, {"month": "Feb", "value": 120}],
            ),
        )
        sse = event.to_sse()
        assert "event: mini_chart\n" in sse
        payload = json.loads(sse.split("data: ", 1)[1].strip())
        assert payload["chart_type"] == "bar"

    def test_suggestion_event_serialisation(self) -> None:
        event = SSEEvent(
            event_type=SSEEventType.SUGGESTION,
            data=SuggestionEvent(suggestions=["Drill into EMEA", "Show trend"]),
        )
        sse = event.to_sse()
        payload = json.loads(sse.split("data: ", 1)[1].strip())
        assert len(payload["suggestions"]) == 2

    def test_confidence_event_serialisation(self) -> None:
        event = SSEEvent(
            event_type=SSEEventType.CONFIDENCE,
            data=ConfidenceEvent(score=0.85, label="high"),
        )
        sse = event.to_sse()
        payload = json.loads(sse.split("data: ", 1)[1].strip())
        assert payload["score"] == 0.85
        assert payload["label"] == "high"

    def test_netting_alert_event_serialisation(self) -> None:
        event = SSEEvent(
            event_type=SSEEventType.NETTING_ALERT,
            data=NettingAlertEvent(
                node_id="geo_americas",
                node_name="Americas",
                net_variance=5000,
                gross_variance=200000,
                netting_ratio=0.025,
                message="Americas nets to immaterial variance",
            ),
        )
        sse = event.to_sse()
        payload = json.loads(sse.split("data: ", 1)[1].strip())
        assert payload["node_id"] == "geo_americas"
        assert payload["netting_ratio"] == 0.025

    def test_review_status_event_serialisation(self) -> None:
        event = SSEEvent(
            event_type=SSEEventType.REVIEW_STATUS,
            data=ReviewStatusEvent(
                variance_id="var_123",
                status="ANALYST_REVIEWED",
                message="Reviewed by analyst",
            ),
        )
        sse = event.to_sse()
        payload = json.loads(sse.split("data: ", 1)[1].strip())
        assert payload["status"] == "ANALYST_REVIEWED"

    def test_error_event_serialisation(self) -> None:
        event = SSEEvent(
            event_type=SSEEventType.ERROR,
            data=ErrorEvent(message="Something went wrong", code="AGENT_ERROR"),
        )
        sse = event.to_sse()
        payload = json.loads(sse.split("data: ", 1)[1].strip())
        assert payload["message"] == "Something went wrong"
        assert payload["code"] == "AGENT_ERROR"

    def test_done_event_serialisation(self) -> None:
        event = SSEEvent(
            event_type=SSEEventType.DONE,
            data=DoneEvent(
                conversation_id="conv_1",
                message_id="msg_1",
                total_tokens=150,
            ),
        )
        sse = event.to_sse()
        payload = json.loads(sse.split("data: ", 1)[1].strip())
        assert payload["conversation_id"] == "conv_1"
        assert payload["total_tokens"] == 150


# ---------------------------------------------------------------------------
# StreamingContext
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestStreamingContext:
    """Test StreamingContext emit/iterate lifecycle."""

    async def test_streaming_context_emits_events(self) -> None:
        ctx = StreamingContext(conversation_id="c1", message_id="m1")

        # Emit tokens in background
        async def _emit():
            await ctx.emit_token("Hello ")
            await ctx.emit_token("world!")
            await ctx.emit_done()

        asyncio.create_task(_emit())

        chunks: list[str] = []
        async for chunk in ctx:
            chunks.append(chunk)

        assert len(chunks) == 3  # 2 tokens + 1 done
        assert "Hello " in chunks[0]
        assert "world!" in chunks[1]
        assert "event: done" in chunks[2]

    async def test_streaming_context_done_sentinel(self) -> None:
        ctx = StreamingContext(conversation_id="c1", message_id="m1")

        async def _emit():
            await ctx.emit_token("test")
            await ctx.emit_done()

        asyncio.create_task(_emit())

        chunks = []
        async for chunk in ctx:
            chunks.append(chunk)

        # Iterator should stop after done
        assert len(chunks) == 2
        assert ctx._done is True

    async def test_emit_after_done_is_noop(self) -> None:
        ctx = StreamingContext(conversation_id="c1", message_id="m1")
        await ctx.emit_done()

        # Queue should have done event + None sentinel
        # Emitting after done should be silently ignored
        await ctx.emit_token("this should be ignored")
        # Queue should still only have 2 items (done event + None sentinel)
        assert ctx._queue.qsize() == 2

    async def test_all_event_types_emit(self) -> None:
        ctx = StreamingContext(conversation_id="c1", message_id="m1")

        async def _emit():
            await ctx.emit_token("text")
            await ctx.emit_data_table("T", ["A"], [[1]])
            await ctx.emit_mini_chart("bar", "Chart", [{"x": 1}])
            await ctx.emit_suggestion(["Q1"])
            await ctx.emit_confidence(0.9, "high")
            await ctx.emit_netting_alert("n1", "Node", 100, 5000, 0.02, "msg")
            await ctx.emit_review_status("v1", "AI_DRAFT", "Draft generated")
            await ctx.emit_error("oops", "ERR")
            await ctx.emit_done()

        asyncio.create_task(_emit())

        chunks = []
        async for chunk in ctx:
            chunks.append(chunk)

        assert len(chunks) == 9
        event_types = [c.split("\n")[0].split(": ", 1)[1] for c in chunks]
        assert event_types == [
            "token",
            "data_table",
            "mini_chart",
            "suggestion",
            "confidence",
            "netting_alert",
            "review_status",
            "error",
            "done",
        ]


# ---------------------------------------------------------------------------
# ConversationManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConversationManager:
    """Test ConversationManager CRUD and stream lifecycle."""

    def test_create_conversation_returns_id(self) -> None:
        mgr = ConversationManager()
        cid = mgr.create_conversation(user_id="user_1", title="Test")
        assert isinstance(cid, str)
        assert len(cid) > 0

    def test_get_conversation(self) -> None:
        mgr = ConversationManager()
        cid = mgr.create_conversation(user_id="user_1", title="Test")
        conv = mgr.get_conversation(cid)
        assert conv is not None
        assert conv["title"] == "Test"
        assert conv["user_id"] == "user_1"

    def test_get_nonexistent_conversation(self) -> None:
        mgr = ConversationManager()
        assert mgr.get_conversation("nonexistent") is None

    def test_delete_conversation(self) -> None:
        mgr = ConversationManager()
        cid = mgr.create_conversation(user_id="user_1")
        assert mgr.delete_conversation(cid) is True
        assert mgr.get_conversation(cid) is None

    def test_delete_nonexistent_conversation(self) -> None:
        mgr = ConversationManager()
        assert mgr.delete_conversation("nonexistent") is False

    def test_list_conversations(self) -> None:
        mgr = ConversationManager()
        mgr.create_conversation(user_id="user_1", title="Conv 1")
        mgr.create_conversation(user_id="user_2", title="Conv 2")
        mgr.create_conversation(user_id="user_1", title="Conv 3")

        all_convs = mgr.list_conversations()
        assert len(all_convs) == 3

        user1_convs = mgr.list_conversations(user_id="user_1")
        assert len(user1_convs) == 2
        assert all(c["title"] in ("Conv 1", "Conv 3") for c in user1_convs)

    def test_list_conversations_returns_summaries(self) -> None:
        mgr = ConversationManager()
        cid = mgr.create_conversation(user_id="user_1", title="Test")
        mgr.add_message(cid, "m1", "user", "Hello")
        mgr.add_message(cid, "m2", "assistant", "Hi there")

        convs = mgr.list_conversations()
        assert len(convs) == 1
        assert convs[0]["message_count"] == 2
        assert "messages" not in convs[0]  # summaries only

    def test_stream_lifecycle(self) -> None:
        mgr = ConversationManager()
        cid = mgr.create_conversation(user_id="user_1")

        # No stream initially
        assert mgr.get_stream(cid) is None

        # Create stream
        ctx = mgr.create_stream(cid)
        assert ctx is not None
        assert ctx.conversation_id == cid
        assert mgr.get_stream(cid) is ctx

        # Remove stream
        mgr.remove_stream(cid)
        assert mgr.get_stream(cid) is None

    def test_create_stream_replaces_existing(self) -> None:
        mgr = ConversationManager()
        cid = mgr.create_conversation(user_id="user_1")
        ctx1 = mgr.create_stream(cid)
        ctx2 = mgr.create_stream(cid)
        assert ctx1 is not ctx2
        assert mgr.get_stream(cid) is ctx2

    def test_add_message(self) -> None:
        mgr = ConversationManager()
        cid = mgr.create_conversation(user_id="user_1")
        mgr.add_message(cid, "m1", "user", "Hello", {"period_id": "2024-01"})

        conv = mgr.get_conversation(cid)
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Hello"
        assert conv["messages"][0]["context"]["period_id"] == "2024-01"
