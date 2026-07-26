"""Integration tests for POST /api/onboarding/cv.

Uses fake gateways (no Groq calls, no DB writes) — verifies the Draft → Review pattern.

Parallèle Symfony : KernelTestCase + overrideService() pour isoler l'Application Service
sans toucher les couches infrastructure externes.
"""
import pytest
from httpx import AsyncClient

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF"


@pytest.mark.asyncio
async def test_upload_cv_valid_returns_200(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/onboarding/cv",
        data={"email": "user@example.com"},
        files={"file": ("cv.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_upload_cv_response_structure(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/onboarding/cv",
        data={"email": "user@example.com"},
        files={"file": ("cv.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    data = response.json()
    assert "cv_profile" in data
    assert "cv_raw_text" in data


@pytest.mark.asyncio
async def test_upload_cv_returns_cv_raw_text(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/onboarding/cv",
        data={"email": "user@example.com"},
        files={"file": ("cv.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    data = response.json()
    assert data["cv_raw_text"] == "fake cv text"


@pytest.mark.asyncio
async def test_upload_cv_valid_response_contains_expected_fields(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/onboarding/cv",
        data={"email": "user@example.com"},
        files={"file": ("cv.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    profile = response.json()["cv_profile"]
    assert profile["email"] == "user@example.com"
    assert profile["full_name"] == "Ada Lovelace"
    assert profile["title"] == "Senior Python Engineer"
    assert profile["years_experience"] == 10
    assert profile["preferred_contract_type"] == "freelance"
    assert profile["target_tjm"] == 700.0
    assert profile["preferred_remote_mode"] == "full_remote"
    assert "python" in profile["skills"]
    assert "availability" in profile


@pytest.mark.asyncio
async def test_upload_cv_does_not_contain_profile_id(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/onboarding/cv",
        data={"email": "user@example.com"},
        files={"file": ("cv.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    data = response.json()
    assert "profile_id" not in data
    assert "profile_id" not in data.get("cv_profile", {})


@pytest.mark.asyncio
async def test_upload_cv_non_pdf_rejected(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/onboarding/cv",
        data={"email": "user@example.com"},
        files={"file": ("cv.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_cv_missing_email_rejected(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/onboarding/cv",
        files={"file": ("cv.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_cv_empty_file_rejected(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/onboarding/cv",
        data={"email": "user@example.com"},
        files={"file": ("cv.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 422
