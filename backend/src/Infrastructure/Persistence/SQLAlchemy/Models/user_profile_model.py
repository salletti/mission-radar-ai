from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Infrastructure.Persistence.SQLAlchemy.base import Base, TimestampedMixin


class UserProfileModel(TimestampedMixin, Base):
    """SQLAlchemy model for UserProfile. ≈ Doctrine Entity with lifecycle callbacks."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_profiles_email"),
        Index("ix_user_profiles_email", "email"),
        Index("ix_user_profiles_availability", "availability"),
        Index("ix_user_profiles_preferred_contract_type", "preferred_contract_type"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred_contract_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_tjm: Mapped[float] = mapped_column(Float, nullable=False)
    preferred_remote_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    availability: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 384 dimensions = all-MiniLM-L6-v2 output size
    embedding: Mapped[Optional[list]] = mapped_column(Vector(384), nullable=True)
    cv_raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    mission_matches: Mapped[list["MissionMatchModel"]] = relationship(
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
