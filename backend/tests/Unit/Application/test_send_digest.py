"""Unit tests for SendDigest use case — no I/O, no real mailer, no real renderer."""
from uuid import uuid4

import pytest

from src.Application.Gateway.email_template_renderer_gateway import EmailTemplateRendererGateway
from src.Application.Gateway.mailer_gateway import MailerGateway
from src.Application.UseCase.send_digest import SendDigest
from src.Domain.Entity.digest_email import DigestEmail


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeRenderer(EmailTemplateRendererGateway):
    def __init__(self, html: str = "<html>digest</html>") -> None:
        self._html = html
        self.calls: list[DigestEmail] = []

    async def render(self, digest: DigestEmail) -> str:
        self.calls.append(digest)
        return self._html


class FakeMailer(MailerGateway):
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, to: str, subject: str, html: str) -> None:
        self.sent.append({"to": to, "subject": subject, "html": html})


def _make_digest(mission_count: int = 0) -> DigestEmail:
    return DigestEmail(
        user_id=uuid4(),
        user_email="jean@example.com",
        user_name="Jean Dupont",
        subject="Mission Radar AI — 3 nouvelles missions aujourd'hui",
        missions=(),
    )


def _make_use_case(
    html: str = "<html>ok</html>",
) -> tuple[SendDigest, FakeRenderer, FakeMailer]:
    renderer = FakeRenderer(html)
    mailer = FakeMailer()
    uc = SendDigest(renderer=renderer, mailer=mailer)
    return uc, renderer, mailer


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_calls_renderer_with_digest():
    uc, renderer, _ = _make_use_case()
    digest = _make_digest()

    await uc.execute(digest)

    assert len(renderer.calls) == 1
    assert renderer.calls[0] is digest


async def test_calls_mailer_with_correct_to():
    uc, _, mailer = _make_use_case()
    digest = _make_digest()

    await uc.execute(digest)

    assert len(mailer.sent) == 1
    assert mailer.sent[0]["to"] == digest.user_email


async def test_calls_mailer_with_correct_subject():
    uc, _, mailer = _make_use_case()
    digest = _make_digest()

    await uc.execute(digest)

    assert mailer.sent[0]["subject"] == digest.subject


async def test_html_from_renderer_passed_to_mailer():
    expected_html = "<html><body>custom</body></html>"
    uc, _, mailer = _make_use_case(html=expected_html)
    digest = _make_digest()

    await uc.execute(digest)

    assert mailer.sent[0]["html"] == expected_html


async def test_renderer_called_before_mailer():
    """Renderer must produce HTML before mailer is called — order matters."""
    call_order: list[str] = []

    class TrackingRenderer(EmailTemplateRendererGateway):
        async def render(self, digest: DigestEmail) -> str:
            call_order.append("render")
            return "<html/>"

    class TrackingMailer(MailerGateway):
        async def send(self, to: str, subject: str, html: str) -> None:
            call_order.append("send")

    uc = SendDigest(renderer=TrackingRenderer(), mailer=TrackingMailer())
    await uc.execute(_make_digest())

    assert call_order == ["render", "send"]


async def test_renderer_exception_propagates():
    class FailingRenderer(EmailTemplateRendererGateway):
        async def render(self, digest: DigestEmail) -> str:
            raise RuntimeError("template error")

    uc = SendDigest(renderer=FailingRenderer(), mailer=FakeMailer())

    with pytest.raises(RuntimeError, match="template error"):
        await uc.execute(_make_digest())
