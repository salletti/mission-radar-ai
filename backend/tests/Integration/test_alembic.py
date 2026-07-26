import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.Infrastructure.Config.settings import settings


@pytest.mark.asyncio
async def test_database_connection_async():
    """La connexion async PostgreSQL fonctionne."""
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_alembic_version_table_exists():
    """Après 'alembic upgrade head', la table alembic_version doit exister.

    Prérequis CI : exécuter 'alembic upgrade head' avant ce test.
    """
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'alembic_version'
                )
            """)
        )
        exists = result.scalar()
    await engine.dispose()
    assert exists, "Table alembic_version absente — exécuter 'alembic upgrade head' d'abord"
