"""Integration tests for POST /api/onboarding/profile.

Uses a fake SaveProfile use case — no DB, no embedding model.
Verifies the HTTP contract: status codes, response shape, error mapping.

Parallèle Symfony : KernelTestCase + overrideService(SaveProfile::class, FakeSaveProfile)
"""
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app
from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.DTO.save_profile_command import SaveProfileCommand
from src.Application.DTO.save_profile_result import SaveProfileResult
from src.Application.UseCase.save_profile import SaveProfile
from src.Domain.Exception.domain_exceptions import InvalidContractTypeError
from src.Infrastructure.Api.Dependency.dependencies import get_authenticated_identity, get_save_profile

_PROFILE_ID = uuid4()
_FAKE_IDENTITY = AuthenticatedIdentity(provider="auth0", subject="auth0|test-user")

_VALID_PAYLOAD: dict[str, Any] = {
    "cv_profile": {
        "email": "ada@example.com",
        "full_name": "Ada Lovelace",
        "title": "Senior Python Engineer",
        "years_experience": 10,
        "preferred_contract_type": "freelance",
        "target_tjm": 700.0,
        "preferred_remote_mode": "full_remote",
        "location": "Paris",
        "skills": ["python", "fastapi"],
        "availability": datetime(2026, 9, 1, tzinfo=timezone.utc).isoformat(),
    },
    "cv_raw_text": "Ada Lovelace — Senior Python Engineer...",
}


# ---------------------------------------------------------------------------
# Fake use case
# ---------------------------------------------------------------------------


class _FakeSaveProfile(SaveProfile):
    def __init__(self, status: str = "created") -> None:
        # Skip SaveProfile.__init__() — fakes don't need real repo/gateway
        self._status = status
        self.received_command: SaveProfileCommand | None = None

    async def execute(self, command: SaveProfileCommand) -> SaveProfileResult:
        self.received_command = command
        return SaveProfileResult(
            profile_id=_PROFILE_ID,
            email=command.cv_profile.email,
            status=self._status,
        )


class _FakeSaveProfileRaisesInvalidContract(SaveProfile):
    def __init__(self) -> None:
        pass  # Skip SaveProfile.__init__()

    async def execute(self, command: SaveProfileCommand) -> SaveProfileResult:
        raise InvalidContractTypeError("unknown_type")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def api_client() -> AsyncClient:
    fake = _FakeSaveProfile(status="created")
    app.dependency_overrides[get_save_profile] = lambda: fake
    app.dependency_overrides[get_authenticated_identity] = lambda: _FAKE_IDENTITY
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_updated() -> AsyncClient:
    fake = _FakeSaveProfile(status="updated")
    app.dependency_overrides[get_save_profile] = lambda: fake
    app.dependency_overrides[get_authenticated_identity] = lambda: _FAKE_IDENTITY
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_invalid_contract() -> AsyncClient:
    fake = _FakeSaveProfileRaisesInvalidContract()
    app.dependency_overrides[get_save_profile] = lambda: fake
    app.dependency_overrides[get_authenticated_identity] = lambda: _FAKE_IDENTITY
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_profile_valid_returns_200(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/onboarding/profile", json=_VALID_PAYLOAD)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_save_profile_response_contains_profile_id(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/onboarding/profile", json=_VALID_PAYLOAD)
    data = response.json()
    assert data["profile_id"] == str(_PROFILE_ID)


@pytest.mark.asyncio
async def test_save_profile_response_contains_email(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/onboarding/profile", json=_VALID_PAYLOAD)
    data = response.json()
    assert data["email"] == "ada@example.com"


@pytest.mark.asyncio
async def test_save_profile_status_created(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/onboarding/profile", json=_VALID_PAYLOAD)
    assert response.json()["status"] == "created"


@pytest.mark.asyncio
async def test_save_profile_status_updated(api_client_updated: AsyncClient) -> None:
    response = await api_client_updated.post("/api/onboarding/profile", json=_VALID_PAYLOAD)
    assert response.json()["status"] == "updated"


@pytest.mark.asyncio
async def test_save_profile_missing_body_returns_422(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/onboarding/profile", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_save_profile_invalid_contract_type_returns_400(
    api_client_invalid_contract: AsyncClient,
) -> None:
    response = await api_client_invalid_contract.post(
        "/api/onboarding/profile", json=_VALID_PAYLOAD
    )
    assert response.status_code == 400
