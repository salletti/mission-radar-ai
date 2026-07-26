from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID, uuid4

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.DTO.cv_profile import CVProfile
from src.Application.DTO.save_profile_command import SaveProfileCommand
from src.Application.DTO.save_profile_result import SaveProfileResult
from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Domain.Entity.external_identity import ExternalIdentity
from src.Domain.Entity.search_query import SearchQuery
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Exception.domain_exceptions import InvalidSearchQueryError
from src.Domain.Repository.external_identity_repository import ExternalIdentityRepository
from src.Domain.Repository.search_query_repository import SearchQueryRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.Service.heuristic_search_query_generator import HeuristicSearchQueryGenerator
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack

logger = logging.getLogger(__name__)

_MAX_QUERIES = 5


def _build_embed_text(profile: CVProfile, cv_raw_text: str) -> str:
    skills_lines = "\n".join(profile.skills)
    return (
        f"{profile.title}\n\n"
        f"{profile.years_experience} years experience\n\n"
        f"Contract: {profile.preferred_contract_type}\n\n"
        f"Remote: {profile.preferred_remote_mode}\n\n"
        f"Skills:\n{skills_lines}\n\n"
        f"Availability:\n{profile.availability}\n\n"
        f"CV:\n{cv_raw_text}"
    )


class SaveProfile:
    """Persist a user-confirmed profile with its embedding and derived search queries.

    ≈ Application Service Symfony : orchestre Repository + Gateway + Domain Service.
    Génère les SearchQuery via LLMGateway (LLM) avec fallback sur HeuristicSearchQueryGenerator
    (déterministe pur) si le LLM échoue. Persiste via SearchQueryRepository (DELETE + INSERT).
    """

    def __init__(
        self,
        user_profile_repo: UserProfileRepository,
        embedding_gateway: EmbeddingGateway,
        search_query_repo: SearchQueryRepository,
        llm_gateway: LLMGateway,
        external_identity_repo: Optional[ExternalIdentityRepository] = None,
    ) -> None:
        self._repo = user_profile_repo
        self._embedding_gateway = embedding_gateway
        self._search_query_repo = search_query_repo
        self._llm_gateway = llm_gateway
        self._external_identity_repo = external_identity_repo
        self._fallback = HeuristicSearchQueryGenerator()

    async def execute(self, command: SaveProfileCommand) -> SaveProfileResult:
        existing = await self._repo.get_by_email(command.cv_profile.email)
        status = "updated" if existing else "created"

        embed_text = _build_embed_text(command.cv_profile, command.cv_raw_text)
        embedding = await self._embedding_gateway.embed_text(embed_text)

        profile = UserProfile(
            id=existing.id if existing else uuid4(),
            email=command.cv_profile.email,
            full_name=command.cv_profile.full_name,
            title=command.cv_profile.title,
            years_experience=command.cv_profile.years_experience,
            preferred_contract_type=ContractType(command.cv_profile.preferred_contract_type),
            target_tjm=command.cv_profile.target_tjm,
            preferred_remote_mode=RemoteMode(command.cv_profile.preferred_remote_mode),
            skills=Stack(command.cv_profile.skills),
            availability=command.cv_profile.availability,
            location=command.cv_profile.location,
            embedding=embedding,
            cv_raw_text=command.cv_raw_text,
        )

        await self._repo.save(profile)
        await self._link_identity(profile.id, command.identity)

        queries = await self._generate_search_queries(profile)
        await self._search_query_repo.delete_by_profile(profile.id)
        await self._search_query_repo.save_many(queries)

        return SaveProfileResult(
            profile_id=profile.id,
            email=profile.email,
            status=status,
            search_queries=[q.query for q in queries],
        )

    async def _link_identity(self, profile_id: UUID, identity: Optional[AuthenticatedIdentity]) -> None:
        if identity is None or self._external_identity_repo is None:
            return
        existing_link = await self._external_identity_repo.get_by_provider_and_subject(
            identity.provider, identity.subject
        )
        if existing_link is None:
            await self._external_identity_repo.save(
                ExternalIdentity(
                    user_profile_id=profile_id,
                    provider=identity.provider,
                    subject=identity.subject,
                )
            )

    async def _generate_search_queries(self, profile: UserProfile) -> list[SearchQuery]:
        try:
            raw = await self._llm_gateway.generate_search_queries(profile)
            queries = self._build_queries(profile, raw)
            if not queries:
                logger.warning("LLM returned empty queries for profile %s — falling back", profile.id)
                return self._fallback.generate(profile)
            return queries
        except Exception:
            logger.warning(
                "LLM search query generation failed for profile %s — falling back",
                profile.id,
                exc_info=True,
            )
            return self._fallback.generate(profile)

    def _build_queries(self, profile: UserProfile, raw: list[dict]) -> list[SearchQuery]:
        seen: set[str] = set()
        result: list[SearchQuery] = []
        for item in raw:
            if len(result) >= _MAX_QUERIES:
                break
            query_str = (item.get("query") or "").strip()
            if not query_str or query_str in seen:
                continue
            seen.add(query_str)
            try:
                result.append(
                    SearchQuery(
                        user_profile_id=profile.id,
                        query=query_str,
                        source=item.get("source") or "linkedin",
                        limit=item.get("limit") or 50,
                    )
                )
            except InvalidSearchQueryError:
                logger.debug("Skipping invalid search query item: %r", item)
        return result
