from typing import Any
from uuid import UUID

from src.Application.DTO.activity_event import ActivityEvent, ActivityHistoryPage
from src.Application.DTO.get_activity_history_query import GetActivityHistoryQuery
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.digest_history import DigestHistory, DigestStatus
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.digest_history_repository import DigestHistoryRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository

_DESCRIPTION_LENGTH = 200


class GetActivityHistory:
    """Returns a paginated activity timeline for a user, sorted newest first.

    Merges MISSION_MATCH and DAILY_DIGEST events from their respective repositories.
    """

    def __init__(
        self,
        mission_match_repository: MissionMatchRepository,
        analyzed_post_repository: AnalyzedPostRepository,
        raw_post_repository: RawPostRepository,
        digest_history_repository: DigestHistoryRepository,
    ) -> None:
        self._mission_match_repository = mission_match_repository
        self._analyzed_post_repository = analyzed_post_repository
        self._raw_post_repository = raw_post_repository
        self._digest_history_repository = digest_history_repository

    async def execute(self, query: GetActivityHistoryQuery) -> ActivityHistoryPage:
        all_matches = await self._mission_match_repository.get_by_user(query.user_profile_id)
        all_digests = await self._digest_history_repository.find_by_user(query.user_profile_id)

        # Unified list of (datetime, type_str, entity)
        raw: list[tuple[Any, str, Any]] = (
            [(m.created_at, "MISSION_MATCH", m) for m in all_matches]
            + [(d.sent_at, "DAILY_DIGEST", d) for d in all_digests]
        )
        raw.sort(key=lambda x: x[0], reverse=True)

        total = len(raw)
        page = raw[query.offset : query.offset + query.limit]

        if not page:
            return ActivityHistoryPage(items=[], total=total, limit=query.limit, offset=query.offset)

        # Enrich MISSION_MATCH items only (DAILY_DIGEST needs no extra DB lookup)
        mission_matches_on_page = [e[2] for e in page if e[1] == "MISSION_MATCH"]

        analyzed_map: dict[UUID, AnalyzedPost] = {}
        raw_map: dict[UUID, RawPost] = {}

        if mission_matches_on_page:
            analyzed_posts = await self._analyzed_post_repository.find_by_ids(
                [m.analyzed_post_id for m in mission_matches_on_page]
            )
            analyzed_map = {ap.id: ap for ap in analyzed_posts}

            raw_posts = await self._raw_post_repository.find_by_ids(
                [ap.raw_post_id for ap in analyzed_posts]
            )
            raw_map = {rp.id: rp for rp in raw_posts}

        items: list[ActivityEvent] = []
        for _, event_type, entity in page:
            if event_type == "MISSION_MATCH":
                analyzed = analyzed_map.get(entity.analyzed_post_id)
                if analyzed is None:
                    continue
                raw_post = raw_map.get(analyzed.raw_post_id)
                if raw_post is None:
                    continue
                title = analyzed.title or analyzed.company or f"Mission de {raw_post.author_name}"
                description = (analyzed.summary or raw_post.content)[:_DESCRIPTION_LENGTH]
                items.append(
                    ActivityEvent(
                        type="MISSION_MATCH",
                        occurred_at=entity.created_at,
                        title=title,
                        description=description,
                        score=round(entity.final_score * 100),
                        mission_match_id=entity.id,
                    )
                )
            else:
                digest: DigestHistory = entity
                if digest.status == DigestStatus.SENT:
                    items.append(
                        ActivityEvent(
                            type="DAILY_DIGEST",
                            occurred_at=digest.sent_at,
                            title="Daily Digest envoyé",
                            description=f"{digest.missions_count} missions",
                            score=digest.missions_count,
                            digest_history_id=digest.id,
                        )
                    )
                else:
                    items.append(
                        ActivityEvent(
                            type="DAILY_DIGEST",
                            occurred_at=digest.sent_at,
                            title="Daily Digest",
                            description=digest.error_message or "Erreur lors de l'envoi",
                            score=-1,
                            digest_history_id=digest.id,
                        )
                    )

        return ActivityHistoryPage(items=items, total=total, limit=query.limit, offset=query.offset)
