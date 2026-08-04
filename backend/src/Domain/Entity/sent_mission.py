from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class SentMission:
    """Trace qu'une mission (AnalyzedPost) a déjà été envoyée à un utilisateur dans un digest.

    Base de l'exclusion définitive dans DigestMissionSelector : une mission envoyée une
    fois à un user n'est plus jamais resélectionnée pour ce même user. Clé stable sur
    analyzed_post_id — contrairement à MissionMatch, supprimé/recréé en entier à chaque
    run de MatchMissions, un flag "sent" dessus serait perdu au run suivant.
    """

    user_profile_id: UUID
    analyzed_post_id: UUID
    id: UUID = field(default_factory=uuid4)
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))
