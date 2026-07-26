from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Domain.Entity.digest_email import DigestEmail


class EmailTemplateRendererGateway(ABC):
    """Renders a DigestEmail into an HTML string. Implemented in Infrastructure/."""

    @abstractmethod
    async def render(self, digest: "DigestEmail") -> str: ...
