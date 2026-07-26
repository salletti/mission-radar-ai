from uuid import UUID

from src.Application.UseCase.digest_assembler import DigestAssembler
from src.Domain.Entity.digest_email import DigestEmail
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.Service.digest_generator import DigestGenerator
from src.Domain.Service.digest_mission_selector import DigestMissionSelector


class GenerateDigest:
    """Builds a DigestEmail from DB data for a given user.

    Delegates the fetch-and-build work to DigestAssembler (shared with SendDigestNow).
    Does not produce HTML — does not know Resend.
    """

    def __init__(
        self,
        user_profile_repository: UserProfileRepository,
        mission_match_repository: MissionMatchRepository,
        analyzed_post_repository: AnalyzedPostRepository,
        raw_post_repository: RawPostRepository,
        selector: DigestMissionSelector,
        generator: DigestGenerator,
    ) -> None:
        self._assembler = DigestAssembler(
            user_profile_repository=user_profile_repository,
            mission_match_repository=mission_match_repository,
            analyzed_post_repository=analyzed_post_repository,
            raw_post_repository=raw_post_repository,
            selector=selector,
            generator=generator,
        )

    async def execute(self, user_id: UUID) -> DigestEmail:
        return await self._assembler.assemble(user_id)
