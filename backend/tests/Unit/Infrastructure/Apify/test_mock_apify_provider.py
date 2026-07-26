"""Unit tests for MockApifyProvider — no network, no I/O hors fixtures JSON."""
from __future__ import annotations

import json
from pathlib import Path


from src.Infrastructure.External.Apify.mock_apify_provider import MockApifyProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider(tmp_path: Path, symfony_data: list | None = None, python_data: list | None = None) -> MockApifyProvider:
    """Crée un MockApifyProvider pointant vers un dossier de fixtures temporaire."""
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    (fixtures_dir / "linkedin_posts_symfony_freelance_paris.json").write_text(
        json.dumps(symfony_data if symfony_data is not None else []),
        encoding="utf-8",
    )
    (fixtures_dir / "linkedin_posts_python_freelance_paris.json").write_text(
        json.dumps(python_data if python_data is not None else []),
        encoding="utf-8",
    )
    (fixtures_dir / "linkedin_posts_empty.json").write_text("[]", encoding="utf-8")
    return MockApifyProvider(fixtures_dir=fixtures_dir)


_SYMFONY_POST = {"id": "sf-001", "content": "Mission Symfony freelance Paris. TJM 650€."}
_PYTHON_POST = {"id": "py-001", "content": "Mission Python FastAPI. TJM 700€. Remote."}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_symfony_query_loads_symfony_fixture(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path, symfony_data=[_SYMFONY_POST])

    result = await provider.search_posts(query="symfony freelance paris", limit=10)

    assert result == [_SYMFONY_POST]


async def test_python_query_loads_python_fixture(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path, python_data=[_PYTHON_POST])

    result = await provider.search_posts(query="python freelance", limit=10)

    assert result == [_PYTHON_POST]


async def test_unknown_query_loads_empty_fixture(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path)

    result = await provider.search_posts(query="java spring boot", limit=10)

    assert result == []


async def test_empty_fixture_returns_empty_list(tmp_path: Path) -> None:
    provider = _make_provider(tmp_path)

    result = await provider.search_posts(query="symfony", limit=10)

    assert result == []


async def test_limit_applied_to_results(tmp_path: Path) -> None:
    posts = [{"id": f"sf-{i:03d}", "content": f"Post {i}"} for i in range(5)]
    provider = _make_provider(tmp_path, symfony_data=posts)

    result = await provider.search_posts(query="symfony", limit=3)

    assert len(result) == 3
    assert result == posts[:3]
