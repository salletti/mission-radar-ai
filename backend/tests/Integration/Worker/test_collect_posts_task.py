"""Integration tests for _collect() — MockApifyProvider + real PostgreSQL."""

import pytest
from unittest.mock import patch

from src.Infrastructure.Worker.tasks.collect_posts_task import _collect


@pytest.mark.asyncio
async def test_collect_persists_new_posts(search_query_id: str) -> None:
    """Premier appel : posts collectés via fixture et persistés en base."""
    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task") as mock_send:
        result = await _collect("python freelance paris", 10, search_query_id)

    assert result["posts_collected"] > 0
    assert result["posts_saved"] == result["posts_collected"]
    assert result["duplicates_skipped"] == 0
    assert result["analyses_dispatched"] == result["posts_saved"]
    assert mock_send.call_count == result["posts_saved"]


@pytest.mark.asyncio
async def test_collect_second_call_skips_duplicates(search_query_id: str) -> None:
    """Deuxième appel identique → 0 sauvegardés, tous doublons détectés, 0 dispatched."""
    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        first = await _collect("python freelance paris", 10, search_query_id)

    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task") as mock_send:
        second = await _collect("python freelance paris", 10, search_query_id)

    assert second["posts_collected"] == first["posts_collected"]
    assert second["posts_saved"] == 0
    assert second["duplicates_skipped"] == first["posts_saved"]
    assert second["analyses_dispatched"] == 0
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_collect_empty_fixture_returns_zeros(search_query_id: str) -> None:
    """Query sans fixture → 0 posts, pas d'erreur."""
    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task") as mock_send:
        result = await _collect("cobol freelance paris", 10, search_query_id)

    assert result["posts_collected"] == 0
    assert result["posts_saved"] == 0
    assert result["duplicates_skipped"] == 0
    assert result["analyses_dispatched"] == 0
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_collect_result_keys_present(search_query_id: str) -> None:
    """Le dict retourné contient toujours les clés attendues."""
    with patch("src.Infrastructure.Worker.tasks.collect_posts_task.celery_app.send_task"):
        result = await _collect("symfony freelance paris", 5, search_query_id)

    assert "posts_collected" in result
    assert "posts_saved" in result
    assert "duplicates_skipped" in result
    assert "analyses_dispatched" in result
    assert "links_created" in result
    assert result["posts_collected"] == result["posts_saved"] + result["duplicates_skipped"]
