from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.Infrastructure.Persistence.SQLAlchemy.base import Base


class SentMissionModel(Base):
    """Trace qu'une mission (AnalyzedPost) a déjà été envoyée à un utilisateur dans un digest.

    Table de liaison append-only : jamais mise à jour, seulement créée. Sert de base à
    l'exclusion définitive côté DigestMissionSelector. Pas de TimestampedMixin (jamais
    modifiée après création).
    """

    __tablename__ = "sent_missions"
    __table_args__ = (
        UniqueConstraint("user_profile_id", "analyzed_post_id", name="uq_sent_missions_user_analyzed_post"),
        Index("ix_sent_missions_user_profile_id", "user_profile_id"),
        Index("ix_sent_missions_analyzed_post_id", "analyzed_post_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    analyzed_post_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analyzed_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
