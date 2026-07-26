from functools import lru_cache
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.Exception.application_error import UserProfileNotLinkedError
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Application.Gateway.token_verifier_gateway import TokenVerifierGateway
from src.Application.UseCase.get_activity_history import GetActivityHistory
from src.Application.UseCase.get_dashboard_summary import GetDashboardSummary
from src.Application.UseCase.get_mission_details import GetMissionDetails
from src.Application.UseCase.get_mission_history import GetMissionHistory
from src.Application.UseCase.get_today_missions import GetTodayMissions
from src.Application.UseCase.get_user_profile import GetUserProfile
from src.Application.UseCase.lookup_user_by_email import LookupUserByEmail
from src.Application.UseCase.process_cv import ProcessCV
from src.Application.UseCase.resolve_identity import ResolveIdentity
from src.Application.UseCase.save_profile import SaveProfile
from src.Application.UseCase.update_search_queries import UpdateSearchQueries
from src.Infrastructure.Config.database import get_db_session
from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Auth0.auth0_token_verifier_gateway import Auth0TokenVerifierGateway
from src.Infrastructure.External.Auth0.exceptions import TokenVerificationError
from src.Infrastructure.External.CV.pdfminer_cv_extractor_gateway import PdfMinerCVExtractorGateway
from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import SentenceTransformerEmbeddingGateway
from src.Infrastructure.External.LLM.groq_llm_gateway import GroqLLMGateway
from src.Infrastructure.External.Observability.langfuse.factory import get_langfuse_tracer
from src.Infrastructure.Persistence.Repository.analyzed_post_repository import SqlAlchemyAnalyzedPostRepository
from src.Infrastructure.Persistence.Repository.digest_history_repository import SqlAlchemyDigestHistoryRepository
from src.Infrastructure.Persistence.Repository.external_identity_repository import (
    SqlAlchemyExternalIdentityRepository,
)
from src.Infrastructure.Persistence.Repository.mission_match_repository import SqlAlchemyMissionMatchRepository
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository
from src.Infrastructure.Persistence.Repository.search_query_repository import SqlAlchemySearchQueryRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository


# Lazy singletons via lru_cache — instantiated on first real request, not at import time.
# This avoids crashing when GROQ_API_KEY is absent (e.g. during test collection).
# ≈ Symfony services with shared: true, but evaluated lazily rather than at container build.


@lru_cache(maxsize=1)
def _get_llm_gateway() -> LLMGateway:
    if settings.LLM_PROVIDER == "groq":
        return GroqLLMGateway(api_key=settings.GROQ_API_KEY, tracer=get_langfuse_tracer())
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER!r}")


@lru_cache(maxsize=1)
def _get_cv_extractor_gateway() -> PdfMinerCVExtractorGateway:
    return PdfMinerCVExtractorGateway()


async def get_user_profile_repository(
    db: AsyncSession = Depends(get_db_session),
) -> SqlAlchemyUserProfileRepository:
    return SqlAlchemyUserProfileRepository(db)


@lru_cache(maxsize=1)
def _get_token_verifier_gateway() -> TokenVerifierGateway:
    return Auth0TokenVerifierGateway(domain=settings.AUTH0_DOMAIN)


_bearer_scheme = HTTPBearer()


async def get_authenticated_identity(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> AuthenticatedIdentity:
    try:
        return await _get_token_verifier_gateway().verify(
            credentials.credentials, expected_audience=settings.AUTH0_API_AUDIENCE
        )
    except TokenVerificationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def get_current_user_profile_id(
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    db: AsyncSession = Depends(get_db_session),
) -> UUID:
    resolve_identity = ResolveIdentity(
        external_identity_repository=SqlAlchemyExternalIdentityRepository(db)
    )
    try:
        return await resolve_identity.execute(identity)
    except UserProfileNotLinkedError as exc:
        raise HTTPException(status_code=404, detail="profile_not_linked") from exc


async def get_user_profile_use_case(
    db: AsyncSession = Depends(get_db_session),
) -> GetUserProfile:
    return GetUserProfile(user_profile_repository=SqlAlchemyUserProfileRepository(db))


@lru_cache(maxsize=1)
def _get_embedding_gateway() -> SentenceTransformerEmbeddingGateway:
    return SentenceTransformerEmbeddingGateway()


def get_process_cv() -> ProcessCV:
    return ProcessCV(
        cv_extractor=_get_cv_extractor_gateway(),
        llm=_get_llm_gateway(),
    )


async def get_save_profile(
    db: AsyncSession = Depends(get_db_session),
) -> SaveProfile:
    return SaveProfile(
        user_profile_repo=SqlAlchemyUserProfileRepository(db),
        embedding_gateway=_get_embedding_gateway(),
        search_query_repo=SqlAlchemySearchQueryRepository(db),
        llm_gateway=_get_llm_gateway(),
        external_identity_repo=SqlAlchemyExternalIdentityRepository(db),
    )


async def get_update_search_queries(
    db: AsyncSession = Depends(get_db_session),
) -> UpdateSearchQueries:
    return UpdateSearchQueries(
        search_query_repo=SqlAlchemySearchQueryRepository(db),
    )


async def get_today_missions_use_case(
    db: AsyncSession = Depends(get_db_session),
) -> GetTodayMissions:
    return GetTodayMissions(
        mission_match_repository=SqlAlchemyMissionMatchRepository(db),
        analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(db),
        raw_post_repository=SqlAlchemyRawPostRepository(db),
    )


async def get_mission_details_use_case(
    db: AsyncSession = Depends(get_db_session),
) -> GetMissionDetails:
    return GetMissionDetails(
        mission_match_repository=SqlAlchemyMissionMatchRepository(db),
        analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(db),
        raw_post_repository=SqlAlchemyRawPostRepository(db),
        user_profile_repository=SqlAlchemyUserProfileRepository(db),
    )


async def get_mission_history_use_case(
    db: AsyncSession = Depends(get_db_session),
) -> GetMissionHistory:
    return GetMissionHistory(
        mission_match_repository=SqlAlchemyMissionMatchRepository(db),
        analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(db),
        raw_post_repository=SqlAlchemyRawPostRepository(db),
    )


async def get_activity_history_use_case(
    db: AsyncSession = Depends(get_db_session),
) -> GetActivityHistory:
    return GetActivityHistory(
        mission_match_repository=SqlAlchemyMissionMatchRepository(db),
        analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(db),
        raw_post_repository=SqlAlchemyRawPostRepository(db),
        digest_history_repository=SqlAlchemyDigestHistoryRepository(db),
    )


async def get_dashboard_summary_use_case(
    db: AsyncSession = Depends(get_db_session),
) -> GetDashboardSummary:
    return GetDashboardSummary(
        mission_match_repository=SqlAlchemyMissionMatchRepository(db),
        pipeline_run_repository=SqlAlchemyPipelineRunRepository(db),
    )


async def get_lookup_user_by_email(
    db: AsyncSession = Depends(get_db_session),
) -> LookupUserByEmail:
    return LookupUserByEmail(repository=SqlAlchemyUserProfileRepository(db))
