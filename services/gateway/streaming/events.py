"""Typed SSE event models for chat streaming.

Defines Pydantic models for each event type that can be streamed
to the frontend via Server-Sent Events. Event types: token, data_table,
mini_chart, suggestion, confidence, netting_alert, review_status, error, done.
"""

import json
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    """All supported SSE event types."""

    TOKEN = "token"
    DATA_TABLE = "data_table"
    MINI_CHART = "mini_chart"
    SUGGESTION = "suggestion"
    CONFIDENCE = "confidence"
    NETTING_ALERT = "netting_alert"
    REVIEW_STATUS = "review_status"
    ERROR = "error"
    DONE = "done"


# ---------------------------------------------------------------------------
# Individual event payloads
# ---------------------------------------------------------------------------


class TokenEvent(BaseModel):
    """Partial text token for streaming narrative generation."""

    text: str


class DataTableEvent(BaseModel):
    """Structured table data for inline display."""

    title: str
    columns: list[str]
    rows: list[list[Any]]
    footer: Optional[str] = None


class MiniChartEvent(BaseModel):
    """Chart specification for inline visualisation."""

    chart_type: str = Field(description='Chart type: "bar", "line", "waterfall"')
    title: str
    data: list[dict[str, Any]]


class SuggestionEvent(BaseModel):
    """Follow-up question suggestions."""

    suggestions: list[str]


class ConfidenceEvent(BaseModel):
    """Confidence score for the agent's response."""

    score: float = Field(ge=0.0, le=1.0)
    label: str = Field(description='"high", "medium", or "low"')


class NettingAlertEvent(BaseModel):
    """Alert when variances net out below threshold at a summary node."""

    node_id: str
    node_name: str
    net_variance: float
    gross_variance: float
    netting_ratio: float
    message: str


class ReviewStatusEvent(BaseModel):
    """Update on a variance's review workflow status."""

    variance_id: str
    status: str
    message: str


class ErrorEvent(BaseModel):
    """Error event for streaming failures."""

    message: str
    code: Optional[str] = None


class DoneEvent(BaseModel):
    """Marks the end of a streaming response."""

    conversation_id: str
    message_id: str
    total_tokens: Optional[int] = None


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------


class SSEEvent(BaseModel):
    """Wrapper for any SSE event — handles wire-format serialisation."""

    event_type: SSEEventType
    data: Any  # One of the above event types

    def to_sse(self) -> str:
        """Format as SSE wire format: ``event: {type}\\ndata: {json}\\n\\n``."""
        if isinstance(self.data, BaseModel):
            payload = self.data.model_dump_json()
        else:
            payload = json.dumps(self.data)
        return f"event: {self.event_type.value}\ndata: {payload}\n\n"
