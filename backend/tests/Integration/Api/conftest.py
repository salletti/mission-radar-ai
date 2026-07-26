"""Fixtures for API integration tests — fake gateways, no real external services."""
from datetime import datetime, timezone

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app
from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.DTO.cv_profile import CVProfile
from src.Application.Gateway.cv_extractor_gateway import CVExtractorGateway
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Application.UseCase.process_cv import ProcessCV
from src.Infrastructure.Api.Dependency.dependencies import get_authenticated_identity, get_process_cv

FAKE_IDENTITY = AuthenticatedIdentity(provider="auth0", subject="auth0|test-user")

_FAKE_PROFILE = CVProfile(
    email="extracted@example.com",
    full_name="Ada Lovelace",
    title="Senior Python Engineer",
    years_experience=10,
    preferred_contract_type="freelance",
    target_tjm=700.0,
    preferred_remote_mode="full_remote",
    skills=("python", "fastapi", "postgresql"),
    availability=datetime(2026, 9, 1, tzinfo=timezone.utc),
    location="Paris",
)


class _FakeCVExtractor(CVExtractorGateway):
    async def extract_text(self, file_path: str) -> str:
        return "fake cv text"


class _FakeLLMGateway(LLMGateway):
    async def extract_profile_from_cv(self, cv_text: str) -> CVProfile:
        return _FAKE_PROFILE

    async def summarize_mission(self, content: str) -> str:
        return "summary"

    async def generate_search_queries(self, profile) -> list[dict]:  # type: ignore[override]
        return []

    async def analyze_post(self, raw_post) -> "PostAnalysis":  # type: ignore[override]
        raise NotImplementedError


@pytest_asyncio.fixture
async def fake_process_cv() -> ProcessCV:
    return ProcessCV(cv_extractor=_FakeCVExtractor(), llm=_FakeLLMGateway())


@pytest_asyncio.fixture
async def api_client(fake_process_cv: ProcessCV) -> AsyncClient:
    """AsyncClient with dependency override — fake external gateways, no DB."""
    app.dependency_overrides[get_process_cv] = lambda: fake_process_cv
    app.dependency_overrides[get_authenticated_identity] = lambda: FAKE_IDENTITY
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
