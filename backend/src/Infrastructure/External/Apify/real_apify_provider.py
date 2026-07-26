from __future__ import annotations

import asyncio
import logging

from apify_client import ApifyClient

from src.Infrastructure.External.Apify.exceptions import (
    ApifyRequestError,
    ApifyTokenMissingError,
)
from src.Infrastructure.External.Apify.posts_provider import PostsProvider

logger = logging.getLogger(__name__)

_ACTOR_ID = "harvestapi/linkedin-post-search"


class RealApifyProvider(PostsProvider):
    """Appelle l'API Apify réelle pour récupérer des posts LinkedIn.

    Aucun mapping métier — retourne les dicts bruts tels que fournis par Apify.
    """

    def __init__(self, token: str) -> None:
        if not token:
            raise ApifyTokenMissingError(
                "APIFY_API_TOKEN est absent. Définissez-le dans .env ou via la variable d'environnement."
            )
        self._token = token

    async def search_posts(self, query: str, limit: int) -> list[dict]:
        try:
            return await asyncio.to_thread(self._call_apify, query, limit)
        except ApifyRequestError:
            raise
        except Exception as exc:
            raise ApifyRequestError(f"Erreur lors de l'appel Apify : {exc}") from exc

    def _call_apify(self, query: str, limit: int) -> list[dict]:
        client = ApifyClient(self._token)

        logger.info("Lancement de l'acteur Apify '%s' (query=%r, limit=%d)", _ACTOR_ID, query, limit)
        run = client.actor(_ACTOR_ID).call(run_input={"searchQueries": [query], "maxPosts": limit, "sortBy": "date"})

        if run is None:
            logger.warning("L'acteur Apify n'a retourné aucun run.")
            return []

        dataset_id = run.default_dataset_id
        if not dataset_id:
            logger.warning("Run Apify sans defaultDatasetId.")
            return []

        items = client.dataset(dataset_id).list_items(limit=limit)
        result = list(items.items or [])
        logger.info("Apify a retourné %d item(s).", len(result))
        return result
