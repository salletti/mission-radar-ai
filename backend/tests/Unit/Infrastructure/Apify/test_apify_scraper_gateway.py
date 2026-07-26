"""Unit tests for ApifyScraperGateway — mapping Apify dict → RawPost."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.Infrastructure.External.Apify.apify_scraper_gateway import ApifyScraperGateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gateway(posts: list[dict[str, Any]]) -> ApifyScraperGateway:
    """Crée un gateway avec un provider stubbé retournant les posts fournis."""
    provider = AsyncMock()
    provider.search_posts.return_value = posts
    return ApifyScraperGateway(provider=provider)


def _full_post(*, post_id: str = "post-001") -> dict[str, Any]:
    return {
        "id": post_id,
        "linkedinUrl": f"https://www.linkedin.com/posts/{post_id}",
        "content": "Mission Symfony senior, 650€/j, full remote. Démarrage ASAP.",
        "author": {
            "name": "Alice Dupont",
            "linkedinUrl": "https://www.linkedin.com/in/alice-dupont",
        },
        "postedAt": {
            "date": "2026-06-06T07:30:02.000Z",
        },
    }


# ---------------------------------------------------------------------------
# Mapping complet
# ---------------------------------------------------------------------------


async def test_mapping_complet_tous_les_champs() -> None:
    gateway = _make_gateway([_full_post()])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert len(posts) == 1
    p = posts[0]
    assert p.external_id == "post-001"
    assert p.source == "linkedin"
    assert p.content == "Mission Symfony senior, 650€/j, full remote. Démarrage ASAP."
    assert p.post_url == "https://www.linkedin.com/posts/post-001"
    assert p.author_name == "Alice Dupont"
    assert p.author_url == "https://www.linkedin.com/in/alice-dupont"
    assert p.published_at == datetime(2026, 6, 6, 7, 30, 2, tzinfo=timezone.utc)
    assert p.scraped_at.tzinfo is not None  # toujours UTC


async def test_source_est_toujours_linkedin() -> None:
    gateway = _make_gateway([_full_post()])

    posts = await gateway.collect_posts(query="python", limit=10)

    assert posts[0].source == "linkedin"


# ---------------------------------------------------------------------------
# Mapping partiel — champs métadonnées manquants → valeur par défaut
# ---------------------------------------------------------------------------


async def test_author_absent_retourne_chaines_vides() -> None:
    data = _full_post()
    del data["author"]
    gateway = _make_gateway([data])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert len(posts) == 1
    assert posts[0].author_name == ""
    assert posts[0].author_url == ""


async def test_author_name_absent_retourne_chaine_vide() -> None:
    data = _full_post()
    data["author"] = {"linkedinUrl": "https://www.linkedin.com/in/bob"}
    gateway = _make_gateway([data])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert posts[0].author_name == ""
    assert posts[0].author_url == "https://www.linkedin.com/in/bob"


async def test_linkedin_url_absent_retourne_chaine_vide() -> None:
    data = _full_post()
    del data["linkedinUrl"]
    gateway = _make_gateway([data])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert len(posts) == 1
    assert posts[0].post_url == ""


async def test_posted_at_absent_utilise_scraped_at() -> None:
    data = _full_post()
    del data["postedAt"]
    gateway = _make_gateway([data])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert len(posts) == 1
    assert posts[0].published_at == posts[0].scraped_at


async def test_posted_at_date_invalide_utilise_scraped_at() -> None:
    data = _full_post()
    data["postedAt"] = {"date": "pas-une-date"}
    gateway = _make_gateway([data])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert len(posts) == 1
    assert posts[0].published_at == posts[0].scraped_at


# ---------------------------------------------------------------------------
# Posts invalides — ignorés
# ---------------------------------------------------------------------------


async def test_post_sans_id_est_ignore() -> None:
    data = _full_post()
    del data["id"]
    gateway = _make_gateway([data])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert posts == []


async def test_post_sans_content_est_ignore() -> None:
    data = _full_post()
    del data["content"]
    gateway = _make_gateway([data])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert posts == []


async def test_post_content_vide_est_ignore() -> None:
    data = _full_post()
    data["content"] = "   "
    gateway = _make_gateway([data])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert posts == []


async def test_post_content_null_est_ignore() -> None:
    data = _full_post()
    data["content"] = None
    gateway = _make_gateway([data])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert posts == []


# ---------------------------------------------------------------------------
# Fixture vide
# ---------------------------------------------------------------------------


async def test_fixture_vide_retourne_liste_vide() -> None:
    gateway = _make_gateway([])

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert posts == []


# ---------------------------------------------------------------------------
# Plusieurs posts — mix valides et invalides
# ---------------------------------------------------------------------------


async def test_plusieurs_posts_mix_valides_invalides() -> None:
    posts_data = [
        _full_post(post_id="valid-001"),
        _full_post(post_id="valid-002"),
        {**_full_post(post_id="no-content"), "content": ""},  # ignoré
        _full_post(post_id="valid-003"),
        {"id": None, "content": "Post sans id"},  # ignoré
    ]
    gateway = _make_gateway(posts_data)

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert len(posts) == 3
    ids = [p.external_id for p in posts]
    assert ids == ["valid-001", "valid-002", "valid-003"]


async def test_plusieurs_posts_tous_valides() -> None:
    posts_data = [_full_post(post_id=f"post-{i:03d}") for i in range(5)]
    gateway = _make_gateway(posts_data)

    posts = await gateway.collect_posts(query="symfony", limit=10)

    assert len(posts) == 5
