"""Audit logging helpers.

Every engine run, LLM call, review action, and data access is logged
to the audit_log table. This module provides convenience functions.
"""

from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from shared.models.facts import AuditLog


def create_audit_entry(
    event_type: str,
    service: str,
    action: str,
    details: Optional[dict[str, Any]] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Create an audit log entry.

    Args:
        event_type: e.g. 'engine_run', 'llm_call', 'review_action', 'data_access'
        service: 'gateway', 'computation', or 'reports'
        action: Specific action description
        details: Additional event payload
        user_id: User performing the action
        ip_address: Request IP

    Returns:
        AuditLog instance ready to persist.
    """
    return AuditLog(
        audit_id=str(uuid4()),
        event_type=event_type,
        service=service,
        action=action,
        details=details or {},
        user_id=user_id,
        ip_address=ip_address,
        timestamp=datetime.now(UTC),
    )
