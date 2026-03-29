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

from services.gateway.api.approval import router as approval_router
from services.gateway.api.auth import router as auth_router
from services.gateway.api.chat import router as chat_router
from services.gateway.api.config import router as config_router
from services.gateway.api.dimensions import router as dimensions_router
from services.gateway.api.notifications import router as notifications_router
from services.gateway.api.review import router as review_router
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
        - Initialise hierarchy cache (placeholder)
        - Connect Redis (placeholder)
    Shutdown:
        - Drain connections
    """
    logger.info("Gateway starting up — initialising caches …")
    # TODO: load hierarchy cache, connect Redis
    yield
    logger.info("Gateway shutting down — draining connections …")
    # TODO: close Redis pool


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


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="ok", service="gateway", version=VERSION)
