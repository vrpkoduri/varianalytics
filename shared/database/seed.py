"""Seed mutable database tables from parquet files on first boot.

Seeds review_status from parquet and creates default auth roles/users.
Only inserts data when the target table is empty, making it safe to call
on every startup.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.database.models import (
    PermissionRecord,
    ReviewStatusRecord,
    RoleRecord,
    UserRecord,
    UserRoleRecord,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System roles definition
# ---------------------------------------------------------------------------

SYSTEM_ROLES: list[dict[str, Any]] = [
    {
        "role_name": "admin",
        "description": "Full system administrator with all permissions",
        "persona_type": "analyst",
        "narrative_level": "detail",
        "is_system": True,
    },
    {
        "role_name": "analyst",
        "description": "Financial analyst with full variance detail access",
        "persona_type": "analyst",
        "narrative_level": "detail",
        "is_system": True,
    },
    {
        "role_name": "bu_leader",
        "description": "Business unit leader with scoped BU access",
        "persona_type": "bu_leader",
        "narrative_level": "midlevel",
        "is_system": True,
    },
    {
        "role_name": "director",
        "description": "Finance director with approval authority",
        "persona_type": "director",
        "narrative_level": "midlevel",
        "is_system": True,
    },
    {
        "role_name": "cfo",
        "description": "Chief Financial Officer — approved summaries only",
        "persona_type": "cfo",
        "narrative_level": "summary",
        "is_system": True,
    },
    {
        "role_name": "hr_finance",
        "description": "HR Finance specialist — headcount domain only",
        "persona_type": "hr_finance",
        "narrative_level": "detail",
        "is_system": True,
    },
    {
        "role_name": "board_viewer",
        "description": "Board member — board and summary narratives only",
        "persona_type": "board_viewer",
        "narrative_level": "board",
        "is_system": True,
    },
]

# Default permissions per role
ROLE_PERMISSIONS: dict[str, list[dict[str, str]]] = {
    "admin": [
        {"resource": "*", "action": "*", "scope_type": "global"},
    ],
    "analyst": [
        {"resource": "dashboard", "action": "read", "scope_type": "global"},
        {"resource": "variances", "action": "read", "scope_type": "global"},
        {"resource": "pl", "action": "read", "scope_type": "global"},
        {"resource": "chat", "action": "use", "scope_type": "global"},
        {"resource": "review", "action": "read", "scope_type": "global"},
        {"resource": "review", "action": "write", "scope_type": "global"},
        {"resource": "reports", "action": "read", "scope_type": "global"},
        {"resource": "reports", "action": "generate", "scope_type": "global"},
    ],
    "bu_leader": [
        {"resource": "dashboard", "action": "read", "scope_type": "bu"},
        {"resource": "variances", "action": "read", "scope_type": "bu"},
        {"resource": "pl", "action": "read", "scope_type": "bu"},
        {"resource": "chat", "action": "use", "scope_type": "bu"},
        {"resource": "reports", "action": "read", "scope_type": "bu"},
    ],
    "director": [
        {"resource": "dashboard", "action": "read", "scope_type": "global"},
        {"resource": "variances", "action": "read", "scope_type": "global"},
        {"resource": "pl", "action": "read", "scope_type": "global"},
        {"resource": "chat", "action": "use", "scope_type": "global"},
        {"resource": "approval", "action": "read", "scope_type": "global"},
        {"resource": "approval", "action": "write", "scope_type": "global"},
        {"resource": "reports", "action": "read", "scope_type": "global"},
        {"resource": "reports", "action": "generate", "scope_type": "global"},
    ],
    "cfo": [
        {"resource": "dashboard", "action": "read", "scope_type": "global"},
        {"resource": "variances", "action": "read", "scope_type": "global"},
        {"resource": "pl", "action": "read", "scope_type": "global"},
        {"resource": "chat", "action": "use", "scope_type": "global"},
        {"resource": "approval", "action": "read", "scope_type": "global"},
        {"resource": "approval", "action": "write", "scope_type": "global"},
        {"resource": "reports", "action": "read", "scope_type": "global"},
    ],
    "hr_finance": [
        {"resource": "dashboard", "action": "read", "scope_type": "domain"},
        {"resource": "variances", "action": "read", "scope_type": "domain"},
        {"resource": "pl", "action": "read", "scope_type": "domain"},
        {"resource": "chat", "action": "use", "scope_type": "domain"},
        {"resource": "review", "action": "read", "scope_type": "domain"},
        {"resource": "review", "action": "write", "scope_type": "domain"},
    ],
    "board_viewer": [
        {"resource": "dashboard", "action": "read", "scope_type": "global"},
        {"resource": "reports", "action": "read", "scope_type": "global"},
    ],
}

# Demo users for development (password: "password123" for all)
DEMO_USERS: list[dict[str, Any]] = [
    {
        "user_id": "admin-001",
        "email": "admin@variance-agent.dev",
        "display_name": "System Admin",
        "password": "password123",
        "roles": [{"role_name": "admin", "bu_scope": ["ALL"]}],
    },
    {
        "user_id": "analyst-001",
        "email": "analyst@variance-agent.dev",
        "display_name": "Sarah Chen",
        "password": "password123",
        "roles": [{"role_name": "analyst", "bu_scope": ["ALL"]}],
    },
    {
        "user_id": "bu-leader-001",
        "email": "bu.leader@variance-agent.dev",
        "display_name": "James Morrison",
        "password": "password123",
        "roles": [{"role_name": "bu_leader", "bu_scope": ["marsh"]}],
    },
    {
        "user_id": "director-001",
        "email": "director@variance-agent.dev",
        "display_name": "Patricia Williams",
        "password": "password123",
        "roles": [{"role_name": "director", "bu_scope": ["ALL"]}],
    },
    {
        "user_id": "cfo-001",
        "email": "cfo@variance-agent.dev",
        "display_name": "Michael Roberts",
        "password": "password123",
        "roles": [{"role_name": "cfo", "bu_scope": ["ALL"]}],
    },
    {
        "user_id": "board-001",
        "email": "board@variance-agent.dev",
        "display_name": "Elizabeth Taylor",
        "password": "password123",
        "roles": [{"role_name": "board_viewer", "bu_scope": ["ALL"]}],
    },
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

async def seed_roles_and_permissions(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Seed system roles and their default permissions.

    Only inserts when the roles table is empty.

    Returns:
        Number of roles seeded.
    """
    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(RoleRecord))
        if count and count > 0:
            logger.info("Roles table already has %d rows — skipping seed.", count)
            return 0

    async with session_factory() as session:
        async with session.begin():
            for role_def in SYSTEM_ROLES:
                role = RoleRecord(**role_def)
                session.add(role)

            # Flush to get role IDs
            await session.flush()

            # Add permissions
            for role_def in SYSTEM_ROLES:
                role = await session.scalar(
                    select(RoleRecord).where(RoleRecord.role_name == role_def["role_name"])
                )
                if not role:
                    continue

                perms = ROLE_PERMISSIONS.get(role_def["role_name"], [])
                for perm_def in perms:
                    perm = PermissionRecord(
                        role_id=role.id,
                        resource=perm_def["resource"],
                        action=perm_def["action"],
                        scope_type=perm_def["scope_type"],
                    )
                    session.add(perm)

    logger.info("Seeded %d system roles with permissions.", len(SYSTEM_ROLES))
    return len(SYSTEM_ROLES)


async def seed_demo_users(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Seed demo users for development.

    Only inserts when the users table is empty.

    Returns:
        Number of users seeded.
    """
    import hashlib
    import hmac

    def _hash(pw: str) -> str:
        return hmac.new(
            b"variance-agent-salt", pw.encode(), hashlib.sha256
        ).hexdigest()

    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(UserRecord))
        if count and count > 0:
            logger.info("Users table already has %d rows — skipping seed.", count)
            return 0

    async with session_factory() as session:
        async with session.begin():
            for user_def in DEMO_USERS:
                user = UserRecord(
                    user_id=user_def["user_id"],
                    email=user_def["email"],
                    display_name=user_def["display_name"],
                    password_hash=_hash(user_def["password"]),
                    is_active=True,
                )
                session.add(user)

            await session.flush()

            # Assign roles
            for user_def in DEMO_USERS:
                for role_assign in user_def["roles"]:
                    role = await session.scalar(
                        select(RoleRecord).where(
                            RoleRecord.role_name == role_assign["role_name"]
                        )
                    )
                    if role:
                        ur = UserRoleRecord(
                            user_id=user_def["user_id"],
                            role_id=role.id,
                            bu_scope=role_assign.get("bu_scope", ["ALL"]),
                            assigned_by="system",
                        )
                        session.add(ur)

    logger.info("Seeded %d demo users.", len(DEMO_USERS))
    return len(DEMO_USERS)


async def seed_review_status(
    session_factory: async_sessionmaker[AsyncSession],
    data_dir: str = "data/output",
) -> int:
    """Seed the ``review_status`` table from ``fact_review_status.parquet``.

    Only inserts when the table is empty.

    Args:
        session_factory: Async session maker bound to the target database.
        data_dir: Directory containing the parquet output files.

    Returns:
        Number of rows seeded (0 if the table already had data or the file
        was not found).
    """
    parquet_path = Path(data_dir) / "fact_review_status.parquet"

    if not parquet_path.exists():
        logger.warning("Parquet file not found at %s — skipping review_status seed.", parquet_path)
        return 0

    async with session_factory() as session:
        row_count = await session.scalar(select(func.count()).select_from(ReviewStatusRecord))
        if row_count and row_count > 0:
            logger.info("review_status table already has %d rows — skipping seed.", row_count)
            return 0

    # Read parquet — pandas is already a project dependency
    import pandas as pd

    df = pd.read_parquet(parquet_path)
    logger.info("Loaded %d rows from %s", len(df), parquet_path)

    # Map parquet columns to model fields.
    # The parquet schema may use slightly different names; normalise here.
    column_map = {
        "variance_id": "variance_id",
        "status": "status",
        "assigned_analyst": "assigned_analyst",
        "reviewer": "reviewer",
        "approver": "approver",
        "original_narrative": "original_narrative",
        "edited_narrative": "edited_narrative",
        "edit_diff": "edit_diff",
        "hypothesis_feedback": "hypothesis_feedback",
        "review_notes": "review_notes",
        "created_at": "created_at",
        "reviewed_at": "reviewed_at",
        "approved_at": "approved_at",
    }

    records: list[ReviewStatusRecord] = []
    for _, row in df.iterrows():
        kwargs = {}
        for parquet_col, model_field in column_map.items():
            if parquet_col in df.columns:
                value = row[parquet_col]
                # Convert NaN / NaT to None
                if pd.isna(value) if not isinstance(value, dict) else False:
                    value = None
                # Strip timezone info from Timestamps (PostgreSQL DateTime expects naive)
                elif isinstance(value, pd.Timestamp) and value.tzinfo is not None:
                    value = value.tz_localize(None)
                kwargs[model_field] = value
        records.append(ReviewStatusRecord(**kwargs))

    async with session_factory() as session:
        async with session.begin():
            session.add_all(records)

    logger.info("Seeded %d rows into review_status.", len(records))
    return len(records)
