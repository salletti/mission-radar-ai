from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Infrastructure.Persistence.SQLAlchemy.base import Base, TimestampedMixin

if TYPE_CHECKING:
    from src.Infrastructure.Persistence.SQLAlchemy.Models.search_query_raw_post_model import SearchQueryRawPostModel


class SearchQueryModel(TimestampedMixin, Base):
    """SQLAlchemy model for SearchQuery. One row = one search executed by the scheduler."""

    __tablename__ = "search_queries"
    __table_args__ = (
        UniqueConstraint("user_profile_id", "query", "source", name="uq_search_query_profile_query_source"),
        Index("ix_search_queries_user_profile_id", "user_profile_id"),
        Index("ix_search_queries_source", "source"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)

    search_query_raw_posts: Mapped[list["SearchQueryRawPostModel"]] = relationship(
        back_populates="search_query",
        cascade="all, delete-orphan",
    )
