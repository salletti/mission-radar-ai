"""Unit tests for FallbackPostsProvider — providers en mémoire, zéro appel réseau."""
import pytest

from src.Infrastructure.External.Apify.exceptions import ApifyQuotaExceededError, ApifyRequestError
from src.Infrastructure.External.Apify.fallback_posts_provider import (
    FallbackPostsProvider,
    build_real_posts_provider,
)
from src.Infrastructure.External.Apify.posts_provider import PostsProvider
from src.Infrastructure.External.Apify.real_apify_provider import RealApifyProvider


class _StubProvider(PostsProvider):
    def __init__(self, result: list[dict] | Exception) -> None:
        self._result = result
        self.calls = 0

    async def search_posts(self, query: str, limit: int) -> list[dict]:
        self.calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


async def test_compte_principal_ok_n_utilise_pas_le_secours() -> None:
    primary, fallback = _StubProvider([{"id": "1"}]), _StubProvider([{"id": "2"}])

    result = await FallbackPostsProvider([primary, fallback]).search_posts("python", 10)

    assert result == [{"id": "1"}]
    assert fallback.calls == 0


async def test_quota_epuise_bascule_sur_le_compte_de_secours() -> None:
    primary = _StubProvider(ApifyQuotaExceededError("Monthly usage hard limit exceeded"))
    fallback = _StubProvider([{"id": "2"}])

    result = await FallbackPostsProvider([primary, fallback]).search_posts("python", 10)

    assert result == [{"id": "2"}]


async def test_bascule_memorisee_pour_les_queries_suivantes_du_run() -> None:
    primary = _StubProvider(ApifyQuotaExceededError("quota"))
    fallback = _StubProvider([{"id": "2"}])
    provider = FallbackPostsProvider([primary, fallback])

    await provider.search_posts("python", 10)
    await provider.search_posts("symfony", 10)

    assert primary.calls == 1
    assert fallback.calls == 2


async def test_tous_les_comptes_epuises_remonte_l_erreur_de_quota() -> None:
    provider = FallbackPostsProvider(
        [_StubProvider(ApifyQuotaExceededError("quota #1")), _StubProvider(ApifyQuotaExceededError("quota #2"))]
    )

    with pytest.raises(ApifyQuotaExceededError, match="quota #2"):
        await provider.search_posts("python", 10)


async def test_erreur_hors_quota_ne_bascule_pas() -> None:
    fallback = _StubProvider([{"id": "2"}])
    provider = FallbackPostsProvider([_StubProvider(ApifyRequestError("actor failed")), fallback])

    with pytest.raises(ApifyRequestError, match="actor failed"):
        await provider.search_posts("python", 10)
    assert fallback.calls == 0


def test_sans_token_de_secours_retourne_le_provider_principal_seul() -> None:
    assert isinstance(build_real_posts_provider("apify_api_primary"), RealApifyProvider)


def test_avec_token_de_secours_retourne_un_fallback_provider() -> None:
    assert isinstance(build_real_posts_provider("apify_api_primary", "apify_api_fallback"), FallbackPostsProvider)
