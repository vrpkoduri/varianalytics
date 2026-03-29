"""Conversation and streaming session manager.

Tracks active conversations and their streaming contexts in memory.
Thread-safe via asyncio — all operations are sync dict ops called from
the single event loop.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from services.gateway.streaming.context import StreamingContext

logger = logging.getLogger("gateway.streaming.manager")


class ConversationManager:
    """Manages active conversations and their streaming contexts.

    In-memory for MVP. Production will back this with Redis / a database.
    """

    def __init__(self) -> None:
        self._active_streams: dict[str, StreamingContext] = {}
        self._conversations: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Conversation lifecycle
    # ------------------------------------------------------------------

    def create_conversation(
        self, user_id: str, title: Optional[str] = None
    ) -> str:
        """Create a new conversation and return its ID."""
        conversation_id = str(uuid.uuid4())
        self._conversations[conversation_id] = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": title or "New conversation",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        }
        logger.info("Created conversation %s for user %s", conversation_id, user_id)
        return conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Return conversation metadata, or None if not found."""
        return self._conversations.get(conversation_id)

    def add_message(
        self,
        conversation_id: str,
        message_id: str,
        role: str,
        content: str,
        context: Optional[dict] = None,
    ) -> None:
        """Append a message to the conversation history."""
        conv = self._conversations.get(conversation_id)
        if conv is None:
            logger.warning(
                "add_message: conversation %s not found", conversation_id
            )
            return
        conv["messages"].append(
            {
                "message_id": message_id,
                "role": role,
                "content": content,
                "context": context,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def delete_conversation(self, conversation_id: str) -> bool:
        """Remove a conversation. Returns True if it existed."""
        removed = self._conversations.pop(conversation_id, None)
        self._active_streams.pop(conversation_id, None)
        if removed:
            logger.info("Deleted conversation %s", conversation_id)
        return removed is not None

    def list_conversations(self, user_id: Optional[str] = None) -> list[dict]:
        """List all conversations, optionally filtered by user.

        Returns lightweight summaries (no full message history).
        """
        results = []
        for conv in self._conversations.values():
            if user_id and conv["user_id"] != user_id:
                continue
            results.append(
                {
                    "conversation_id": conv["conversation_id"],
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "message_count": len(conv["messages"]),
                }
            )
        return results

    # ------------------------------------------------------------------
    # Stream lifecycle
    # ------------------------------------------------------------------

    def create_stream(self, conversation_id: str) -> StreamingContext:
        """Create a StreamingContext for a new message in a conversation.

        If there is already an active stream for this conversation it is
        replaced (the old one is effectively abandoned).
        """
        message_id = str(uuid.uuid4())
        ctx = StreamingContext(
            conversation_id=conversation_id, message_id=message_id
        )
        self._active_streams[conversation_id] = ctx
        logger.info(
            "Created stream for conversation %s, message %s",
            conversation_id,
            message_id,
        )
        return ctx

    def get_stream(self, conversation_id: str) -> Optional[StreamingContext]:
        """Get the active stream for a conversation, if any."""
        return self._active_streams.get(conversation_id)

    def remove_stream(self, conversation_id: str) -> None:
        """Clean up stream after completion or client disconnect."""
        removed = self._active_streams.pop(conversation_id, None)
        if removed:
            logger.info("Removed stream for conversation %s", conversation_id)
