import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.Infrastructure.Config.database import AsyncSessionLocal


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Transactional fixture — rolls back after each test for full isolation."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
