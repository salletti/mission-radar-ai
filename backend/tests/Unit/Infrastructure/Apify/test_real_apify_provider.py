"""Unit tests for RealApifyProvider — ApifyClient est entièrement mocké, zéro appel réseau."""
import pytest
from unittest.mock import MagicMock, patch

from src.Infrastructure.External.Apify.exceptions import (
    ApifyRequestError,
    ApifyTokenMissingError,
)
from src.Infrastructure.External.Apify.real_apify_provider import RealApifyProvider

_VALID_TOKEN = "apify_api_fake_token_for_tests"
_ACTOR_PATH = "src.Infrastructure.External.Apify.real_apify_provider.ApifyClient"


def _make_apify_client_mock(items: list[dict] | None = None, run: MagicMock | None = None) -> MagicMock:
    """Construit un mock ApifyClient qui retourne les items donnés."""
    # apify-client 3.x retourne un objet Pydantic Run avec attributs snake_case
    default_run = run if run is not None else MagicMock(default_dataset_id="dataset-123")
    default_items = items if items is not None else []

    dataset_mock = MagicMock()
    dataset_mock.list_items.return_value = MagicMock(items=default_items)

    actor_mock = MagicMock()
    actor_mock.call.return_value = default_run

    client_mock = MagicMock()
    client_mock.actor.return_value = actor_mock
    client_mock.dataset.return_value = dataset_mock

    return client_mock


class TestRealApifyProviderInit:
    def test_token_absent_leve_erreur(self):
        with pytest.raises(ApifyTokenMissingError):
            RealApifyProvider("")

    def test_token_valide_instancie_correctement(self):
        provider = RealApifyProvider(_VALID_TOKEN)
        assert provider is not None


class TestRealApifyProviderSearchPosts:
    async def test_reponse_valide_retourne_liste_de_dicts(self):
        items = [{"id": "1", "content": "Mission Python"}, {"id": "2", "content": "Mission Symfony"}]
        client_mock = _make_apify_client_mock(items=items)

        with patch(_ACTOR_PATH, return_value=client_mock):
            provider = RealApifyProvider(_VALID_TOKEN)
            result = await provider.search_posts("python freelance", 10)

        assert result == items

    async def test_run_none_retourne_liste_vide(self):
        client_mock = _make_apify_client_mock()
        client_mock.actor.return_value.call.return_value = None

        with patch(_ACTOR_PATH, return_value=client_mock):
            provider = RealApifyProvider(_VALID_TOKEN)
            result = await provider.search_posts("python freelance", 10)

        assert result == []

    async def test_dataset_vide_retourne_liste_vide(self):
        client_mock = _make_apify_client_mock(items=[])

        with patch(_ACTOR_PATH, return_value=client_mock):
            provider = RealApifyProvider(_VALID_TOKEN)
            result = await provider.search_posts("cobol freelance", 5)

        assert result == []

    async def test_erreur_sdk_leve_apify_request_error(self):
        client_mock = MagicMock()
        client_mock.actor.return_value.call.side_effect = RuntimeError("Apify actor failed")

        with patch(_ACTOR_PATH, return_value=client_mock):
            provider = RealApifyProvider(_VALID_TOKEN)
            with pytest.raises(ApifyRequestError):
                await provider.search_posts("python freelance", 10)

    async def test_input_format_correct(self):
        client_mock = _make_apify_client_mock(items=[])

        with patch(_ACTOR_PATH, return_value=client_mock):
            provider = RealApifyProvider(_VALID_TOKEN)
            await provider.search_posts("symfony freelance", 5)

        client_mock.actor.return_value.call.assert_called_once_with(
            run_input={"searchQueries": ["symfony freelance"], "maxPosts": 5, "sortBy": "date"}
        )

    async def test_items_none_retourne_liste_vide(self):
        client_mock = _make_apify_client_mock()
        client_mock.dataset.return_value.list_items.return_value = MagicMock(items=None)

        with patch(_ACTOR_PATH, return_value=client_mock):
            provider = RealApifyProvider(_VALID_TOKEN)
            result = await provider.search_posts("python freelance", 10)

        assert result == []
