from __future__ import annotations

import asyncio
from typing import Any

from src.Application.Gateway.mailer_gateway import MailerGateway
from src.Infrastructure.External.Mailer.exceptions import MailerSendError


class ResendMailerGateway(MailerGateway):
    """Sends emails via the Resend API.

    The Resend SDK is synchronous — calls are offloaded to a thread pool via
    asyncio.to_thread() to preserve the async interface (same pattern as RealApifyProvider).
    Inject _client in tests to avoid real HTTP calls.
    """

    def __init__(
        self,
        api_key: str,
        from_email: str,
        from_name: str,
        _client: Any = None,
    ) -> None:
        self._from_address = f"{from_name} <{from_email}>"
        if _client is not None:
            self._client = _client
        else:
            import resend  # imported here to keep the module-level import optional in tests
            resend.api_key = api_key
            self._client = resend.Emails

    async def send(self, to: str, subject: str, html: str) -> str | None:
        params = {
            "from": self._from_address,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        try:
            result = await asyncio.to_thread(self._client.send, params)
            if isinstance(result, dict):
                return result.get("id")
            return getattr(result, "id", None)
        except Exception as exc:
            raise MailerSendError(str(exc)) from exc
