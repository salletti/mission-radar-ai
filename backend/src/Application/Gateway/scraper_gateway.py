from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Domain.Entity.raw_post import RawPost


class ScraperGateway(ABC):
    """Collecte de posts bruts depuis une source externe. Implémenté dans Infrastructure/."""

    @abstractmethod
    async def collect_posts(self, query: str, limit: int) -> list[RawPost]: ...
