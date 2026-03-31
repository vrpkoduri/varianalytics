"""Variance Agent — Reports Service (Port 8002).

Handles report generation (PDF, PPTX, DOCX, XLSX), scheduling,
and distribution of variance analysis outputs.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.reports.api.distribution import router as distribution_router
from services.reports.api.reports import router as reports_router
from services.reports.api.scheduling import router as scheduling_router
from services.reports.generators.data_provider import ReportDataProvider
from services.reports.generators.storage import LocalReportStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("reports-service")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown lifecycle events."""
    logger.info("Reports service starting up")
    # Initialise report data provider and storage
    app.state.data_provider = ReportDataProvider(
        computation_url="http://localhost:8001",
    )
    app.state.storage = LocalReportStorage("data/reports")
    from services.reports.scheduler import ReportScheduler
    app.state.scheduler = ReportScheduler(reports_url="http://localhost:8002")
    await app.state.scheduler.start()
    yield
    logger.info("Reports service shutting down")
    if hasattr(app.state, "scheduler"):
        await app.state.scheduler.stop()
    await app.state.data_provider.close()


app = FastAPI(
    title="Variance Agent — Reports",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router, prefix="/api/v1")
app.include_router(scheduling_router, prefix="/api/v1")
app.include_router(distribution_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok", "service": "reports"}
