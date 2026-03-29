"""Chat and SSE streaming endpoints.

Handles conversational interactions with the variance-analysis agent.
Messages are sent via POST; responses stream back as Server-Sent Events.
"""

import uuid
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from shared.models.api import ChatMessage, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ConversationSummary(BaseModel):
    """Summary of a stored conversation."""

    conversation_id: str
    title: str
    created_at: str
    message_count: int


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""

    conversations: list[ConversationSummary] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/messages",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a chat message",
)
async def send_message(body: ChatMessage) -> ChatResponse:
    """Accept a user message and return a conversation reference.

    The actual response content is delivered via the SSE stream endpoint.
    """
    conversation_id = body.conversation_id or str(uuid.uuid4())
    # TODO: enqueue message for OrchestratorAgent processing
    return ChatResponse(
        conversation_id=conversation_id,
        stream_url=f"/api/v1/chat/stream/{conversation_id}",
    )


@router.get(
    "/stream/{conversation_id}",
    summary="Stream agent response via SSE",
)
async def stream_response(conversation_id: str) -> StreamingResponse:
    """Server-Sent Events stream for a conversation.

    Typed events: token, data_table, mini_chart, suggestion, confidence,
    netting_alert, review_status, done.
    """

    async def _event_generator() -> Any:
        # TODO: wire to OrchestratorAgent; yield typed SSE events
        yield f"event: token\ndata: Stub response for {conversation_id}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations",
)
async def list_conversations() -> ConversationListResponse:
    """Return paginated list of the current user's conversations."""
    # TODO: query conversation store
    return ConversationListResponse(conversations=[], total=0)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
async def delete_conversation(conversation_id: str) -> None:
    """Soft-delete a conversation by ID."""
    # TODO: mark conversation as deleted in store
    return None
