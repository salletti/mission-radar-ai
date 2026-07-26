from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Infrastructure.Persistence.SQLAlchemy.base import Base, TimestampedMixin


class AnalyzedPostModel(TimestampedMixin, Base):
    """SQLAlchemy model for AnalyzedPost — normalized output from MissionNormalizer."""

    __tablename__ = "analyzed_posts"
    __table_args__ = (UniqueConstraint("raw_post_id", name="uq_analyzed_posts_raw_post_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    raw_post_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("raw_posts.id"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detected_stack: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    detected_tjm_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    detected_contract_type: Mapped[str] = mapped_column(String(50), nullable=False)
    detected_remote_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seniority: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    raw_post: Mapped["RawPostModel"] = relationship(back_populates="analyzed_post")  # type: ignore[name-defined]
    mission_matches: Mapped[list["MissionMatchModel"]] = relationship(
        back_populates="analyzed_post",
        cascade="all, delete-orphan",
    )
