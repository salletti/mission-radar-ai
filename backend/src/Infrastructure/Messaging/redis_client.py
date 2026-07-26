import redis.asyncio as aioredis

from src.Infrastructure.Config.settings import settings


class RedisClient:
    def __init__(self) -> None:
        self._client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=3,
        )

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


redis_client = RedisClient()
