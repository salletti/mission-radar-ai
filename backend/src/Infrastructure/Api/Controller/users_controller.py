import re
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from src.Application.DTO.lookup_user_by_email_query import LookupUserByEmailQuery
from src.Application.UseCase.get_user_profile import GetUserProfile
from src.Application.UseCase.lookup_user_by_email import LookupUserByEmail
from src.Infrastructure.Api.Dependency.dependencies import (
    get_current_user_profile_id,
    get_lookup_user_by_email,
    get_user_profile_use_case,
)

router = APIRouter(prefix="/api/users", tags=["users"])

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LookupByEmailRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip()
        if not _EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v


class LookupByEmailResponse(BaseModel):
    exists: bool
    user_id: str | None


@router.post("/lookup-by-email", response_model=LookupByEmailResponse, status_code=200)
async def lookup_by_email(
    body: LookupByEmailRequest,
    use_case: LookupUserByEmail = Depends(get_lookup_user_by_email),
) -> LookupByEmailResponse:
    result = await use_case.execute(LookupUserByEmailQuery(email=body.email))
    return LookupByEmailResponse(exists=result.exists, user_id=result.user_id)


class MeResponse(BaseModel):
    profile_id: str
    email: str


@router.get("/me", response_model=MeResponse, status_code=200)
async def get_me(
    user_profile_id: UUID = Depends(get_current_user_profile_id),
    get_user_profile: GetUserProfile = Depends(get_user_profile_use_case),
) -> MeResponse:
    """Returns the profile linked to the authenticated identity.

    get_current_user_profile_id already raises 404 {"detail": "profile_not_linked"}
    when the caller is authenticated but has no linked UserProfile yet — the
    frontend uses that exact response to redirect to onboarding.
    """
    profile = await get_user_profile.execute(user_profile_id)
    return MeResponse(profile_id=str(profile.id), email=profile.email)
