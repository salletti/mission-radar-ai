from __future__ import annotations

import logging

from src.Infrastructure.External.Apify.exceptions import ApifyQuotaExceededError
from src.Infrastructure.External.Apify.posts_provider import PostsProvider
from src.Infrastructure.External.Apify.real_apify_provider import RealApifyProvider

logger = logging.getLogger(__name__)


class FallbackPostsProvider(PostsProvider):
    """Décore plusieurs PostsProvider (un par compte Apify) et bascule sur le suivant
    quand le courant lève ApifyQuotaExceededError.

    La bascule est mémorisée pour la durée de vie de l'instance : les queries suivantes
    d'un même run ne réessaient pas un compte déjà épuisé. Les autres erreurs
    (acteur, réseau) remontent telles quelles — changer de compte ne les corrigerait pas.
    """

    def __init__(self, providers: list[PostsProvider]) -> None:
        if not providers:
            raise ValueError("FallbackPostsProvider requires at least one provider")
        self._providers = providers
        self._current = 0

    async def search_posts(self, query: str, limit: int) -> list[dict]:
        while True:
            try:
                return await self._providers[self._current].search_posts(query, limit)
            except ApifyQuotaExceededError as exc:
                if self._current == len(self._providers) - 1:
                    raise
                self._current += 1
                logger.warning(
                    "Quota Apify épuisé sur le compte #%d (%s) — bascule sur le compte #%d",
                    self._current,
                    exc,
                    self._current + 1,
                )


def build_real_posts_provider(primary_token: str, fallback_token: str = "") -> PostsProvider:
    """Compte principal seul, ou compte principal + compte de secours si un second token est fourni."""
    primary = RealApifyProvider(primary_token)
    if not fallback_token:
        return primary
    return FallbackPostsProvider([primary, RealApifyProvider(fallback_token)])
