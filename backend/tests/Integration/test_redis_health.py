import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from src.Infrastructure.Messaging.redis_client import redis_client


@pytest.mark.asyncio
async def test_redis_ping():
    assert await redis_client.ping() is True


@pytest.mark.asyncio
async def test_health_includes_redis():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["services"]["redis"] == "up"
