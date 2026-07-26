import logging
import os
import tempfile
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.DTO.cv_profile import CVProfile
from src.Application.DTO.process_cv_command import ProcessCVCommand
from src.Application.DTO.save_profile_command import SaveProfileCommand
from src.Application.UseCase.process_cv import ProcessCV
from src.Application.UseCase.save_profile import SaveProfile
from src.Application.UseCase.update_search_queries import UpdateSearchQueries, UpdateSearchQueriesCommand
from src.Domain.Exception.domain_exceptions import InvalidContractTypeError, InvalidEmailError, InvalidRemoteModeError
from src.Infrastructure.Api.Dependency.dependencies import (
    get_authenticated_identity,
    get_process_cv,
    get_save_profile,
    get_update_search_queries,
)
from src.Infrastructure.External.CV.exceptions import CVExtractionError
from src.Infrastructure.External.LLM.exceptions import LLMExtractionError, LLMResponseFormatError
from src.Infrastructure.Persistence.exceptions import DatabaseError

logger = logging.getLogger(__name__)

MAX_CV_SIZE_MB = 10

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class CVProfileResponse(BaseModel):
    email: str
    full_name: str
    title: str
    years_experience: int
    preferred_contract_type: str
    target_tjm: float
    preferred_remote_mode: str
    location: Optional[str]
    skills: list[str]
    availability: str


class OnboardingDraftResponse(BaseModel):
    cv_profile: CVProfileResponse
    cv_raw_text: str


class CVProfileInput(BaseModel):
    email: str
    full_name: str
    title: str
    years_experience: int
    preferred_contract_type: str
    target_tjm: float
    preferred_remote_mode: str
    location: Optional[str] = None
    skills: list[str]
    availability: datetime


class SaveProfileRequest(BaseModel):
    cv_profile: CVProfileInput
    cv_raw_text: str


class SaveProfileResponse(BaseModel):
    profile_id: str
    email: str
    status: str
    search_queries: list[str] = []
    search_queries_count: int = 0


class UpdateSearchQueriesRequest(BaseModel):
    queries: list[str]


class UpdateSearchQueriesResponse(BaseModel):
    profile_id: str
    count: int


@router.post("/cv", response_model=OnboardingDraftResponse, status_code=200)
async def upload_cv(
    email: str = Form(...),
    file: UploadFile = File(...),
    process_cv: ProcessCV = Depends(get_process_cv),
    _identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> OnboardingDraftResponse:
    """Upload a CV PDF and return an extracted draft profile for user review.

    Requires a valid Auth0 bearer token (authenticated but not yet linked to a
    UserProfile — that's exactly the onboarding case). `email` still comes from
    the form rather than the token: the token only carries it once the Auth0
    Action from Phase 10.4.1 is deployed.

    ≈ Symfony Controller action with injected Application Service.
    - Form(...) ≈ Request::request->get('email')
    - UploadFile ≈ Symfony UploadedFile
    - Depends(get_process_cv) ≈ Service Container autowiring
    """
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=422, detail="File is empty")

    if len(content) > MAX_CV_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_CV_SIZE_MB} MB limit")

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        draft = await process_cv.execute(ProcessCVCommand(email=email, file_path=tmp_path))

    except CVExtractionError:
        raise HTTPException(status_code=400, detail="CV extraction failed — ensure the file is a valid readable PDF")
    except LLMExtractionError as e:
        logger.error("Groq API failure during CV extraction: %s", e.reason)
        raise HTTPException(status_code=502, detail="LLM service temporarily unavailable, please try again later")
    except LLMResponseFormatError as e:
        logger.error("LLM response parsing failed during CV extraction: %s", e.reason)
        raise HTTPException(status_code=502, detail="LLM service temporarily unavailable, please try again later")
    except InvalidEmailError:
        raise HTTPException(status_code=422, detail="Invalid email format")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    profile = draft.profile
    return OnboardingDraftResponse(
        cv_profile=CVProfileResponse(
            email=email,
            full_name=profile.full_name,
            title=profile.title,
            years_experience=profile.years_experience,
            preferred_contract_type=profile.preferred_contract_type,
            target_tjm=profile.target_tjm,
            preferred_remote_mode=profile.preferred_remote_mode,
            location=profile.location,
            skills=list(profile.skills),
            availability=profile.availability.isoformat(),
        ),
        cv_raw_text=draft.cv_raw_text,
    )


@router.post("/profile", response_model=SaveProfileResponse, status_code=200)
async def save_profile(
    body: SaveProfileRequest,
    save_profile_uc: SaveProfile = Depends(get_save_profile),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> SaveProfileResponse:
    """Persist a user-confirmed profile with embedding and derived search queries.

    SaveProfile Use Case orchestre en interne : embedding → UserProfile upsert
    → ExternalIdentity link (si absent) → HeuristicSearchQueryGenerator (Domain
    Service) → SearchQuery DELETE + INSERT.
    """
    p = body.cv_profile
    try:
        result = await save_profile_uc.execute(
            SaveProfileCommand(
                cv_profile=CVProfile(
                    email=p.email,
                    full_name=p.full_name,
                    title=p.title,
                    years_experience=p.years_experience,
                    preferred_contract_type=p.preferred_contract_type,
                    target_tjm=p.target_tjm,
                    preferred_remote_mode=p.preferred_remote_mode,
                    skills=tuple(p.skills),
                    availability=p.availability,
                    location=p.location,
                ),
                cv_raw_text=body.cv_raw_text,
                identity=identity,
            )
        )
    except InvalidEmailError:
        raise HTTPException(status_code=422, detail="Invalid email format")
    except (InvalidContractTypeError, InvalidRemoteModeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Database error while saving profile")

    return SaveProfileResponse(
        profile_id=str(result.profile_id),
        email=result.email,
        status=result.status,
        search_queries=result.search_queries,
        search_queries_count=result.search_queries_count,
    )


@router.put(
    "/profile/{profile_id}/search-queries",
    response_model=UpdateSearchQueriesResponse,
    status_code=200,
)
async def update_search_queries(
    profile_id: str,
    body: UpdateSearchQueriesRequest,
    update_uc: UpdateSearchQueries = Depends(get_update_search_queries),
) -> UpdateSearchQueriesResponse:
    """Replace all search queries for a profile with the user-edited list."""
    from uuid import UUID

    try:
        pid = UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid profile_id format")

    count = await update_uc.execute(
        UpdateSearchQueriesCommand(profile_id=pid, queries=body.queries)
    )
    return UpdateSearchQueriesResponse(profile_id=profile_id, count=count)
