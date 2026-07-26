from src.Domain.Entity.digest_email import DigestEmail
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.ValueObject.digest_mission import DigestMission


class DigestGenerator:
    """Builds a DigestEmail from a user profile and pre-selected DigestMission objects.

    Receives DigestMissions already assembled by the Use Case — fully decoupled
    from persistence and selection logic.
    """

    def generate(
        self,
        user: UserProfile,
        missions: list[DigestMission],
    ) -> DigestEmail:
        return DigestEmail(
            user_id=user.id,
            user_email=user.email,
            user_name=user.full_name,
            subject=self._build_subject(len(missions)),
            missions=tuple(missions),
        )

    def _build_subject(self, count: int) -> str:
        if count == 0:
            return "Mission Radar AI — Aucune nouvelle mission aujourd'hui"
        adj = "nouvelles" if count > 1 else "nouvelle"
        noun = "missions" if count > 1 else "mission"
        return f"Mission Radar AI — {count} {adj} {noun} aujourd'hui"
