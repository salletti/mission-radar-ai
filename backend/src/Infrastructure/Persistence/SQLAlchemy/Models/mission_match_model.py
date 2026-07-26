from uuid import UUID, uuid4

from sqlalchemy import Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Infrastructure.Persistence.SQLAlchemy.base import Base, TimestampedMixin


class MissionMatchModel(TimestampedMixin, Base):
    """SQLAlchemy model for MissionMatch — weighted scores between a user and a mission."""

    __tablename__ = "mission_matches"
    __table_args__ = (
        UniqueConstraint("user_profile_id", "analyzed_post_id", name="uq_mission_match"),
        Index("ix_mission_matches_user_profile_id", "user_profile_id"),
        Index("ix_mission_matches_analyzed_post_id", "analyzed_post_id"),
        Index("ix_mission_matches_global_score", "global_score"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False
    )
    analyzed_post_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyzed_posts.id"), nullable=False
    )
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)
    stack_score: Mapped[float] = mapped_column(Float, nullable=False)
    contract_score: Mapped[float] = mapped_column(Float, nullable=False)
    tjm_score: Mapped[float] = mapped_column(Float, nullable=False)
    remote_score: Mapped[float] = mapped_column(Float, nullable=False)
    global_score: Mapped[float] = mapped_column(Float, nullable=False)

    user_profile: Mapped["UserProfileModel"] = relationship(back_populates="mission_matches")  # type: ignore[name-defined]
    analyzed_post: Mapped["AnalyzedPostModel"] = relationship(back_populates="mission_matches")  # type: ignore[name-defined]
