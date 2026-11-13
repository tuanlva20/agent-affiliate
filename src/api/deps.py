"""AMAS v1.4.0 — FastAPI Dependency Injection."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields an active AsyncSession."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
