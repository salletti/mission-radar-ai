import asyncio

import pika

from src.Infrastructure.Config.settings import settings


class RabbitMQClient:
    def __init__(self) -> None:
        self._params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD,
            ),
            connection_attempts=1,
            socket_timeout=3,
        )

    def _ping_sync(self) -> bool:
        try:
            conn = pika.BlockingConnection(self._params)
            conn.close()
            return True
        except Exception:
            return False

    async def ping(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._ping_sync)


rabbitmq_client = RabbitMQClient()
