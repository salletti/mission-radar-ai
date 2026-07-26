import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from src.Infrastructure.Messaging.rabbitmq_client import rabbitmq_client


@pytest.mark.asyncio
async def test_rabbitmq_ping():
    assert await rabbitmq_client.ping() is True


@pytest.mark.asyncio
async def test_health_includes_rabbitmq():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["services"]["rabbitmq"] == "up"
