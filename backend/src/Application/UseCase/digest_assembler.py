from uuid import UUID

from src.Application.Exception.application_error import UserProfileNotFoundError
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.digest_email import DigestEmail
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.Service.digest_generator import DigestGenerator
from src.Domain.Service.digest_mission_selector import DigestMissionSelector
from src.Domain.ValueObject.digest_mission import DigestMission
from src.Domain.ValueObject.remote_mode import RemoteMode


class DigestAssembler:
    """Assembles a DigestEmail from DB data for a given user by batch-fetching
    MissionMatch/AnalyzedPost/RawPost and delegating to the Domain selector/generator.
    Shared by every Use Case that needs to build a digest (GenerateDigest, SendDigestNow)
    to avoid duplicating this fetch-and-build logic — same pattern as TodayMissionAssembler."""

    def __init__(
        self,
        user_profile_repository: UserProfileRepository,
        mission_match_repository: MissionMatchRepository,
        analyzed_post_repository: AnalyzedPostRepository,
        raw_post_repository: RawPostRepository,
        selector: DigestMissionSelector,
        generator: DigestGenerator,
    ) -> None:
        self._user_profile_repository = user_profile_repository
        self._mission_match_repository = mission_match_repository
        self._analyzed_post_repository = analyzed_post_repository
        self._raw_post_repository = raw_post_repository
        self._selector = selector
        self._generator = generator

    async def assemble(self, user_id: UUID) -> DigestEmail:
        user = await self._user_profile_repository.get_by_id(user_id)
        if user is None:
            raise UserProfileNotFoundError(f"UserProfile {user_id} not found")

        matches = await self._mission_match_repository.get_by_user(user_id)
        selected = self._selector.select(matches)

        if not selected:
            return self._generator.generate(user, [])

        analyzed_post_ids = [m.analyzed_post_id for m in selected]
        analyzed_posts = await self._analyzed_post_repository.find_by_ids(analyzed_post_ids)
        analyzed_map: dict[UUID, AnalyzedPost] = {ap.id: ap for ap in analyzed_posts}

        raw_post_ids = [ap.raw_post_id for ap in analyzed_posts]
        raw_posts = await self._raw_post_repository.find_by_ids(raw_post_ids)
        raw_map: dict[UUID, RawPost] = {rp.id: rp for rp in raw_posts}

        digest_missions: list[DigestMission] = []
        for match in selected:
            analyzed = analyzed_map.get(match.analyzed_post_id)
            if analyzed is None:
                continue
            raw = raw_map.get(analyzed.raw_post_id)

            digest_missions.append(
                DigestMission(
                    mission_match_id=match.id,
                    analyzed_post_id=analyzed.id,
                    final_score=match.final_score,
                    summary=analyzed.summary,
                    title=analyzed.title,
                    company=analyzed.company,
                    detected_stack=analyzed.detected_stack,
                    detected_remote_mode=analyzed.detected_remote_mode
                    if analyzed.detected_remote_mode is not None
                    else RemoteMode.UNKNOWN,
                    detected_tjm=analyzed.detected_tjm,
                    post_url=raw.post_url if raw is not None else None,
                )
            )

        return self._generator.generate(user, digest_missions)
