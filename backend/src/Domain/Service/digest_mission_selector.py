from src.Domain.Entity.mission_match import MissionMatch

TOP_MISSIONS: int = 10


class DigestMissionSelector:
    """Selects the top-N missions from today's matches for inclusion in the digest.

    Sorting and limiting are the only responsibilities — no enrichment, no persistence.
    Change selection criteria here without touching DigestGenerator.
    """

    def select(
        self,
        matches: list[MissionMatch],
        max_count: int = TOP_MISSIONS,
    ) -> list[MissionMatch]:
        return sorted(matches, key=lambda m: m.final_score, reverse=True)[:max_count]
