"""Async SQLAlchemy engine and session management.

Provides factory functions for the async engine and session maker.
Supports PostgreSQL (asyncpg) for production and SQLite (aiosqlite) for tests.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def init_engine(
    database_url: str,
    *,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> AsyncEngine:
    """Create the global async engine.

    Args:
        database_url: SQLAlchemy async connection URL.
            PostgreSQL: ``postgresql+asyncpg://user:pass@host/db``
            SQLite:     ``sqlite+aiosqlite:///path`` or ``sqlite+aiosqlite://``
        echo: If True, log all SQL statements.
        pool_size: Number of persistent connections (ignored for SQLite).
        max_overflow: Max temporary connections above pool_size (ignored for SQLite).

    Returns:
        The newly created :class:`AsyncEngine`.
    """
    global _engine, _session_factory

    kwargs: dict = {"echo": echo}

    # SQLite does not support pool_size / max_overflow
    if not database_url.startswith("sqlite"):
        kwargs["pool_size"] = pool_size
        kwargs["max_overflow"] = max_overflow

    _engine = create_async_engine(database_url, **kwargs)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    logger.info("Database engine initialised: %s", database_url.split("@")[-1] if "@" in database_url else database_url)
    return _engine


def get_engine() -> AsyncEngine:
    """Return the current async engine. Raises if ``init_engine`` has not been called."""
    if _engine is None:
        raise RuntimeError("Database engine not initialised. Call init_engine() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the current session factory. Raises if ``init_engine`` has not been called."""
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Call init_engine() first.")
    return _session_factory


async def init_db() -> None:
    """Create all tables defined in ``Base.metadata``.

    Safe to call multiple times — SQLAlchemy's ``create_all`` is idempotent.
    """
    from shared.database.models import Base  # local import to avoid circular deps

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created / verified.")


async def dispose_engine() -> None:
    """Dispose the engine and release all pooled connections."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed.")

    _engine = None
    _session_factory = None
