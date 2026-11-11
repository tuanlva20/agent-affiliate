"""Global test fixtures for AMAS test suite."""

import pytest
import pytest_asyncio
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from src.database.models import Base
from src.database.session import get_async_engine, get_session_factory

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True, scope="session")
def ensure_global_tmp_video_files():
    """Ensures test video fixtures exist on disk across all test suites."""
    paths = [Path("/tmp/vid.mp4"), Path("/tmp/video.mp4"), Path("/tmp/mock.mp4")]
    created = []
    for p in paths:
        if not p.exists():
            try:
                p.touch()
                created.append(p)
            except OSError:
                pass
    yield
    for p in created:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass


@pytest.fixture(scope="session")
def engine() -> AsyncEngine:
    """Session-scoped async SQLite engine for testing."""
    return get_async_engine(TEST_DB_URL, force_new=True)


@pytest_asyncio.fixture(scope="function")
async def init_db(engine: AsyncEngine):
    """Initializes and tears down clean database schema before and after each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(init_db, engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated AsyncSession bound to the test engine."""
    factory = get_session_factory(TEST_DB_URL)
    async with factory() as session:
        yield session
