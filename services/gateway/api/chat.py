"""Chat and SSE streaming endpoints.

Handles conversational interactions with the variance-analysis agent.
Messages are sent via POST; responses stream back as Server-Sent Events.
"""

import asyncio
import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from shared.auth.middleware import UserContext, get_current_user
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
# Agent processing — wired to OrchestratorAgent
# ---------------------------------------------------------------------------
async def _run_agent(
    request: Request,
    ctx: StreamingContext,
    message: str,
    context: dict[str, Any],
) -> None:
    """Run the OrchestratorAgent to process a user message.

    Called as a background task after the POST /messages response is sent.
    The agent emits SSE events directly to the StreamingContext.
    """
    from services.gateway.agents.orchestrator import OrchestratorAgent

    try:
        computation_client = getattr(request.app.state, "computation_client", None)
        review_store = getattr(request.app.state, "review_store", None)
        llm_client = getattr(request.app.state, "llm_client", None)

        if computation_client is None:
            # Fallback: emit error if computation client not configured
            await ctx.emit_token(
                "The computation service is not connected. "
                "Please ensure both services are running."
            )
            await ctx.emit_suggestion(
                ["How did revenue perform?", "Show me the P&L"]
            )
            await ctx.emit_done()
            return

        orchestrator = OrchestratorAgent(
            computation_client=computation_client,
            review_store=review_store,
            llm_client=llm_client,
        )
        try:
            await asyncio.wait_for(
                orchestrator.handle_message(message, context, ctx),
                timeout=60.0,  # 60-second SLA for agent response
            )
        except asyncio.TimeoutError:
            logger.error("Agent timed out after 60s for message: %s", message[:100])
            await ctx.emit_error(
                "The analysis is taking longer than expected. Please try a simpler question.",
                code="AGENT_TIMEOUT",
            )
            await ctx.emit_done()

    except Exception as exc:
        logger.exception("Error in agent processing: %s", exc)
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
    user: UserContext = Depends(get_current_user),
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

    # Launch agent processing via OrchestratorAgent
    background_tasks.add_task(
        _run_agent, request, ctx, body.message, body.context or {},
    )

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
async def list_conversations(
    request: Request,
    user: UserContext = Depends(get_current_user),
) -> ConversationListResponse:
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
    conversation_id: str,
    request: Request,
    user: UserContext = Depends(get_current_user),
) -> None:
    """Soft-delete a conversation by ID."""
    manager: ConversationManager = request.app.state.conversation_manager
    if not manager.delete_conversation(conversation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return None
