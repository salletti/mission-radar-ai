from uuid import UUID

from src.Domain.Entity.mission_match import MissionMatch

TOP_MISSIONS: int = 10


class DigestMissionSelector:
    """Selects the top-N missions from today's matches for inclusion in the digest,
    after excluding any mission already sent to this user in a previous digest.

    Sorting, exclusion and limiting are the only responsibilities — no enrichment,
    no persistence. Change selection criteria here without touching DigestGenerator.
    """

    def select(
        self,
        matches: list[MissionMatch],
        max_count: int = TOP_MISSIONS,
        excluded_analyzed_post_ids: frozenset[UUID] = frozenset(),
    ) -> list[MissionMatch]:
        candidates = [m for m in matches if m.analyzed_post_id not in excluded_analyzed_post_ids]
        return sorted(candidates, key=lambda m: m.final_score, reverse=True)[:max_count]
