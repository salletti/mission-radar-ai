from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.Infrastructure.Config.settings import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.APP_DEBUG)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# asyncio.run() dans chaque Celery task crée un nouvel event loop — le pool de connexions
# asyncpg devient stale entre deux tasks. NullPool force une connexion fraîche à chaque call.
celery_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=settings.APP_DEBUG,
)
CeleryAsyncSessionLocal = async_sessionmaker(celery_engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
