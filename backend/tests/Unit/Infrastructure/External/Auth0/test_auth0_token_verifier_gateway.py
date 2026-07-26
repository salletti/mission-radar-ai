"""Unit tests for Auth0TokenVerifierGateway — tokens signed locally with a
test RSA keypair, PyJWKClient's JWKS fetch monkeypatched. No real Auth0 call."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWKClient

from src.Infrastructure.External.Auth0.auth0_token_verifier_gateway import Auth0TokenVerifierGateway
from src.Infrastructure.External.Auth0.exceptions import TokenVerificationError

_DOMAIN = "test-tenant.auth0.com"
_ISSUER = f"https://{_DOMAIN}/"
_AUDIENCE = "https://api.mission-radar.dev"
_SUBJECT = "auth0|68f0c1f2a1b2c3d4e5f6a7b8"


class _FakeSigningKey:
    def __init__(self, key) -> None:
        self.key = key


def _make_token(
    private_key,
    *,
    audience: str = _AUDIENCE,
    issuer: str = _ISSUER,
    subject: str = _SUBJECT,
    exp_delta: timedelta = timedelta(hours=1),
    extra_claims: dict | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + exp_delta,
        **(extra_claims or {}),
    }
    return jwt.encode(claims, private_key, algorithm="RS256")


def _patch_jwks(monkeypatch, public_key) -> None:
    monkeypatch.setattr(
        PyJWKClient,
        "get_signing_key_from_jwt",
        lambda self, token: _FakeSigningKey(public_key),
    )


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.mark.asyncio
async def test_verify_returns_authenticated_identity_for_valid_token(monkeypatch, rsa_keypair) -> None:
    private_key, public_key = rsa_keypair
    _patch_jwks(monkeypatch, public_key)
    gateway = Auth0TokenVerifierGateway(domain=_DOMAIN)
    token = _make_token(private_key)

    identity = await gateway.verify(token, expected_audience=_AUDIENCE)

    assert identity.provider == "auth0"
    assert identity.subject == _SUBJECT
    assert identity.email is None


@pytest.mark.asyncio
async def test_verify_extracts_namespaced_email_claim(monkeypatch, rsa_keypair) -> None:
    private_key, public_key = rsa_keypair
    _patch_jwks(monkeypatch, public_key)
    gateway = Auth0TokenVerifierGateway(domain=_DOMAIN)
    token = _make_token(
        private_key, extra_claims={"https://mission-radar.dev/email": "ada@example.com"}
    )

    identity = await gateway.verify(token, expected_audience=_AUDIENCE)

    assert identity.email == "ada@example.com"


@pytest.mark.asyncio
async def test_verify_rejects_expired_token(monkeypatch, rsa_keypair) -> None:
    private_key, public_key = rsa_keypair
    _patch_jwks(monkeypatch, public_key)
    gateway = Auth0TokenVerifierGateway(domain=_DOMAIN)
    token = _make_token(private_key, exp_delta=timedelta(minutes=-5))

    with pytest.raises(TokenVerificationError):
        await gateway.verify(token, expected_audience=_AUDIENCE)


@pytest.mark.asyncio
async def test_verify_rejects_wrong_audience(monkeypatch, rsa_keypair) -> None:
    private_key, public_key = rsa_keypair
    _patch_jwks(monkeypatch, public_key)
    gateway = Auth0TokenVerifierGateway(domain=_DOMAIN)
    token = _make_token(private_key, audience="https://someone-else.example.com")

    with pytest.raises(TokenVerificationError):
        await gateway.verify(token, expected_audience=_AUDIENCE)


@pytest.mark.asyncio
async def test_verify_rejects_wrong_issuer(monkeypatch, rsa_keypair) -> None:
    private_key, public_key = rsa_keypair
    _patch_jwks(monkeypatch, public_key)
    gateway = Auth0TokenVerifierGateway(domain=_DOMAIN)
    token = _make_token(private_key, issuer="https://someone-elses-tenant.auth0.com/")

    with pytest.raises(TokenVerificationError):
        await gateway.verify(token, expected_audience=_AUDIENCE)


@pytest.mark.asyncio
async def test_verify_rejects_token_signed_with_a_different_key(monkeypatch, rsa_keypair) -> None:
    private_key, _ = rsa_keypair
    other_public_key = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()
    _patch_jwks(monkeypatch, other_public_key)
    gateway = Auth0TokenVerifierGateway(domain=_DOMAIN)
    token = _make_token(private_key)

    with pytest.raises(TokenVerificationError):
        await gateway.verify(token, expected_audience=_AUDIENCE)
