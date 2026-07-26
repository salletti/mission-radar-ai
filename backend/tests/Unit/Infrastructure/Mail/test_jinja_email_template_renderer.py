"""Unit tests for JinjaEmailTemplateRenderer — uses real Jinja2 + real templates."""
from uuid import uuid4

import pytest

from src.Domain.Entity.digest_email import DigestEmail
from src.Domain.ValueObject.digest_mission import DigestMission
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Infrastructure.External.Mailer.jinja_email_template_renderer import JinjaEmailTemplateRenderer


def _make_digest(missions: tuple[DigestMission, ...] = ()) -> DigestEmail:
    return DigestEmail(
        user_id=uuid4(),
        user_email="jean@example.com",
        user_name="Jean Dupont",
        subject="Mission Radar AI — 2 nouvelles missions aujourd'hui",
        missions=missions,
    )


def _make_mission(
    score: float = 0.85,
    title: str = "Lead Python Developer",
    company: str = "Acme Corp",
    post_url: str | None = "https://linkedin.com/post/123",
    remote_mode: RemoteMode = RemoteMode.FULL_REMOTE,
    tjm: float | None = 700.0,
    stack: tuple[str, ...] = ("python", "fastapi", "postgresql"),
) -> DigestMission:
    return DigestMission(
        mission_match_id=uuid4(),
        analyzed_post_id=uuid4(),
        final_score=score,
        summary="Mission senior Python, full remote, 700€/j. Stack FastAPI + PostgreSQL.",
        title=title,
        company=company,
        detected_stack=stack,
        detected_remote_mode=remote_mode,
        detected_tjm=tjm,
        post_url=post_url,
    )


@pytest.fixture
def renderer() -> JinjaEmailTemplateRenderer:
    return JinjaEmailTemplateRenderer()


async def test_render_returns_non_empty_string(renderer: JinjaEmailTemplateRenderer):
    html = await renderer.render(_make_digest())
    assert isinstance(html, str)
    assert len(html) > 100


async def test_render_contains_user_name(renderer: JinjaEmailTemplateRenderer):
    html = await renderer.render(_make_digest())
    assert "Jean Dupont" in html


async def test_render_contains_mission_title(renderer: JinjaEmailTemplateRenderer):
    mission = _make_mission(title="Lead Python Developer")
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "Lead Python Developer" in html


async def test_render_contains_company(renderer: JinjaEmailTemplateRenderer):
    mission = _make_mission(company="Acme Corp")
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "Acme Corp" in html


async def test_render_contains_score_percentage(renderer: JinjaEmailTemplateRenderer):
    mission = _make_mission(score=0.85)
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "85" in html


async def test_render_contains_stack_technologies(renderer: JinjaEmailTemplateRenderer):
    mission = _make_mission(stack=("python", "fastapi", "postgresql"))
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "python" in html
    assert "fastapi" in html


async def test_render_contains_linkedin_link(renderer: JinjaEmailTemplateRenderer):
    mission = _make_mission(post_url="https://linkedin.com/post/abc")
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "https://linkedin.com/post/abc" in html


async def test_render_zero_missions_shows_empty_message(renderer: JinjaEmailTemplateRenderer):
    html = await renderer.render(_make_digest(missions=()))
    assert "Aucune nouvelle mission" in html


async def test_render_high_score_badge_is_green(renderer: JinjaEmailTemplateRenderer):
    """Score >= 0.8 → green badge (#dcfce7)."""
    mission = _make_mission(score=0.9)
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "#dcfce7" in html


async def test_render_medium_score_badge_is_yellow(renderer: JinjaEmailTemplateRenderer):
    """Score in [0.6, 0.8) → yellow badge (#fef9c3)."""
    mission = _make_mission(score=0.65)
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "#fef9c3" in html


async def test_render_low_score_badge_is_grey(renderer: JinjaEmailTemplateRenderer):
    """Score < 0.6 → grey badge (#f3f4f6)."""
    mission = _make_mission(score=0.45)
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "#f3f4f6" in html


async def test_render_multiple_missions(renderer: JinjaEmailTemplateRenderer):
    missions = (
        _make_mission(title="Lead Python Dev", score=0.9),
        _make_mission(title="Symfony Expert", score=0.75),
    )
    html = await renderer.render(_make_digest(missions=missions))
    assert "Lead Python Dev" in html
    assert "Symfony Expert" in html


async def test_render_is_valid_html(renderer: JinjaEmailTemplateRenderer):
    html = await renderer.render(_make_digest())
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html


async def test_render_tjm_displayed(renderer: JinjaEmailTemplateRenderer):
    mission = _make_mission(tjm=750.0)
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "750" in html


async def test_render_no_linkedin_link_when_url_none(renderer: JinjaEmailTemplateRenderer):
    mission = _make_mission(post_url=None)
    html = await renderer.render(_make_digest(missions=(mission,)))
    assert "Voir le post LinkedIn" not in html
