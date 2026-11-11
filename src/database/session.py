"""AMAS v1.4.0 Async Database Session & Engine Management.

Supports PostgreSQL (asyncpg) for production and SQLite (aiosqlite) for testing.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from functools import wraps
from typing import AsyncGenerator, Dict, Optional, Tuple

from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool


# Ensure SQLite compiler hook is registered
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# Engine and sessionmaker cache
_engines: Dict[str, AsyncEngine] = {}
_session_factories: Dict[str, async_sessionmaker[AsyncSession]] = {}
_sqlite_locks: Dict[Tuple[str, int], asyncio.Lock] = {}


def _get_sqlite_lock(url: str) -> asyncio.Lock:
    try:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
    except RuntimeError:
        loop_id = 0
    key = (url, loop_id)
    if key not in _sqlite_locks:
        _sqlite_locks[key] = asyncio.Lock()
    return _sqlite_locks[key]


def get_async_engine(
    database_url: Optional[str] = None, force_new: bool = False
) -> AsyncEngine:
    """Returns an AsyncEngine instance.

    For SQLite engines, StaticPool, check_same_thread=False, and PRAGMA foreign_keys=ON are configured.
    """
    url = database_url or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if force_new:
        _engines.pop(url, None)
        _session_factories.pop(url, None)

    if url not in _engines:
        if url.startswith("sqlite"):
            engine = create_async_engine(
                url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=False,
            )

            @event.listens_for(engine.sync_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        else:
            engine = create_async_engine(
                url,
                pool_size=20,
                max_overflow=30,
                pool_timeout=30.0,
                pool_pre_ping=True,
                echo=False,
            )
        _engines[url] = engine
    return _engines[url]


def get_session_factory(
    database_url: Optional[str] = None,
) -> async_sessionmaker[AsyncSession]:
    """Returns an async_sessionmaker bound to the corresponding engine."""
    url = database_url or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if url not in _session_factories:
        engine = get_async_engine(url)
        _session_factories[url] = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
    return _session_factories[url]


class _DualAsyncContextManager:
    """Wrapper enabling both 'async with get_db()' and 'async for db in get_db()' syntax."""

    def __init__(self, gen_func, *args, **kwargs):
        self._cm = asynccontextmanager(gen_func)(*args, **kwargs)

    async def __aenter__(self) -> AsyncSession:
        return await self._cm.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._cm.__aexit__(exc_type, exc_val, exc_tb)

    async def __aiter__(self):
        async with self as val:
            yield val


def _dual_async_cm(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return _DualAsyncContextManager(func, *args, **kwargs)

    return wrapper


@_dual_async_cm
async def get_db(
    database_url: Optional[str] = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Context manager / async generator providing an isolated AsyncSession.

    Commits on clean exit, rolls back on exception, and guarantees session closure.
    For SQLite engines with StaticPool, serializes access via asyncio.Lock to
    prevent uncommitted state cross-pollution across concurrent coroutines.
    """
    url = database_url or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    factory = get_session_factory(database_url)

    if url.startswith("sqlite"):
        lock = _get_sqlite_lock(url)
        async with lock:
            async with factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
    else:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
