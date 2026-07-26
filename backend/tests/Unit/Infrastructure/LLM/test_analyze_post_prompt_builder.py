"""Unit tests for analyze_post_prompt_builder — pure function, no I/O."""
from datetime import datetime, timezone


from src.Domain.Entity.raw_post import RawPost
from src.Infrastructure.External.LLM.analyze_post_prompt_builder import (
    build_analyze_post_prompt,
)

_NOW = datetime(2026, 6, 19, 10, 0, 0, tzinfo=timezone.utc)

_EXPECTED_JSON_FIELDS = [
    "is_job_offer",
    "title",
    "company",
    "location",
    "contract_type",
    "summary",
    "required_skills",
    "nice_to_have_skills",
    "seniority",
    "remote_policy",
    "daily_rate",
]


def _make_raw_post(
    content: str = "Recherche développeur Python senior freelance. Full remote. TJM 700€.",
    external_id: str = "post-001",
    author_name: str = "Alice Recruiter",
    post_url: str = "https://linkedin.com/posts/post-001",
) -> RawPost:
    return RawPost(
        source="linkedin",
        external_id=external_id,
        author_name=author_name,
        author_url="https://linkedin.com/in/alice",
        content=content,
        post_url=post_url,
        published_at=_NOW,
        scraped_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


def test_prompt_is_str() -> None:
    prompt = build_analyze_post_prompt(_make_raw_post())
    assert isinstance(prompt, str)


def test_prompt_contains_all_expected_json_fields() -> None:
    prompt = build_analyze_post_prompt(_make_raw_post())
    for field in _EXPECTED_JSON_FIELDS:
        assert f'"{field}"' in prompt, f'champ JSON manquant dans le prompt : "{field}"'


def test_prompt_contains_null_instruction() -> None:
    prompt = build_analyze_post_prompt(_make_raw_post())
    assert "null" in prompt


def test_prompt_contains_json_only_instruction() -> None:
    prompt = build_analyze_post_prompt(_make_raw_post())
    assert "JSON" in prompt


# ---------------------------------------------------------------------------
# Injection du RawPost
# ---------------------------------------------------------------------------


def test_prompt_contains_raw_post_content() -> None:
    content = "Mission Python senior FastAPI — full remote — TJM 700€."
    prompt = build_analyze_post_prompt(_make_raw_post(content=content))
    assert content in prompt


def test_prompt_contains_author_name() -> None:
    prompt = build_analyze_post_prompt(_make_raw_post(author_name="Bob Recruteur"))
    assert "Bob Recruteur" in prompt


def test_prompt_contains_post_url() -> None:
    url = "https://linkedin.com/posts/xyz-42"
    prompt = build_analyze_post_prompt(_make_raw_post(post_url=url))
    assert url in prompt


def test_prompt_contains_published_at() -> None:
    raw_post = _make_raw_post()
    prompt = build_analyze_post_prompt(raw_post)
    assert raw_post.published_at.isoformat() in prompt


# ---------------------------------------------------------------------------
# Déterminisme
# ---------------------------------------------------------------------------


def test_prompt_is_deterministic() -> None:
    raw_post = _make_raw_post()
    p1 = build_analyze_post_prompt(raw_post)
    p2 = build_analyze_post_prompt(raw_post)
    assert p1 == p2


def test_different_posts_produce_different_prompts() -> None:
    post_a = _make_raw_post(content="Mission React senior.", external_id="post-a")
    post_b = _make_raw_post(content="Mission Symfony junior.", external_id="post-b")
    assert build_analyze_post_prompt(post_a) != build_analyze_post_prompt(post_b)
