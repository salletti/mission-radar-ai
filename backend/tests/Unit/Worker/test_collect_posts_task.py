"""Unit tests for collect_posts_task — no DB, no network, no Celery broker."""
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.Infrastructure.Worker.tasks.collect_posts_task import _collect, collect_posts

_QUERY_ID = str(uuid4())
_NOW = datetime(2026, 6, 15, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeRawPostRepository:
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], object] = {}
        self.save_many_calls: list[list] = []

    async def save(self, post: object) -> None:
        self._store[(post.source, post.external_id)] = post  # type: ignore[attr-defined]

    async def save_many(self, posts: list) -> None:
        self.save_many_calls.append(posts)
        for p in posts:
            self._store[(p.source, p.external_id)] = p  # type: ignore[attr-defined]

    async def exists_by_external_id(self, source: str, external_id: str) -> bool:
        return (source, external_id) in self._store

    async def get_by_source_and_external_id(self, source: str, external_id: str) -> Optional[object]:
        return self._store.get((source, external_id))

    async def get_by_id(self, post_id: UUID) -> Optional[object]:
        return None

    async def list_recent(self, limit: int) -> list:
        return []


class FakeSearchQueryRawPostRepository:
    def __init__(self) -> None:
        self._links: set[tuple[UUID, UUID]] = set()

    async def save(self, link: object) -> None:
        self._links.add((link.search_query_id, link.raw_post_id))  # type: ignore[attr-defined]

    async def exists(self, search_query_id: UUID, raw_post_id: UUID) -> bool:
        return (search_query_id, raw_post_id) in self._links

    async def find_by_search_query_id(self, search_query_id: UUID) -> list:
        return []

    async def find_by_raw_post_id(self, raw_post_id: UUID) -> list:
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_ctx() -> tuple[MagicMock, MagicMock]:
    """Renvoie (mock_AsyncSessionLocal, mock_session) — prêt pour `async with`."""
    session = MagicMock()
    session.commit = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx), session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_collect_posts_task_ignores_result() -> None:
    """La tâche Celery ne stocke pas son résultat dans Redis — PostgreSQL est la source de vérité."""
    assert collect_posts.ignore_result is True


@pytest.mark.asyncio
async def test_collect_nominal_saves_new_posts() -> None:
    """Posts collectés et sauvegardés — aucun doublon."""
    fake_repo = FakeRawPostRepository()
    fake_link_repo = FakeSearchQueryRawPostRepository()
    mock_session_local, _ = _make_session_ctx()

    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        result = await _collect("python freelance paris", 10, _QUERY_ID)

    assert result["posts_collected"] > 0
    assert result["posts_saved"] == result["posts_collected"]
    assert result["duplicates_skipped"] == 0
    assert result["analyses_dispatched"] == result["posts_saved"]


@pytest.mark.asyncio
async def test_collect_empty_fixture_returns_zeros() -> None:
    """Query sans fixture correspondante → 0 posts collectés, 0 sauvegardés."""
    fake_repo = FakeRawPostRepository()
    fake_link_repo = FakeSearchQueryRawPostRepository()
    mock_session_local, _ = _make_session_ctx()

    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        result = await _collect("cobol freelance paris", 10, _QUERY_ID)

    assert result["posts_collected"] == 0
    assert result["posts_saved"] == 0
    assert result["duplicates_skipped"] == 0
    assert result["analyses_dispatched"] == 0


@pytest.mark.asyncio
async def test_collect_all_duplicates_skipped() -> None:
    """Deuxième appel avec même query et même repo → tous doublons."""
    fake_repo = FakeRawPostRepository()
    fake_link_repo = FakeSearchQueryRawPostRepository()

    # Premier appel : sauvegarde tous les posts
    mock_session_local_1, _ = _make_session_ctx()
    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local_1), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        first = await _collect("python freelance paris", 5, _QUERY_ID)

    # Deuxième appel : même repo pré-rempli → tous doublons
    mock_session_local_2, _ = _make_session_ctx()
    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local_2), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        second = await _collect("python freelance paris", 5, _QUERY_ID)

    assert second["posts_saved"] == 0
    assert second["duplicates_skipped"] == first["posts_saved"]
    assert second["posts_collected"] == first["posts_collected"]
    assert second["analyses_dispatched"] == 0


@pytest.mark.asyncio
async def test_collect_propagates_provider_error() -> None:
    """Erreur du provider → exception propagée depuis _collect()."""
    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.MockApifyProvider") as MockProviderCls, \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        mock_provider = MagicMock()
        mock_provider.search_posts = AsyncMock(side_effect=RuntimeError("Apify down"))
        MockProviderCls.return_value = mock_provider

        with pytest.raises(RuntimeError, match="Apify down"):
            await _collect("python freelance paris", 10, _QUERY_ID)


# ---------------------------------------------------------------------------
# Tests switch APIFY_PROVIDER
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apify_provider_mock_instancie_mock_provider() -> None:
    """APIFY_PROVIDER=mock → MockApifyProvider instancié."""
    fake_repo = FakeRawPostRepository()
    fake_link_repo = FakeSearchQueryRawPostRepository()
    mock_session_local, _ = _make_session_ctx()

    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.settings") as mock_settings, \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.MockApifyProvider") as MockCls, \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        mock_settings.APIFY_PROVIDER = "mock"
        MockCls.return_value = MagicMock()
        MockCls.return_value.search_posts = AsyncMock(return_value=[])
        await _collect("python freelance paris", 5, _QUERY_ID)

    MockCls.assert_called_once()


@pytest.mark.asyncio
async def test_apify_provider_real_instancie_real_provider() -> None:
    """APIFY_PROVIDER=real → RealApifyProvider instancié avec le token."""
    fake_repo = FakeRawPostRepository()
    fake_link_repo = FakeSearchQueryRawPostRepository()
    mock_session_local, _ = _make_session_ctx()

    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.settings") as mock_settings, \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.RealApifyProvider") as RealCls, \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        mock_settings.APIFY_PROVIDER = "real"
        mock_settings.APIFY_API_TOKEN = "apify_test_token"
        RealCls.return_value = MagicMock()
        RealCls.return_value.search_posts = AsyncMock(return_value=[])
        await _collect("python freelance paris", 5, _QUERY_ID)

    RealCls.assert_called_once_with("apify_test_token")


# ---------------------------------------------------------------------------
# Tests dispatch analyze_post_task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_called_for_each_new_post() -> None:
    """N nouveaux posts → send_task appelé N fois avec 'tasks.analyze_post'."""
    fake_repo = FakeRawPostRepository()
    fake_link_repo = FakeSearchQueryRawPostRepository()
    mock_session_local, _ = _make_session_ctx()

    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task") as mock_send:
        result = await _collect("python freelance paris", 10, _QUERY_ID)

    assert mock_send.call_count == result["posts_saved"]
    assert result["analyses_dispatched"] == result["posts_saved"]
    mock_send.assert_any_call("tasks.analyze_post", args=[ANY])


@pytest.mark.asyncio
async def test_dispatch_not_called_when_all_duplicates() -> None:
    """Tous doublons → send_task jamais appelé, analyses_dispatched == 0."""
    fake_repo = FakeRawPostRepository()
    fake_link_repo = FakeSearchQueryRawPostRepository()

    # Premier appel : pré-remplit le repo
    mock_session_local_1, _ = _make_session_ctx()
    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local_1), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        await _collect("python freelance paris", 5, _QUERY_ID)

    # Deuxième appel : tous doublons
    mock_session_local_2, _ = _make_session_ctx()
    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local_2), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task") as mock_send:
        result = await _collect("python freelance paris", 5, _QUERY_ID)

    mock_send.assert_not_called()
    assert result["analyses_dispatched"] == 0


@pytest.mark.asyncio
async def test_analyses_dispatched_always_present_in_result() -> None:
    """La clé 'analyses_dispatched' est toujours présente dans le résultat."""
    fake_repo = FakeRawPostRepository()
    fake_link_repo = FakeSearchQueryRawPostRepository()
    mock_session_local, _ = _make_session_ctx()

    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemyRawPostRepository", return_value=fake_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.SqlAlchemySearchQueryRawPostRepository", return_value=fake_link_repo), \
         patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        result = await _collect("cobol freelance paris", 10, _QUERY_ID)

    assert "analyses_dispatched" in result
    assert "links_created" in result
