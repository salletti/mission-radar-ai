from __future__ import annotations

import json
from pathlib import Path

from src.Infrastructure.External.Apify.posts_provider import PostsProvider

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _resolve_fixture(query: str, fixtures_dir: Path) -> Path:
    q = query.lower()
    if "symfony" in q:
        return fixtures_dir / "linkedin_posts_symfony_freelance_paris.json"
    if "python" in q:
        return fixtures_dir / "linkedin_posts_python_freelance_paris.json"
    return fixtures_dir / "linkedin_posts_empty.json"


class MockApifyProvider(PostsProvider):
    """Implémentation de développement — charge des fixtures JSON sans appel réseau."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self._fixtures_dir = fixtures_dir or _FIXTURES_DIR

    async def search_posts(self, query: str, limit: int) -> list[dict]:
        fixture_path = _resolve_fixture(query, self._fixtures_dir)
        data: list[dict] = json.loads(fixture_path.read_text(encoding="utf-8"))
        return data[:limit]
