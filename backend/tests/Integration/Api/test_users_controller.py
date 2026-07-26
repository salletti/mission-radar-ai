"""Integration tests for /api/users endpoints — fake use cases, no DB."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from main import app
from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.DTO.lookup_user_by_email_query import LookupUserByEmailQuery
from src.Application.DTO.lookup_user_by_email_result import LookupUserByEmailResult
from src.Application.DTO.user_profile import UserProfile
from src.Application.UseCase.get_user_profile import GetUserProfile
from src.Application.UseCase.lookup_user_by_email import LookupUserByEmail
from src.Infrastructure.Api.Dependency.dependencies import (
    get_authenticated_identity,
    get_current_user_profile_id,
    get_lookup_user_by_email,
    get_user_profile_use_case,
)

_KNOWN_ID = uuid4()
_FAKE_IDENTITY = AuthenticatedIdentity(provider="auth0", subject="auth0|test-user")


class _FakeLookupFound(LookupUserByEmail):
    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def execute(self, query: LookupUserByEmailQuery) -> LookupUserByEmailResult:
        return LookupUserByEmailResult(exists=True, user_id=str(_KNOWN_ID))


class _FakeLookupNotFound(LookupUserByEmail):
    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def execute(self, query: LookupUserByEmailQuery) -> LookupUserByEmailResult:
        return LookupUserByEmailResult(exists=False, user_id=None)


@pytest_asyncio.fixture
async def api_client_found() -> AsyncClient:
    app.dependency_overrides[get_lookup_user_by_email] = lambda: _FakeLookupFound()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_not_found() -> AsyncClient:
    app.dependency_overrides[get_lookup_user_by_email] = lambda: _FakeLookupNotFound()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — email existant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_known_email_returns_200(api_client_found: AsyncClient) -> None:
    response = await api_client_found.post(
        "/api/users/lookup-by-email",
        json={"email": "ada@example.com"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_known_email_returns_exists_true(api_client_found: AsyncClient) -> None:
    response = await api_client_found.post(
        "/api/users/lookup-by-email",
        json={"email": "ada@example.com"},
    )
    data = response.json()
    assert data["exists"] is True
    assert data["user_id"] == str(_KNOWN_ID)


# ---------------------------------------------------------------------------
# Tests — email inconnu
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_email_returns_200(api_client_not_found: AsyncClient) -> None:
    response = await api_client_not_found.post(
        "/api/users/lookup-by-email",
        json={"email": "unknown@example.com"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unknown_email_returns_exists_false(api_client_not_found: AsyncClient) -> None:
    response = await api_client_not_found.post(
        "/api/users/lookup-by-email",
        json={"email": "unknown@example.com"},
    )
    data = response.json()
    assert data["exists"] is False
    assert data["user_id"] is None


# ---------------------------------------------------------------------------
# Tests — validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_email_returns_422(api_client_not_found: AsyncClient) -> None:
    response = await api_client_not_found.post(
        "/api/users/lookup-by-email",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_empty_email_returns_422(api_client_not_found: AsyncClient) -> None:
    response = await api_client_not_found.post(
        "/api/users/lookup-by-email",
        json={"email": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_email_field_returns_422(api_client_not_found: AsyncClient) -> None:
    response = await api_client_not_found.post(
        "/api/users/lookup-by-email",
        json={},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — GET /api/users/me
# ---------------------------------------------------------------------------

_FAKE_PROFILE = UserProfile(
    id=_KNOWN_ID,
    email="ada@example.com",
    full_name="Ada Lovelace",
    title="Senior Python Engineer",
    years_experience=10,
    preferred_contract_type="freelance",
    target_tjm=700.0,
    preferred_remote_mode="full_remote",
    skills=("python", "fastapi"),
    availability=datetime(2026, 9, 1, tzinfo=timezone.utc),
    location="Paris",
)


class _FakeGetUserProfile(GetUserProfile):
    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def execute(self, user_profile_id) -> UserProfile:  # type: ignore[override]
        return _FAKE_PROFILE


def _raise_profile_not_linked():
    raise HTTPException(status_code=404, detail="profile_not_linked")


@pytest_asyncio.fixture
async def api_client_me_linked() -> AsyncClient:
    app.dependency_overrides[get_authenticated_identity] = lambda: _FAKE_IDENTITY
    app.dependency_overrides[get_current_user_profile_id] = lambda: _KNOWN_ID
    app.dependency_overrides[get_user_profile_use_case] = lambda: _FakeGetUserProfile()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_me_not_linked() -> AsyncClient:
    app.dependency_overrides[get_authenticated_identity] = lambda: _FAKE_IDENTITY
    app.dependency_overrides[get_current_user_profile_id] = _raise_profile_not_linked
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_me_unauthenticated() -> AsyncClient:
    """No dependency overrides at all — exercises the real auth dependency chain."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_me_returns_200_when_linked(api_client_me_linked: AsyncClient) -> None:
    response = await api_client_me_linked.get("/api/users/me")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_me_response_contains_profile_id_and_email(api_client_me_linked: AsyncClient) -> None:
    response = await api_client_me_linked.get("/api/users/me")
    data = response.json()
    assert data["profile_id"] == str(_KNOWN_ID)
    assert data["email"] == "ada@example.com"


@pytest.mark.asyncio
async def test_me_returns_404_profile_not_linked_when_unlinked(
    api_client_me_not_linked: AsyncClient,
) -> None:
    response = await api_client_me_not_linked.get("/api/users/me")
    assert response.status_code == 404
    assert response.json()["detail"] == "profile_not_linked"


@pytest.mark.asyncio
async def test_me_returns_401_without_auth(api_client_me_unauthenticated: AsyncClient) -> None:
    response = await api_client_me_unauthenticated.get("/api/users/me")
    assert response.status_code == 401
