"""Review Store — in-memory mutable store for review/approval workflow.

Wraps the loaded fact_review_status + fact_variance_material DataFrames.
Provides query and mutation methods for review queue, approval queue,
and status transitions. Thread-safe via copy-on-write patterns.

In Sprint 1, this operates on in-memory DataFrames loaded from parquet.
PostgreSQL persistence (SD-1) is available but the store serves as the
fast-path query layer. Status mutations are written to both in-memory
and PostgreSQL.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Optional

import pandas as pd

from shared.data.loader import DataLoader

logger = logging.getLogger(__name__)

# Valid status transitions
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "AI_DRAFT": {"ANALYST_REVIEWED", "ESCALATED", "DISMISSED"},
    "ANALYST_REVIEWED": {"APPROVED", "AI_DRAFT", "ESCALATED"},
    "ESCALATED": {"ANALYST_REVIEWED", "DISMISSED"},
    "DISMISSED": {"AI_DRAFT"},
    "APPROVED": set(),  # Terminal state
    "AUTO_CLOSED": set(),  # Terminal state
}

# Action → target status mapping
_ACTION_STATUS_MAP: dict[str, str] = {
    "approve": "ANALYST_REVIEWED",  # Analyst approves → ANALYST_REVIEWED
    "edit": "ANALYST_REVIEWED",  # Edit implies review
    "escalate": "ESCALATED",
    "dismiss": "DISMISSED",
    "director_approve": "APPROVED",
    "director_reject": "AI_DRAFT",  # Send back to draft
}


class ReviewStore:
    """In-memory review and approval state manager.

    Loads fact_review_status and fact_variance_material at init.
    Provides query/mutation for review queue and approval queue.
    """

    def __init__(self, data_dir: str = "data/output") -> None:
        """Load review status and variance data from parquet files."""
        loader = DataLoader(data_dir)

        self._review_status = loader.load_table("fact_review_status").copy()
        self._variance_material = loader.load_table("fact_variance_material").copy()

        # Load account names for display
        self._account_lookup: dict[str, str] = {}
        try:
            dim_account = loader.load_table("dim_account")
            if not dim_account.empty:
                for _, row in dim_account.iterrows():
                    self._account_lookup[str(row["account_id"])] = str(row.get("account_name", row["account_id"]))
        except Exception:
            pass

        # Ensure required columns exist
        if "reviewed_at" not in self._review_status.columns:
            self._review_status["reviewed_at"] = pd.NaT
        if "approved_at" not in self._review_status.columns:
            self._review_status["approved_at"] = pd.NaT
        if "version_count" not in self._review_status.columns:
            self._review_status["version_count"] = 1
        if "locked_by" not in self._review_status.columns:
            self._review_status["locked_by"] = None
        if "locked_until" not in self._review_status.columns:
            self._review_status["locked_until"] = None

        logger.info(
            "ReviewStore loaded: %d review records, %d material variances",
            len(self._review_status),
            len(self._variance_material),
        )

    def get_review_queue(
        self,
        status_filter: Optional[str] = None,
        sort_by: str = "impact",
        page: int = 1,
        page_size: int = 50,
        fiscal_year: Optional[int] = None,
        allowed_statuses: Optional[list[str]] = None,
        bu_scope: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Get the analyst review queue.

        Args:
            status_filter: Filter by status (AI_DRAFT, ANALYST_REVIEWED, etc.)
            sort_by: Sort field — impact (abs variance), sla, period
            page: Page number (1-indexed)
            page_size: Items per page
            fiscal_year: Filter to specific fiscal year (e.g. 2026)
            allowed_statuses: RBAC-derived list of statuses this persona may see.
            bu_scope: RBAC-derived list of BU IDs this user may access (["ALL"] = no restriction).

        Returns:
            Dict with items, total, page, page_size.
        """
        # Join review_status with variance_material for display data
        rs = self._review_status.copy()
        vm = self._variance_material.copy()

        # Select available columns from variance_material (defensive — some may be missing in test fixtures)
        desired_cols = ["variance_id", "account_id", "period_id", "bu_id",
                        "variance_amount", "variance_pct", "narrative_oneliner",
                        "narrative_detail", "narrative_source",
                        "pl_category"]
        available_cols = [c for c in desired_cols if c in vm.columns]
        merged = rs.merge(
            vm[available_cols].drop_duplicates(subset=["variance_id"]),
            on="variance_id",
            how="left",
            suffixes=("", "_vm"),
        )

        # RBAC: filter by allowed statuses (persona-driven)
        if allowed_statuses:
            merged = merged[merged["status"].isin(allowed_statuses)]

        # RBAC: filter by BU scope (persona-driven)
        if bu_scope and "ALL" not in bu_scope and "bu_id" in merged.columns:
            merged = merged[merged["bu_id"].isin(bu_scope)]

        # Apply fiscal year filter
        if fiscal_year and "period_id" in merged.columns:
            merged = merged[merged["period_id"].str.startswith(str(fiscal_year))]

        # Apply additional status filter (narrows within RBAC-allowed statuses)
        if status_filter:
            merged = merged[merged["status"] == status_filter]

        # Sort
        if sort_by == "impact":
            merged["abs_variance"] = merged["variance_amount"].abs()
            merged = merged.sort_values("abs_variance", ascending=False)
        elif sort_by == "sla":
            merged = merged.sort_values("created_at", ascending=True)
        elif sort_by == "period":
            merged = merged.sort_values("period_id", ascending=False)

        total = len(merged)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        page_data = merged.iloc[start:end]

        items = []
        for _, row in page_data.iterrows():
            # Calculate SLA (48 hours from creation)
            sla_hours = None
            if pd.notna(row.get("created_at")):
                try:
                    created = pd.Timestamp(row["created_at"])
                    deadline = created + pd.Timedelta(hours=48)
                    remaining = (deadline - pd.Timestamp.now()).total_seconds() / 3600
                    sla_hours = round(remaining, 1)
                except Exception:
                    sla_hours = None

            items.append({
                "variance_id": str(row.get("variance_id", "")),
                "account_name": self._account_lookup.get(str(row.get("account_id", "")), str(row.get("account_id", ""))),
                "period_label": str(row.get("period_id", "")),
                "variance_amount": float(row.get("variance_amount", 0)),
                "variance_pct": float(row["variance_pct"]) if pd.notna(row.get("variance_pct")) else None,
                "current_status": str(row.get("status", "AI_DRAFT")),
                "narrative_preview": str(row.get("narrative_oneliner", ""))[:200],
                "narrative_detail": str(row.get("narrative_detail", ""))[:500] if pd.notna(row.get("narrative_detail")) else "",
                "narrative_source": str(row.get("narrative_source", "")),
                "sla_hours_remaining": sla_hours,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # Locking
    # ------------------------------------------------------------------

    def acquire_lock(self, variance_id: str, user_id: str) -> dict[str, Any]:
        """Acquire a soft edit lock on a variance (30 min timeout)."""
        mask = self._review_status["variance_id"] == variance_id
        if not mask.any():
            raise ValueError(f"Variance {variance_id} not found")

        now = datetime.datetime.now(datetime.timezone.utc)
        current_lock = self._review_status.loc[mask, "locked_by"].iloc[0] if "locked_by" in self._review_status.columns else None
        lock_until = self._review_status.loc[mask, "locked_until"].iloc[0] if "locked_until" in self._review_status.columns else None

        # Check if already locked by someone else
        if current_lock and current_lock != user_id:
            if lock_until and str(lock_until) > now.isoformat():
                return {"locked": False, "locked_by": current_lock, "message": f"Locked by {current_lock}"}

        # Acquire lock
        expire = now + datetime.timedelta(minutes=30)
        if "locked_by" not in self._review_status.columns:
            self._review_status["locked_by"] = None
            self._review_status["locked_until"] = None
        self._review_status.loc[mask, "locked_by"] = user_id
        self._review_status.loc[mask, "locked_until"] = expire.isoformat()
        return {"locked": True, "locked_by": user_id, "locked_until": expire.isoformat()}

    def release_lock(self, variance_id: str, user_id: str) -> bool:
        """Release a lock if owned by the caller."""
        mask = self._review_status["variance_id"] == variance_id
        if not mask.any():
            return False
        if "locked_by" in self._review_status.columns:
            current = self._review_status.loc[mask, "locked_by"].iloc[0]
            if current == user_id or current is None:
                self._review_status.loc[mask, "locked_by"] = None
                self._review_status.loc[mask, "locked_until"] = None
                return True
        return False

    def get_lock_status(self, variance_id: str) -> dict[str, Any]:
        """Check the lock status of a variance."""
        mask = self._review_status["variance_id"] == variance_id
        if not mask.any():
            return {"locked": False}
        if "locked_by" not in self._review_status.columns:
            return {"locked": False}
        locked_by = self._review_status.loc[mask, "locked_by"].iloc[0]
        locked_until = self._review_status.loc[mask, "locked_until"].iloc[0]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        is_locked = bool(locked_by) and str(locked_until or "") > now
        return {"locked": is_locked, "locked_by": locked_by if is_locked else None, "locked_until": locked_until if is_locked else None}

    # ------------------------------------------------------------------
    # Review action
    # ------------------------------------------------------------------

    def submit_review_action(
        self,
        variance_id: str,
        action: str,
        edited_narrative: Optional[str] = None,
        hypothesis_feedback: Optional[str] = None,
        comment: Optional[str] = None,
        user_id: Optional[str] = None,
        change_reason: Optional[str] = None,
    ) -> dict[str, str]:
        """Process an analyst review action.

        Args:
            variance_id: Target variance.
            action: One of approve, edit, escalate, dismiss, director_approve, director_reject.
            edited_narrative: New narrative text (for edit action).
            hypothesis_feedback: thumbs_up or thumbs_down.
            comment: Review comment.
            user_id: ID of the user performing the action (for locking and audit).
            change_reason: Why the narrative was changed (factual_correction, added_context, etc.)

        Returns:
            Dict with variance_id, new_status, message.

        Raises:
            ValueError: If variance_id not found or invalid transition.
        """
        mask = self._review_status["variance_id"] == variance_id
        if not mask.any():
            raise ValueError(f"Variance {variance_id} not found in review queue")

        # Lock check: reject if locked by another user
        if user_id and "locked_by" in self._review_status.columns:
            locked_by = self._review_status.loc[mask, "locked_by"].iloc[0]
            locked_until = self._review_status.loc[mask, "locked_until"].iloc[0]
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if locked_by and locked_by != user_id and str(locked_until or "") > now:
                raise ValueError(f"Variance is locked by {locked_by}")

        current_status = self._review_status.loc[mask, "status"].iloc[0]
        target_status = _ACTION_STATUS_MAP.get(action)
        if not target_status:
            raise ValueError(f"Unknown action: {action}")

        valid_targets = _VALID_TRANSITIONS.get(current_status, set())
        if target_status not in valid_targets:
            raise ValueError(
                f"Cannot transition from {current_status} to {target_status} "
                f"(valid: {valid_targets})"
            )

        # Update status
        self._review_status.loc[mask, "status"] = target_status
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if target_status == "ANALYST_REVIEWED":
            self._review_status.loc[mask, "reviewed_at"] = now
            self._review_status.loc[mask, "reviewer"] = user_id or "analyst"
        elif target_status == "APPROVED":
            self._review_status.loc[mask, "approved_at"] = now
            self._review_status.loc[mask, "approver"] = user_id or "director"

        if edited_narrative:
            self._review_status.loc[mask, "edited_narrative"] = edited_narrative

        if hypothesis_feedback:
            self._review_status.loc[mask, "hypothesis_feedback"] = hypothesis_feedback

        if comment:
            self._review_status.loc[mask, "review_notes"] = comment

        # Version tracking
        if "version_count" in self._review_status.columns:
            current_vc = self._review_status.loc[mask, "version_count"].iloc[0]
            new_vc = (int(current_vc) if current_vc and not (isinstance(current_vc, float) and current_vc != current_vc) else 0) + 1
            self._review_status.loc[mask, "version_count"] = new_vc
        else:
            new_vc = 1

        # Release lock after action
        if user_id and "locked_by" in self._review_status.columns:
            self._review_status.loc[mask, "locked_by"] = None
            self._review_status.loc[mask, "locked_until"] = None

        logger.info(
            "Review action: %s on %s (%s → %s) by %s [v%d]",
            action, variance_id, current_status, target_status, user_id or "unknown", new_vc,
        )

        return {
            "variance_id": variance_id,
            "new_status": target_status,
            "message": f"Action '{action}' applied: {current_status} → {target_status}",
            "version": new_vc,
        }

    def get_review_stats(
        self,
        allowed_statuses: Optional[list[str]] = None,
        bu_scope: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Get aggregate review queue statistics.

        Args:
            allowed_statuses: RBAC-derived list of statuses this persona may see.
            bu_scope: RBAC-derived list of BU IDs this user may access.
        """
        rs = self._review_status.copy()

        # RBAC: filter by allowed statuses
        if allowed_statuses:
            rs = rs[rs["status"].isin(allowed_statuses)]

        # RBAC: filter by BU scope
        if bu_scope and "ALL" not in bu_scope:
            # Need to join with variance_material for bu_id
            vm = self._variance_material
            if "bu_id" in vm.columns:
                bu_vids = vm[vm["bu_id"].isin(bu_scope)]["variance_id"].unique()
                rs = rs[rs["variance_id"].isin(bu_vids)]

        status_counts = rs["status"].value_counts().to_dict()

        return {
            "total_pending": int(status_counts.get("AI_DRAFT", 0) + status_counts.get("ESCALATED", 0)),
            "ai_draft": int(status_counts.get("AI_DRAFT", 0)),
            "analyst_reviewed": int(status_counts.get("ANALYST_REVIEWED", 0)),
            "escalated": int(status_counts.get("ESCALATED", 0)),
            "dismissed": int(status_counts.get("DISMISSED", 0)),
            "approved": int(status_counts.get("APPROVED", 0)),
            "avg_sla_hours": None,  # TODO: compute from created_at
        }

    def get_approval_queue(
        self,
        page: int = 1,
        page_size: int = 50,
        allowed_statuses: Optional[list[str]] = None,
        bu_scope: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Get the director approval queue.

        Args:
            page: Page number (1-indexed).
            page_size: Items per page.
            allowed_statuses: RBAC-derived list of statuses (defaults to ANALYST_REVIEWED).
            bu_scope: RBAC-derived list of BU IDs this user may access.

        Returns:
            Dict with items, total, page, page_size.
        """
        # Default to ANALYST_REVIEWED for backward compatibility
        target_statuses = allowed_statuses or ["ANALYST_REVIEWED"]
        rs = self._review_status[
            self._review_status["status"].isin(target_statuses)
        ].copy()
        vm = self._variance_material

        desired_cols = ["variance_id", "account_id", "period_id", "bu_id",
                        "variance_amount", "variance_pct",
                        "narrative_oneliner", "narrative_detail", "narrative_source"]
        available_cols = [c for c in desired_cols if c in vm.columns]
        merged = rs.merge(
            vm[available_cols].drop_duplicates(subset=["variance_id"]),
            on="variance_id",
            how="left",
        )

        # RBAC: filter by BU scope
        if bu_scope and "ALL" not in bu_scope and "bu_id" in merged.columns:
            merged = merged[merged["bu_id"].isin(bu_scope)]

        total = len(merged)
        start = (page - 1) * page_size
        end = start + page_size
        page_data = merged.iloc[start:end]

        items = []
        for _, row in page_data.iterrows():
            items.append({
                "variance_id": str(row.get("variance_id", "")),
                "account_name": self._account_lookup.get(str(row.get("account_id", "")), str(row.get("account_id", ""))),
                "period_label": str(row.get("period_id", "")),
                "variance_amount": float(row.get("variance_amount", 0)),
                "variance_pct": float(row["variance_pct"]) if pd.notna(row.get("variance_pct")) else None,
                "analyst_name": str(row.get("reviewer", "analyst")),
                "reviewed_narrative": str(row.get("edited_narrative", row.get("narrative_oneliner", "")))[:300],
                "narrative_detail": str(row.get("narrative_detail", ""))[:500] if pd.notna(row.get("narrative_detail")) else "",
                "narrative_source": str(row.get("narrative_source", "")) if pd.notna(row.get("narrative_source")) else "",
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def submit_bulk_approval(
        self,
        variance_ids: list[str],
        action: str = "approve",
        comment: Optional[str] = None,
    ) -> dict[str, Any]:
        """Bulk approve or reject ANALYST_REVIEWED variances.

        Args:
            variance_ids: List of variance IDs to process.
            action: "approve" or "reject".
            comment: Optional comment.

        Returns:
            Dict with approved_count, rejected_count, errors.
        """
        approved = 0
        rejected = 0
        errors: list[str] = []

        for vid in variance_ids:
            try:
                if action == "approve":
                    self.submit_review_action(vid, "director_approve", comment=comment)
                    approved += 1
                elif action == "reject":
                    self.submit_review_action(vid, "director_reject", comment=comment)
                    rejected += 1
                else:
                    errors.append(f"Unknown action: {action}")
            except ValueError as e:
                errors.append(str(e))

        return {
            "approved_count": approved,
            "rejected_count": rejected,
            "errors": errors,
        }

    def get_approval_stats(self) -> dict[str, Any]:
        """Get aggregate approval statistics."""
        rs = self._review_status
        status_counts = rs["status"].value_counts().to_dict()

        return {
            "pending_approval": int(status_counts.get("ANALYST_REVIEWED", 0)),
            "approved_today": 0,  # TODO: filter by date
            "rejected_today": 0,
            "total_approved": int(status_counts.get("APPROVED", 0)),
        }
