"""Variance Agent — Gateway (Service 1, Port 8000).

Entry point for the Gateway microservice. Handles authentication, chat/SSE,
dimension lookups, configuration, review/approval workflows, and notifications.
"""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.gateway.api.admin import router as admin_router
from services.gateway.api.approval import router as approval_router
from services.gateway.api.auth import router as auth_router
from services.gateway.api.chat import router as chat_router
from services.gateway.api.config import router as config_router
from services.gateway.api.dimensions import router as dimensions_router
from services.gateway.api.notifications import router as notifications_router
from services.gateway.api.review import router as review_router
from services.gateway.streaming.manager import ConversationManager
from shared.models.api import HealthResponse

# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("gateway")

# ---------------------------------------------------------------------------
# Application version
# ---------------------------------------------------------------------------
VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Startup:
        - Initialise DataService (parquet data)
        - Initialise ReviewStore (mutable workflow state)
        - Initialise ConversationManager (chat sessions)
    Shutdown:
        - Drain connections
    """
    from shared.data.service import DataService
    from shared.data.review_store import ReviewStore
    from services.gateway.clients.computation_client import ComputationClient
    from shared.config.settings import Settings
    from shared.llm.client import LLMClient

    settings = Settings()

    # Store environment for dev-mode auth fallback
    app.state.environment = settings.environment

    # Database initialization (graceful degradation)
    session_factory = None
    try:
        from shared.database.engine import init_engine, init_db, get_session_factory, dispose_engine
        from shared.database.seed import seed_review_status, seed_roles_and_permissions, seed_demo_users

        init_engine(settings.database_url)
        await init_db()
        session_factory = get_session_factory()

        # Seed auth tables (roles, permissions, demo users)
        roles_seeded = await seed_roles_and_permissions(session_factory)
        if roles_seeded > 0:
            logger.info("Seeded %d system roles with permissions", roles_seeded)
        users_seeded = await seed_demo_users(session_factory)
        if users_seeded > 0:
            logger.info("Seeded %d demo users", users_seeded)

        # Seed review status from parquet (separate try/catch — don't break auth if this fails)
        try:
            seeded = await seed_review_status(session_factory)
            if seeded > 0:
                logger.info("Seeded %d review records from parquet", seeded)
        except Exception as exc:
            logger.warning("Review status seeding failed (non-critical): %s", exc)

        logger.info("Database connected")
    except Exception as exc:
        logger.warning("Database unavailable, using in-memory only: %s", exc)
        session_factory = None

    # JWT Service
    from shared.auth.jwt import JWTService
    app.state.jwt_service = JWTService(
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
        refresh_token_expire_minutes=settings.jwt_refresh_token_expire_minutes,
    )
    logger.info("JWT service initialised (algorithm=%s)", settings.jwt_algorithm)

    # User Store (requires database)
    if session_factory:
        from shared.auth.user_store import UserStore
        app.state.user_store = UserStore(session_factory)
        logger.info("User store initialised (PostgreSQL-backed)")
    else:
        app.state.user_store = None
        logger.warning("User store unavailable — auth endpoints limited to dev mode")

    # Azure AD Provider (optional — only when configured)
    from shared.auth.azure_ad import create_azure_ad_provider
    app.state.azure_ad_provider = create_azure_ad_provider(
        tenant_id=settings.azure_ad_tenant_id,
        client_id=settings.azure_ad_client_id,
        client_secret=settings.azure_ad_client_secret,
    )

    logger.info("Gateway starting up — initialising services …")
    app.state.data_service = DataService()

    # Initialize knowledge store for approval-triggered RAG population
    knowledge_store = None
    try:
        from shared.knowledge.embedding import EmbeddingService
        from shared.knowledge.vector_store import create_vector_store
        from shared.knowledge.knowledge_store import KnowledgeStore

        embedding_svc = EmbeddingService()
        vector_store = create_vector_store(qdrant_url=None)  # InMemory for now
        knowledge_store = KnowledgeStore(embedding_svc, vector_store)
        logger.info("Knowledge store initialised (in-memory vector store)")
    except Exception as exc:
        logger.warning("Knowledge store unavailable: %s", exc)

    from shared.data.async_review_store import AsyncReviewStore
    inner_store = ReviewStore()
    app.state.review_store = AsyncReviewStore(
        inner_store,
        session_factory=session_factory,
        knowledge_store=knowledge_store,
    )

    app.state.conversation_manager = ConversationManager()
    app.state.computation_client = ComputationClient(
        base_url=settings.computation_service_url,
    )
    app.state.llm_client = LLMClient(settings)
    if app.state.llm_client.is_available:
        logger.info("LLM available: provider=%s", app.state.llm_client.provider)
    else:
        logger.info("LLM not available — using keyword intent + template responses")

    # LLM Health Checker (AI Monitoring dashboard)
    from shared.llm.health import LLMHealthChecker
    app.state.llm_health = LLMHealthChecker(app.state.llm_client)

    # Note: Engine task queue lives in computation service (Phase 3D)
    # Frontend calls computation service directly for engine control.

    # Cascade Manager (Phase 3C — now wired to review API)
    from shared.cascade.manager import CascadeManager
    app.state.cascade_manager = CascadeManager(
        data_service=app.state.data_service,
        llm_client=app.state.llm_client if app.state.llm_client.is_available else None,
        debounce_seconds=60,
    )
    logger.info("CascadeManager initialized (debounce=60s)")

    logger.info(
        "Gateway ready — DataService + ReviewStore + ConversationManager + JWT + ComputationClient(%s) + CascadeManager",
        settings.computation_service_url,
    )
    yield
    logger.info("Gateway shutting down — closing connections …")
    await app.state.computation_client.close()
    try:
        from shared.database.engine import dispose_engine
        await dispose_engine()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Variance Agent — Gateway",
    description="Service 1: Auth, Chat/SSE, Dimensions, Config, Review, Approval, Notifications",
    version=VERSION,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow all origins in dev; tighten for production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
API_V1 = "/api/v1"

app.include_router(auth_router, prefix=API_V1)
app.include_router(chat_router, prefix=API_V1)
app.include_router(dimensions_router, prefix=API_V1)
app.include_router(config_router, prefix=API_V1)
app.include_router(review_router, prefix=API_V1)
app.include_router(approval_router, prefix=API_V1)
app.include_router(notifications_router, prefix=API_V1)
app.include_router(admin_router, prefix=API_V1)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="ok", service="gateway", version=VERSION)
