"""Variance Agent — Computation Engine (Service 2).

FastAPI service exposing the 5.5-pass materiality-first computation engine,
dashboard aggregations, variance drill-down, P&L views, and narrative synthesis.

Runs on port 8001.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.data.service import DataService

from services.computation.api.dashboard import router as dashboard_router
from services.computation.api.drilldown import router as drilldown_router
from services.computation.api.engine_control import router as engine_router
from services.computation.api.pl import router as pl_router
from services.computation.api.synthesis import router as synthesis_router
from services.computation.api.variances import router as variances_router

logger = logging.getLogger("computation")

# ---------------------------------------------------------------------------
# Structured logging setup
# ---------------------------------------------------------------------------

def _configure_logging() -> None:
    """Configure structured JSON-style logging for the service."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks.

    Startup:
        - Configure logging
        - Warm caches (hierarchy rollup, dimension lookups)
        - Pre-load synthetic data if present

    Shutdown:
        - Flush pending audit-log writes
        - Close Redis / DB connections
    """
    _configure_logging()
    logger.info("Computation engine starting up …")
    start = time.monotonic()

    # Load DataService (all parquet tables into memory)
    app.state.data_service = DataService()
    logger.info("DataService initialized")

    # Initialize LLM + RAG (optional — graceful if unavailable)
    try:
        from shared.llm.client import LLMClient
        from shared.knowledge.embedding import EmbeddingService
        from shared.knowledge.vector_store import create_vector_store
        from shared.knowledge.rag import RAGRetriever

        app.state.llm_client = LLMClient()
        embedding_svc = EmbeddingService()
        vector_store = create_vector_store(qdrant_url=None)  # InMemory for computation
        app.state.rag_retriever = RAGRetriever(embedding_svc, vector_store)
        logger.info(
            "LLM + RAG initialized (available=%s)", app.state.llm_client.is_available
        )
    except Exception as exc:
        logger.warning("LLM/RAG initialization failed: %s", exc)
        app.state.llm_client = None
        app.state.rag_retriever = None

    # Redis cache (Phase 3E)
    from shared.data.cache import CacheClient
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    app.state.cache = CacheClient(redis_url=redis_url)
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(app.state.cache.connect())
    except Exception:
        logger.warning("Redis cache not available — running without cache")

    # Engine task queue (Phase 3D + 3E hot-reload)
    from shared.engine.task_queue import EngineTaskQueue
    app.state.engine_task_queue = EngineTaskQueue(
        data_dir="data/output",
        data_service=app.state.data_service,
        cache_client=app.state.cache if app.state.cache.is_connected else None,
    )
    logger.info("Engine task queue initialized (cache=%s)", app.state.cache.is_connected)

    elapsed = time.monotonic() - start
    logger.info("Startup complete in %.2f s", elapsed)

    yield  # ── application serves requests ──

    logger.info("Computation engine shutting down …")
    # TODO: flush audit log
    # TODO: close Redis / DB pools


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Variance Agent — Computation Engine",
    description="5.5-pass materiality-first engine for variance detection, "
    "decomposition, trend analysis, and narrative generation.",
    version="0.1.0",
    lifespan=lifespan,
)

# -- CORS ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Routers ---------------------------------------------------------------
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(variances_router, prefix="/api/v1")
app.include_router(drilldown_router, prefix="/api/v1")
app.include_router(pl_router, prefix="/api/v1")
app.include_router(synthesis_router, prefix="/api/v1")
app.include_router(engine_router, prefix="/api/v1")


# -- Health ----------------------------------------------------------------

@app.get("/health", tags=["infra"])
async def health_check() -> dict[str, str]:
    """Liveness / readiness probe for container orchestration."""
    return {"status": "healthy", "service": "computation"}
