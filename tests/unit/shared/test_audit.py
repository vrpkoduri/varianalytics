"""Unit tests for shared.utils.audit — audit log entry creation."""

import pytest

from shared.utils.audit import create_audit_entry


@pytest.mark.unit
class TestCreateAuditEntry:
    """Tests for audit log entry creation."""

    def test_creates_entry_with_required_fields(self) -> None:
        entry = create_audit_entry(
            event_type="engine_run",
            service="computation",
            action="pass1_variance",
        )
        assert entry.event_type == "engine_run"
        assert entry.service == "computation"
        assert entry.action == "pass1_variance"
        assert entry.audit_id  # non-empty UUID
        assert entry.timestamp is not None

    def test_unique_audit_ids(self) -> None:
        e1 = create_audit_entry(event_type="test", service="gateway", action="test")
        e2 = create_audit_entry(event_type="test", service="gateway", action="test")
        assert e1.audit_id != e2.audit_id

    def test_optional_user_and_ip(self) -> None:
        entry = create_audit_entry(
            event_type="review_action",
            service="gateway",
            action="approve",
            user_id="analyst@company.com",
            ip_address="10.0.0.1",
        )
        assert entry.user_id == "analyst@company.com"
        assert entry.ip_address == "10.0.0.1"

    def test_details_payload(self) -> None:
        details = {"model": "gpt-4o", "tokens": 500, "latency_ms": 1200}
        entry = create_audit_entry(
            event_type="llm_call",
            service="computation",
            action="narrative_generation",
            details=details,
        )
        assert entry.details == details

    def test_empty_details_default(self) -> None:
        entry = create_audit_entry(
            event_type="data_access",
            service="computation",
            action="load_table",
        )
        assert entry.details == {}

    def test_none_optional_fields(self) -> None:
        entry = create_audit_entry(
            event_type="engine_run",
            service="computation",
            action="full_pipeline",
        )
        assert entry.user_id is None
        assert entry.ip_address is None
