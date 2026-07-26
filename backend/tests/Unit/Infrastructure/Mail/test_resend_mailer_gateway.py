"""Unit tests for ResendMailerGateway — Resend SDK fully mocked via _client injection."""
import pytest

from src.Infrastructure.External.Mailer.exceptions import MailerSendError
from src.Infrastructure.External.Mailer.resend_mailer_gateway import ResendMailerGateway


# ---------------------------------------------------------------------------
# Fake Resend client
# ---------------------------------------------------------------------------


class _FakeResendEmails:
    def __init__(self, should_raise: bool = False) -> None:
        self.sent: list[dict] = []
        self._should_raise = should_raise

    def send(self, params: dict) -> dict:
        if self._should_raise:
            raise RuntimeError("Resend API error")
        self.sent.append(params)
        return {"id": "fake-email-id"}


def _make_gateway(
    api_key: str = "re_test_key",
    from_email: str = "noreply@mission-radar.ai",
    from_name: str = "Mission Radar AI",
    should_raise: bool = False,
) -> tuple[ResendMailerGateway, _FakeResendEmails]:
    client = _FakeResendEmails(should_raise=should_raise)
    gw = ResendMailerGateway(
        api_key=api_key,
        from_email=from_email,
        from_name=from_name,
        _client=client,
    )
    return gw, client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_send_calls_client_send():
    gw, client = _make_gateway()
    await gw.send(to="user@example.com", subject="Test subject", html="<html/>")
    assert len(client.sent) == 1


async def test_send_passes_correct_to():
    gw, client = _make_gateway()
    await gw.send(to="user@example.com", subject="Sub", html="<html/>")
    assert client.sent[0]["to"] == ["user@example.com"]


async def test_send_passes_correct_subject():
    gw, client = _make_gateway()
    await gw.send(to="u@e.com", subject="Mission Radar AI — 5 missions", html="<html/>")
    assert client.sent[0]["subject"] == "Mission Radar AI — 5 missions"


async def test_send_passes_correct_html():
    html = "<html><body>hello</body></html>"
    gw, client = _make_gateway()
    await gw.send(to="u@e.com", subject="Sub", html=html)
    assert client.sent[0]["html"] == html


async def test_from_address_formatted_correctly():
    gw, client = _make_gateway(from_name="Mission Radar AI", from_email="noreply@mr.ai")
    await gw.send(to="u@e.com", subject="Sub", html="<html/>")
    assert client.sent[0]["from"] == "Mission Radar AI <noreply@mr.ai>"


async def test_sdk_error_raises_mailer_send_error():
    gw, _ = _make_gateway(should_raise=True)
    with pytest.raises(MailerSendError):
        await gw.send(to="u@e.com", subject="Sub", html="<html/>")


async def test_sdk_error_message_preserved():
    gw, _ = _make_gateway(should_raise=True)
    with pytest.raises(MailerSendError) as exc_info:
        await gw.send(to="u@e.com", subject="Sub", html="<html/>")
    assert "Resend API error" in str(exc_info.value)


async def test_send_called_once_per_execute():
    gw, client = _make_gateway()
    await gw.send(to="a@b.com", subject="S1", html="<html/>")
    await gw.send(to="c@d.com", subject="S2", html="<html/>")
    assert len(client.sent) == 2
