"""Streaming context for SSE event emission.

Provides an async-queue-backed context that agents write typed events into.
The SSE endpoint reads from the queue via the async iterator protocol.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional

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

logger = logging.getLogger("gateway.streaming")


class StreamingContext:
    """Async context for emitting SSE events to a client.

    Agents write events via ``emit_*`` methods.
    The SSE generator reads from the internal queue via ``__aiter__``.

    Usage::

        ctx = StreamingContext(conversation_id="abc", message_id="m1")

        # Agent side
        await ctx.emit_token("Hello ")
        await ctx.emit_token("world!")
        await ctx.emit_done()

        # SSE endpoint side
        async for chunk in ctx:
            yield chunk  # already SSE wire-formatted
    """

    def __init__(self, conversation_id: str, message_id: str) -> None:
        self.conversation_id = conversation_id
        self.message_id = message_id
        self._queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        self._done = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _put(self, event: SSEEvent) -> None:
        """Enqueue an event. No-op if already done."""
        if self._done:
            logger.warning(
                "Attempted to emit event after done: conversation_id=%s",
                self.conversation_id,
            )
            return
        await self._queue.put(event)

    # ------------------------------------------------------------------
    # Typed emit methods
    # ------------------------------------------------------------------

    async def emit_token(self, text: str) -> None:
        """Emit a partial text token."""
        await self._put(
            SSEEvent(event_type=SSEEventType.TOKEN, data=TokenEvent(text=text))
        )

    async def emit_data_table(
        self,
        title: str,
        columns: list[str],
        rows: list[list],
        footer: Optional[str] = None,
    ) -> None:
        """Emit a structured data table."""
        await self._put(
            SSEEvent(
                event_type=SSEEventType.DATA_TABLE,
                data=DataTableEvent(
                    title=title, columns=columns, rows=rows, footer=footer
                ),
            )
        )

    async def emit_mini_chart(
        self, chart_type: str, title: str, data: list[dict]
    ) -> None:
        """Emit a mini chart specification."""
        await self._put(
            SSEEvent(
                event_type=SSEEventType.MINI_CHART,
                data=MiniChartEvent(chart_type=chart_type, title=title, data=data),
            )
        )

    async def emit_suggestion(self, suggestions: list[str]) -> None:
        """Emit follow-up question suggestions."""
        await self._put(
            SSEEvent(
                event_type=SSEEventType.SUGGESTION,
                data=SuggestionEvent(suggestions=suggestions),
            )
        )

    async def emit_confidence(self, score: float, label: str) -> None:
        """Emit a confidence indicator."""
        await self._put(
            SSEEvent(
                event_type=SSEEventType.CONFIDENCE,
                data=ConfidenceEvent(score=score, label=label),
            )
        )

    async def emit_netting_alert(
        self,
        node_id: str,
        node_name: str,
        net_variance: float,
        gross_variance: float,
        netting_ratio: float,
        message: str,
    ) -> None:
        """Emit a netting alert for a summary node."""
        await self._put(
            SSEEvent(
                event_type=SSEEventType.NETTING_ALERT,
                data=NettingAlertEvent(
                    node_id=node_id,
                    node_name=node_name,
                    net_variance=net_variance,
                    gross_variance=gross_variance,
                    netting_ratio=netting_ratio,
                    message=message,
                ),
            )
        )

    async def emit_review_status(
        self, variance_id: str, status: str, message: str
    ) -> None:
        """Emit a review status update."""
        await self._put(
            SSEEvent(
                event_type=SSEEventType.REVIEW_STATUS,
                data=ReviewStatusEvent(
                    variance_id=variance_id, status=status, message=message
                ),
            )
        )

    async def emit_error(self, message: str, code: Optional[str] = None) -> None:
        """Emit an error event."""
        await self._put(
            SSEEvent(
                event_type=SSEEventType.ERROR,
                data=ErrorEvent(message=message, code=code),
            )
        )

    async def emit_done(self, total_tokens: Optional[int] = None) -> None:
        """Emit the done event and close the stream."""
        await self._put(
            SSEEvent(
                event_type=SSEEventType.DONE,
                data=DoneEvent(
                    conversation_id=self.conversation_id,
                    message_id=self.message_id,
                    total_tokens=total_tokens,
                ),
            )
        )
        self._done = True
        # Sentinel: signals the async iterator to stop
        await self._queue.put(None)

    # ------------------------------------------------------------------
    # Async iterator interface (consumed by StreamingResponse)
    # ------------------------------------------------------------------

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[str]:
        """Yield SSE-formatted strings until the done sentinel arrives."""
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield event.to_sse()
