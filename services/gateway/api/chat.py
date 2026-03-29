"""Chat and SSE streaming endpoints.

Handles conversational interactions with the variance-analysis agent.
Messages are sent via POST; responses stream back as Server-Sent Events.
"""

import asyncio
import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from shared.models.api import ChatMessage, ChatResponse
from services.gateway.streaming import ConversationManager, StreamingContext

logger = logging.getLogger("gateway.chat")

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


class SendMessageResponse(BaseModel):
    """Response from POST /messages — includes IDs needed to connect to stream."""

    conversation_id: str
    message_id: str
    stream_url: str


# ---------------------------------------------------------------------------
# Placeholder agent processing (Sprint 0 — agent not wired yet)
# ---------------------------------------------------------------------------
async def _placeholder_agent_response(ctx: StreamingContext) -> None:
    """Emit placeholder SSE events until the real orchestrator is connected.

    This will be replaced by the OrchestratorAgent in Sprint 1 (SD-6).
    """
    try:
        await ctx.emit_token("I received your message. ")
        await asyncio.sleep(0.05)  # Simulate latency
        await ctx.emit_token("The agent system is being connected. ")
        await asyncio.sleep(0.05)
        await ctx.emit_suggestion(
            ["How did revenue perform?", "Show me the P&L"]
        )
        await ctx.emit_done()
    except Exception as exc:
        logger.exception("Error in placeholder agent response")
        await ctx.emit_error(str(exc), code="AGENT_ERROR")
        await ctx.emit_done()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a chat message",
)
async def send_message(
    body: ChatMessage,
    request: Request,
    background_tasks: BackgroundTasks,
) -> SendMessageResponse:
    """Accept a user message and return a conversation reference.

    The actual response content is delivered via the SSE stream endpoint.

    1. Get or create a conversation.
    2. Create a StreamingContext for this message.
    3. Store the user message.
    4. Launch agent processing as a background task.
    5. Return conversation_id + message_id + stream_url.
    """
    manager: ConversationManager = request.app.state.conversation_manager

    # Get or create conversation
    conversation_id = body.conversation_id
    if conversation_id and manager.get_conversation(conversation_id):
        pass  # Existing conversation
    else:
        # TODO: extract user_id from auth token
        conversation_id = manager.create_conversation(
            user_id="anonymous", title=body.message[:80]
        )

    # Create streaming context
    ctx = manager.create_stream(conversation_id)

    # Store user message
    manager.add_message(
        conversation_id=conversation_id,
        message_id=str(uuid.uuid4()),
        role="user",
        content=body.message,
        context=body.context,
    )

    # Launch agent processing (placeholder for Sprint 0)
    background_tasks.add_task(_placeholder_agent_response, ctx)

    return SendMessageResponse(
        conversation_id=conversation_id,
        message_id=ctx.message_id,
        stream_url=f"/api/v1/chat/stream/{conversation_id}",
    )


@router.get(
    "/stream/{conversation_id}",
    summary="Stream agent response via SSE",
)
async def stream_response(
    conversation_id: str,
    request: Request,
) -> StreamingResponse:
    """Server-Sent Events stream for a conversation.

    Typed events: token, data_table, mini_chart, suggestion, confidence,
    netting_alert, review_status, error, done.
    """
    manager: ConversationManager = request.app.state.conversation_manager
    ctx = manager.get_stream(conversation_id)

    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active stream for conversation {conversation_id}",
        )

    async def _generate():
        try:
            async for chunk in ctx:
                yield chunk
        finally:
            manager.remove_stream(conversation_id)

    return StreamingResponse(
        _generate(),
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
async def list_conversations(request: Request) -> ConversationListResponse:
    """Return list of the current user's conversations."""
    manager: ConversationManager = request.app.state.conversation_manager
    # TODO: extract user_id from auth token
    conversations = manager.list_conversations()
    return ConversationListResponse(
        conversations=[ConversationSummary(**c) for c in conversations],
        total=len(conversations),
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: str, request: Request
) -> None:
    """Soft-delete a conversation by ID."""
    manager: ConversationManager = request.app.state.conversation_manager
    if not manager.delete_conversation(conversation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return None
