"""SQLAlchemy ORM models for mutable workflow tables.

These tables hold review/approval state, conversations, and audit logs.
Computed analytical data (variances, decomposition, etc.) lives in parquet files.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    type_annotation_map = {
        dict[str, Any]: JSON,
    }


# ---------------------------------------------------------------------------
# Review / Approval Workflow
# ---------------------------------------------------------------------------

class ReviewStatusRecord(Base):
    """Tracks AI-generated narratives through the review/approval workflow.

    Status lifecycle: AI_DRAFT -> ANALYST_REVIEWED -> APPROVED
    (also: ESCALATED, DISMISSED, AUTO_CLOSED)
    """

    __tablename__ = "review_status"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    variance_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="AI_DRAFT")
    assigned_analyst: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approver: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    original_narrative: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edited_narrative: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edit_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hypothesis_feedback: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ReviewStatusRecord(variance_id={self.variance_id!r}, status={self.status!r})>"


# ---------------------------------------------------------------------------
# Knowledge Commentary (approved narratives for RAG retrieval)
# ---------------------------------------------------------------------------

class KnowledgeCommentaryRecord(Base):
    """Approved commentaries stored for RAG retrieval."""

    __tablename__ = "knowledge_commentary"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    variance_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    narrative_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    narrative_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    account_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    period_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bu_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    variance_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    variance_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    context_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    embedding_stored: Mapped[bool] = mapped_column(default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<KnowledgeCommentaryRecord(variance_id={self.variance_id!r})>"


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

class ConversationRecord(Base):
    """A chat conversation belonging to a user."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ConversationRecord(id={self.conversation_id!r}, user={self.user_id!r})>"


# ---------------------------------------------------------------------------
# Chat Messages
# ---------------------------------------------------------------------------

class ChatMessageRecord(Base):
    """A single message within a conversation."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_chat_messages_conv_created", "conversation_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ChatMessageRecord(conversation={self.conversation_id!r}, role={self.role!r})>"


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class AuditLogRecord(Base):
    """Immutable audit trail for engine runs, LLM calls, reviews, and data access."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    service: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_log_user_ts", "user_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditLogRecord(audit_id={self.audit_id!r}, event={self.event_type!r})>"
