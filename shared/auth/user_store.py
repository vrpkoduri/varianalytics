"""User and role CRUD operations backed by PostgreSQL.

Provides async methods for user management, role assignment,
and permission queries. Used by auth endpoints and admin API.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.database.models import (
    PermissionRecord,
    RoleRecord,
    UserRecord,
    UserRoleRecord,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Password hashing (simple HMAC-based for dev; swap to bcrypt in prod)
# ---------------------------------------------------------------------------

import hashlib
import hmac


def _hash_password(password: str, secret: str = "variance-agent-salt") -> str:
    """Hash a password using HMAC-SHA256. Simple but secure for dev mode."""
    return hmac.new(
        secret.encode(), password.encode(), hashlib.sha256
    ).hexdigest()


def _verify_password(password: str, password_hash: str, secret: str = "variance-agent-salt") -> bool:
    """Verify a password against its hash."""
    return hmac.compare_digest(
        _hash_password(password, secret),
        password_hash,
    )


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------

class UserDTO:
    """Lightweight user representation returned by UserStore methods."""

    def __init__(
        self,
        user_id: str,
        email: str,
        display_name: str,
        is_active: bool = True,
        roles: Optional[list[dict[str, Any]]] = None,
        bu_scope: Optional[list[str]] = None,
        persona: str = "analyst",
        created_at: Optional[datetime] = None,
    ) -> None:
        self.user_id = user_id
        self.email = email
        self.display_name = display_name
        self.is_active = is_active
        self.roles = roles or []
        self.bu_scope = bu_scope or ["ALL"]
        self.persona = persona
        self.created_at = created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "roles": self.roles,
            "bu_scope": self.bu_scope,
            "persona": self.persona,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def role_names(self) -> list[str]:
        return [r["role_name"] for r in self.roles if "role_name" in r]


# ---------------------------------------------------------------------------
# UserStore
# ---------------------------------------------------------------------------

class UserStore:
    """Async user and role CRUD backed by PostgreSQL.

    Args:
        session_factory: SQLAlchemy async session maker.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    # ----- User CRUD -----

    async def create_user(
        self,
        email: str,
        display_name: str,
        password: Optional[str] = None,
        azure_ad_oid: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> UserDTO:
        """Create a new user.

        Args:
            email: User email (must be unique).
            display_name: Display name.
            password: Plain-text password (hashed before storage). Optional for Azure AD users.
            azure_ad_oid: Azure AD object ID (for SSO users).
            user_id: Explicit user ID. Auto-generated if not provided.

        Returns:
            Created user as UserDTO.

        Raises:
            ValueError: If email already exists.
        """
        uid = user_id or str(uuid4())
        password_hash = _hash_password(password) if password else None

        async with self._sf() as session:
            async with session.begin():
                # Check for existing email
                existing = await session.scalar(
                    select(UserRecord).where(UserRecord.email == email)
                )
                if existing:
                    raise ValueError(f"User with email {email} already exists")

                record = UserRecord(
                    user_id=uid,
                    email=email,
                    display_name=display_name,
                    password_hash=password_hash,
                    azure_ad_oid=azure_ad_oid,
                    is_active=True,
                )
                session.add(record)

        logger.info("Created user: %s (%s)", uid, email)
        return UserDTO(
            user_id=uid,
            email=email,
            display_name=display_name,
            created_at=datetime.now(UTC),
        )

    async def get_user_by_id(self, user_id: str) -> Optional[UserDTO]:
        """Get user by user_id."""
        async with self._sf() as session:
            record = await session.scalar(
                select(UserRecord).where(UserRecord.user_id == user_id)
            )
            if not record:
                return None
            return await self._record_to_dto(session, record)

    async def get_user_by_email(self, email: str) -> Optional[UserDTO]:
        """Get user by email address."""
        async with self._sf() as session:
            record = await session.scalar(
                select(UserRecord).where(UserRecord.email == email)
            )
            if not record:
                return None
            return await self._record_to_dto(session, record)

    async def get_user_by_azure_oid(self, oid: str) -> Optional[UserDTO]:
        """Get user by Azure AD object ID."""
        async with self._sf() as session:
            record = await session.scalar(
                select(UserRecord).where(UserRecord.azure_ad_oid == oid)
            )
            if not record:
                return None
            return await self._record_to_dto(session, record)

    async def verify_password(self, email: str, password: str) -> Optional[UserDTO]:
        """Verify email/password and return user if valid.

        Returns None if credentials are invalid or user is inactive.
        """
        async with self._sf() as session:
            record = await session.scalar(
                select(UserRecord).where(UserRecord.email == email)
            )
            if not record or not record.is_active:
                return None
            if not record.password_hash:
                return None  # Azure AD user — no local password
            if not _verify_password(password, record.password_hash):
                return None
            return await self._record_to_dto(session, record)

    async def update_user(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        password: Optional[str] = None,
    ) -> Optional[UserDTO]:
        """Update user fields. Only provided fields are changed."""
        values: dict[str, Any] = {}
        if display_name is not None:
            values["display_name"] = display_name
        if is_active is not None:
            values["is_active"] = is_active
        if password is not None:
            values["password_hash"] = _hash_password(password)

        if not values:
            return await self.get_user_by_id(user_id)

        async with self._sf() as session:
            async with session.begin():
                await session.execute(
                    update(UserRecord)
                    .where(UserRecord.user_id == user_id)
                    .values(**values)
                )

        return await self.get_user_by_id(user_id)

    async def deactivate_user(self, user_id: str) -> bool:
        """Soft-delete a user by setting is_active=False."""
        async with self._sf() as session:
            async with session.begin():
                result = await session.execute(
                    update(UserRecord)
                    .where(UserRecord.user_id == user_id)
                    .values(is_active=False)
                )
                return result.rowcount > 0  # type: ignore[return-value]

    async def list_users(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserDTO]:
        """List users with pagination."""
        async with self._sf() as session:
            query = select(UserRecord).order_by(UserRecord.display_name)
            if active_only:
                query = query.where(UserRecord.is_active == True)  # noqa: E712
            query = query.limit(limit).offset(offset)
            result = await session.scalars(query)
            records = result.all()
            return [await self._record_to_dto(session, r) for r in records]

    async def count_users(self, active_only: bool = True) -> int:
        """Count total users."""
        async with self._sf() as session:
            query = select(func.count()).select_from(UserRecord)
            if active_only:
                query = query.where(UserRecord.is_active == True)  # noqa: E712
            return await session.scalar(query) or 0

    # ----- Role management -----

    async def assign_role(
        self,
        user_id: str,
        role_name: str,
        bu_scope: Optional[list[str]] = None,
        assigned_by: Optional[str] = None,
    ) -> bool:
        """Assign a role to a user.

        Args:
            user_id: Target user ID.
            role_name: Role name to assign.
            bu_scope: BU scope for this role assignment.
            assigned_by: User ID of the assigner.

        Returns:
            True if assigned, False if role not found or already assigned.
        """
        async with self._sf() as session:
            async with session.begin():
                role = await session.scalar(
                    select(RoleRecord).where(RoleRecord.role_name == role_name)
                )
                if not role:
                    logger.warning("Role not found: %s", role_name)
                    return False

                # Check if already assigned
                existing = await session.scalar(
                    select(UserRoleRecord).where(
                        UserRoleRecord.user_id == user_id,
                        UserRoleRecord.role_id == role.id,
                    )
                )
                if existing:
                    logger.info("Role %s already assigned to user %s", role_name, user_id)
                    return False

                record = UserRoleRecord(
                    user_id=user_id,
                    role_id=role.id,
                    bu_scope=bu_scope or ["ALL"],
                    assigned_by=assigned_by,
                )
                session.add(record)

        logger.info("Assigned role %s to user %s", role_name, user_id)
        return True

    async def remove_role(self, user_id: str, role_name: str) -> bool:
        """Remove a role from a user."""
        async with self._sf() as session:
            async with session.begin():
                role = await session.scalar(
                    select(RoleRecord).where(RoleRecord.role_name == role_name)
                )
                if not role:
                    return False

                result = await session.execute(
                    delete(UserRoleRecord).where(
                        UserRoleRecord.user_id == user_id,
                        UserRoleRecord.role_id == role.id,
                    )
                )
                return result.rowcount > 0  # type: ignore[return-value]

    async def get_user_roles(self, user_id: str) -> list[dict[str, Any]]:
        """Get all roles assigned to a user with their BU scopes."""
        async with self._sf() as session:
            result = await session.scalars(
                select(UserRoleRecord).where(UserRoleRecord.user_id == user_id)
            )
            user_roles = result.all()

            roles = []
            for ur in user_roles:
                role = await session.get(RoleRecord, ur.role_id)
                if role:
                    roles.append({
                        "role_name": role.role_name,
                        "persona_type": role.persona_type,
                        "narrative_level": role.narrative_level,
                        "bu_scope": ur.bu_scope or ["ALL"],
                        "assigned_at": ur.assigned_at.isoformat() if ur.assigned_at else None,
                    })
            return roles

    async def get_user_bu_scope(self, user_id: str) -> list[str]:
        """Get the merged BU scope across all user roles."""
        roles = await self.get_user_roles(user_id)
        all_scopes: set[str] = set()
        for r in roles:
            scope = r.get("bu_scope", ["ALL"])
            if "ALL" in scope:
                return ["ALL"]
            all_scopes.update(scope)
        return sorted(all_scopes) if all_scopes else ["ALL"]

    # ----- Role CRUD -----

    async def list_roles(self) -> list[dict[str, Any]]:
        """List all roles."""
        async with self._sf() as session:
            result = await session.scalars(
                select(RoleRecord).order_by(RoleRecord.role_name)
            )
            return [
                {
                    "id": r.id,
                    "role_name": r.role_name,
                    "description": r.description,
                    "persona_type": r.persona_type,
                    "narrative_level": r.narrative_level,
                    "is_system": r.is_system,
                }
                for r in result.all()
            ]

    async def get_role(self, role_name: str) -> Optional[dict[str, Any]]:
        """Get a role by name."""
        async with self._sf() as session:
            role = await session.scalar(
                select(RoleRecord).where(RoleRecord.role_name == role_name)
            )
            if not role:
                return None
            return {
                "id": role.id,
                "role_name": role.role_name,
                "description": role.description,
                "persona_type": role.persona_type,
                "narrative_level": role.narrative_level,
                "is_system": role.is_system,
            }

    # ----- Permission queries -----

    async def get_permissions_for_role(self, role_name: str) -> list[dict[str, Any]]:
        """Get all permissions for a role."""
        async with self._sf() as session:
            role = await session.scalar(
                select(RoleRecord).where(RoleRecord.role_name == role_name)
            )
            if not role:
                return []

            result = await session.scalars(
                select(PermissionRecord).where(PermissionRecord.role_id == role.id)
            )
            return [
                {
                    "resource": p.resource,
                    "action": p.action,
                    "scope_type": p.scope_type,
                }
                for p in result.all()
            ]

    async def check_user_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """Check if a user has a specific permission via any of their roles."""
        async with self._sf() as session:
            # Get user's role IDs
            user_roles = await session.scalars(
                select(UserRoleRecord.role_id).where(UserRoleRecord.user_id == user_id)
            )
            role_ids = list(user_roles.all())

            if not role_ids:
                return False

            # Check for admin role (has all permissions)
            admin_check = await session.scalar(
                select(RoleRecord).where(
                    RoleRecord.id.in_(role_ids),
                    RoleRecord.role_name == "admin",
                )
            )
            if admin_check:
                return True

            # Check specific permission
            perm = await session.scalar(
                select(PermissionRecord).where(
                    PermissionRecord.role_id.in_(role_ids),
                    PermissionRecord.resource == resource,
                    PermissionRecord.action == action,
                )
            )
            return perm is not None

    # ----- Upsert for Azure AD -----

    async def upsert_azure_ad_user(
        self,
        oid: str,
        email: str,
        display_name: str,
    ) -> UserDTO:
        """Create or update a user from Azure AD sign-in.

        If user exists (by oid or email), update display name.
        If new, create with default analyst role.
        """
        existing = await self.get_user_by_azure_oid(oid)
        if existing:
            if existing.display_name != display_name:
                await self.update_user(existing.user_id, display_name=display_name)
            return await self.get_user_by_id(existing.user_id) or existing

        # Check by email (user might exist from local auth)
        existing_by_email = await self.get_user_by_email(email)
        if existing_by_email:
            async with self._sf() as session:
                async with session.begin():
                    await session.execute(
                        update(UserRecord)
                        .where(UserRecord.user_id == existing_by_email.user_id)
                        .values(azure_ad_oid=oid, display_name=display_name)
                    )
            return await self.get_user_by_id(existing_by_email.user_id) or existing_by_email

        # Create new user
        user = await self.create_user(
            email=email,
            display_name=display_name,
            azure_ad_oid=oid,
        )

        # Assign default analyst role
        await self.assign_role(user.user_id, "analyst")

        return await self.get_user_by_id(user.user_id) or user

    # ----- Private helpers -----

    async def _record_to_dto(
        self,
        session: AsyncSession,
        record: UserRecord,
    ) -> UserDTO:
        """Convert a UserRecord + its roles to a UserDTO."""
        roles_result = await session.scalars(
            select(UserRoleRecord).where(UserRoleRecord.user_id == record.user_id)
        )
        user_roles = roles_result.all()

        roles: list[dict[str, Any]] = []
        bu_scopes: set[str] = set()
        primary_persona = "analyst"

        for ur in user_roles:
            role = await session.get(RoleRecord, ur.role_id)
            if role:
                roles.append({
                    "role_name": role.role_name,
                    "persona_type": role.persona_type,
                    "narrative_level": role.narrative_level,
                    "bu_scope": ur.bu_scope or ["ALL"],
                })
                scope = ur.bu_scope or ["ALL"]
                if "ALL" in scope:
                    bu_scopes = {"ALL"}
                else:
                    bu_scopes.update(scope)

                if role.persona_type:
                    primary_persona = role.persona_type

        return UserDTO(
            user_id=record.user_id,
            email=record.email,
            display_name=record.display_name,
            is_active=record.is_active,
            roles=roles,
            bu_scope=sorted(bu_scopes) if bu_scopes else ["ALL"],
            persona=primary_persona,
            created_at=record.created_at,
        )
