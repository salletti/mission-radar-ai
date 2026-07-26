from abc import ABC, abstractmethod


class MailerGateway(ABC):
    """Sends transactional emails. Implemented in Infrastructure/."""

    @abstractmethod
    async def send(self, to: str, subject: str, html: str) -> str | None: ...
