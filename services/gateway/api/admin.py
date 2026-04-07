"""Admin API endpoints for user/role management and audit log viewing.

All endpoints require admin role. Provides CRUD for users and roles,
and a paginated audit log viewer.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from shared.auth.middleware import UserContext, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserCreateRequest(BaseModel):
    email: str
    display_name: str
    password: str = Field(..., min_length=6)
    role_name: str = "analyst"
    bu_scope: list[str] = Field(default_factory=lambda: ["ALL"])


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class RoleAssignRequest(BaseModel):
    role_name: str
    bu_scope: list[str] = Field(default_factory=lambda: ["ALL"])


class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    is_active: bool = True
    roles: list[dict[str, Any]] = Field(default_factory=list)
    bu_scope: list[str] = Field(default_factory=lambda: ["ALL"])
    persona: str = "analyst"
    created_at: Optional[str] = None


class UserListResponse(BaseModel):
    users: list[UserResponse] = Field(default_factory=list)
    total: int = 0


class RoleResponse(BaseModel):
    id: int
    role_name: str
    description: Optional[str] = None
    persona_type: Optional[str] = None
    narrative_level: Optional[str] = None
    is_system: bool = False


class AuditLogEntry(BaseModel):
    audit_id: str
    event_type: str
    user_id: str
    service: str
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    timestamp: str


class AuditLogResponse(BaseModel):
    entries: list[AuditLogEntry] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users",
)
async def list_users(
    request: Request,
    active_only: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: UserContext = Depends(require_admin()),
) -> UserListResponse:
    """List all users with their roles."""
    store = getattr(request.app.state, "user_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="User store unavailable")

    users = await store.list_users(active_only=active_only, limit=limit, offset=offset)
    total = await store.count_users(active_only=active_only)

    return UserListResponse(
        users=[
            UserResponse(**u.to_dict())
            for u in users
        ],
        total=total,
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    user: UserContext = Depends(require_admin()),
) -> UserResponse:
    """Create a new user and assign initial role."""
    store = getattr(request.app.state, "user_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="User store unavailable")

    try:
        new_user = await store.create_user(
            email=body.email,
            display_name=body.display_name,
            password=body.password,
        )
        await store.assign_role(
            new_user.user_id,
            body.role_name,
            bu_scope=body.bu_scope,
            assigned_by=user.user_id,
        )

        # Refresh to include roles
        refreshed = await store.get_user_by_id(new_user.user_id)
        if refreshed:
            return UserResponse(**refreshed.to_dict())
        return UserResponse(**new_user.to_dict())

    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
)
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    request: Request,
    user: UserContext = Depends(require_admin()),
) -> UserResponse:
    """Update user fields (name, status, password)."""
    store = getattr(request.app.state, "user_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="User store unavailable")

    updated = await store.update_user(
        user_id,
        display_name=body.display_name,
        is_active=body.is_active,
        password=body.password,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**updated.to_dict())


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user",
)
async def deactivate_user(
    user_id: str,
    request: Request,
    user: UserContext = Depends(require_admin()),
) -> None:
    """Soft-delete (deactivate) a user."""
    store = getattr(request.app.state, "user_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="User store unavailable")

    if user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    success = await store.deactivate_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")


# ---------------------------------------------------------------------------
# Role assignment
# ---------------------------------------------------------------------------

@router.post(
    "/users/{user_id}/roles",
    status_code=status.HTTP_200_OK,
    summary="Assign a role to a user",
)
async def assign_role(
    user_id: str,
    body: RoleAssignRequest,
    request: Request,
    user: UserContext = Depends(require_admin()),
) -> dict[str, Any]:
    """Assign a role to a user with BU scope."""
    store = getattr(request.app.state, "user_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="User store unavailable")

    assigned = await store.assign_role(
        user_id,
        body.role_name,
        bu_scope=body.bu_scope,
        assigned_by=user.user_id,
    )
    if not assigned:
        raise HTTPException(
            status_code=400,
            detail="Role not found or already assigned",
        )
    return {"status": "assigned", "role": body.role_name, "user_id": user_id}


@router.delete(
    "/users/{user_id}/roles/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a role from a user",
)
async def remove_role(
    user_id: str,
    role_name: str,
    request: Request,
    user: UserContext = Depends(require_admin()),
) -> None:
    """Remove a role from a user."""
    store = getattr(request.app.state, "user_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="User store unavailable")

    removed = await store.remove_role(user_id, role_name)
    if not removed:
        raise HTTPException(status_code=404, detail="Role assignment not found")


# ---------------------------------------------------------------------------
# Roles listing
# ---------------------------------------------------------------------------

@router.get(
    "/roles",
    response_model=list[RoleResponse],
    summary="List all roles",
)
async def list_roles(
    request: Request,
    user: UserContext = Depends(require_admin()),
) -> list[RoleResponse]:
    """List all system and custom roles."""
    store = getattr(request.app.state, "user_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="User store unavailable")

    roles = await store.list_roles()
    return [RoleResponse(**r) for r in roles]


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

@router.get(
    "/audit-log",
    response_model=AuditLogResponse,
    summary="View audit log",
)
async def get_audit_log(
    request: Request,
    event_type: Optional[str] = Query(None),
    user_filter: Optional[str] = Query(None, alias="user"),
    service: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: UserContext = Depends(require_admin()),
) -> AuditLogResponse:
    """Paginated audit log with optional filters."""
    session_factory = getattr(request.app.state, "_session_factory", None)

    # For now, return empty — audit log queries will be wired when
    # the audit store is enhanced in CP-5
    return AuditLogResponse(entries=[], total=0, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Engine Control — Moved to computation service (Phase 3D)
# ---------------------------------------------------------------------------
# Engine control endpoints are served by the computation service at
# /api/v1/engine/* (port 8001). The frontend calls computation directly
# for engine operations. See services/computation/api/engine_control.py.


# ---------------------------------------------------------------------------
# Hot-Reload (Framework Completion Sprint)
# ---------------------------------------------------------------------------


@router.post(
    "/reload",
    summary="Reload data from disk",
)
async def reload_data(
    request: Request,
    admin: UserContext = Depends(require_admin()),
) -> dict:
    """Force DataService to reload all tables from parquet files.

    Use after running the engine via CLI to refresh in-memory data
    without restarting the service.
    """
    ds = getattr(request.app.state, "data_service", None)
    if ds is None:
        raise HTTPException(status_code=503, detail="DataService not initialized")

    ds._load_all_tables()
    ds._build_account_metadata()
    ds.invalidate_graph_cache()

    # Also reload ReviewStore (it caches its own copy of variance_material)
    review_store = getattr(request.app.state, "review_store", None)
    if review_store:
        try:
            from shared.data.loader import DataLoader
            loader = DataLoader(ds._data_dir if hasattr(ds, '_data_dir') else "data/output")
            if hasattr(review_store, '_store'):
                # AsyncReviewStore wraps a sync ReviewStore
                review_store._store._variance_material = loader.load_table("fact_variance_material").copy()
                review_store._store._review_status = loader.load_table("fact_review_status").copy()
                logger.info("ReviewStore reloaded via AsyncReviewStore wrapper")
            elif hasattr(review_store, '_variance_material'):
                review_store._variance_material = loader.load_table("fact_variance_material").copy()
                review_store._review_status = loader.load_table("fact_review_status").copy()
                logger.info("ReviewStore reloaded directly")
        except Exception as exc:
            logger.warning("ReviewStore reload failed: %s", exc)

    table_counts = {name: len(df) for name, df in ds._tables.items() if not df.empty}
    logger.info("Admin reload: %d tables reloaded", len(table_counts))

    return {
        "status": "reloaded",
        "tables": table_counts,
    }


# ---------------------------------------------------------------------------
# LLM Monitoring (AI Monitoring Dashboard)
# ---------------------------------------------------------------------------


@router.get(
    "/llm-health",
    summary="LLM health status",
)
async def get_llm_health(
    request: Request,
    admin: UserContext = Depends(require_admin()),
) -> dict:
    """Return LLM provider health status, configured models, and endpoint info."""
    health_checker = getattr(request.app.state, "llm_health", None)
    if health_checker is None:
        return {
            "status": "unavailable",
            "provider": "none",
            "endpoint": "",
            "api_key_configured": False,
            "models": [],
        }
    return health_checker.get_health_status()


@router.get(
    "/narrative-quality",
    summary="Narrative quality breakdown",
)
async def get_narrative_quality(
    request: Request,
    admin: UserContext = Depends(require_admin()),
    period_id: str | None = Query(None, description="Filter to a specific period"),
) -> dict:
    """Return LLM vs template narrative breakdown and engine run history."""
    ds = getattr(request.app.state, "data_service", None)
    if ds is None:
        return {"total": 0, "llm_count": 0, "template_count": 0, "llm_pct": 0, "by_level": {}, "engine_runs": []}
    return ds.get_narrative_quality(period_id=period_id)


@router.post(
    "/llm-test",
    summary="Test LLM connectivity",
)
async def test_llm_connectivity(
    request: Request,
    admin: UserContext = Depends(require_admin()),
) -> dict:
    """Send a test prompt to the configured LLM and return response + latency."""
    health_checker = getattr(request.app.state, "llm_health", None)
    if health_checker is None:
        return {
            "success": False,
            "provider": "none",
            "model": "none",
            "response_text": "LLM health checker not initialized",
            "latency_ms": 0,
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
        }
    return await health_checker.test_connectivity()
