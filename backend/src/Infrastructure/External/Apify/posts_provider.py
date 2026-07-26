from abc import ABC, abstractmethod


class PostsProvider(ABC):
    """Accès brut à une source de posts — retourne des dicts non mappés, sans objet métier."""

    @abstractmethod
    async def search_posts(self, query: str, limit: int) -> list[dict]: ...
