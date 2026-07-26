import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from main import app
from src.Infrastructure.Config.database import AsyncSessionLocal


@pytest.mark.asyncio
async def test_postgres_direct_connection():
    """Vérifie la connexion directe à PostgreSQL via SQLAlchemy async."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
    assert value == 1


@pytest.mark.asyncio
async def test_health_endpoint_postgres_up():
    """Vérifie que /health retourne status ok et postgres up avec le conteneur actif."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["services"]["api"] == "up"
    assert data["services"]["postgres"] == "up"
