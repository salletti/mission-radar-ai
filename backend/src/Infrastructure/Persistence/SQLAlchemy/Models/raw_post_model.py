from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Infrastructure.Persistence.SQLAlchemy.base import Base, TimestampedMixin

if TYPE_CHECKING:
    from src.Infrastructure.Persistence.SQLAlchemy.Models.analyzed_post_model import AnalyzedPostModel
    from src.Infrastructure.Persistence.SQLAlchemy.Models.search_query_raw_post_model import SearchQueryRawPostModel


class RawPostModel(TimestampedMixin, Base):
    """SQLAlchemy model for RawPost — LinkedIn post as scraped from Apify."""

    __tablename__ = "raw_posts"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_raw_posts_source_external_id"),
        Index("ix_raw_posts_source", "source"),
        Index("ix_raw_posts_published_at", "published_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_url: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    post_url: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    analyzed_post: Mapped[Optional["AnalyzedPostModel"]] = relationship(
        back_populates="raw_post",
        uselist=False,
        cascade="all, delete-orphan",
    )
    search_query_raw_posts: Mapped[list["SearchQueryRawPostModel"]] = relationship(
        back_populates="raw_post",
        cascade="all, delete-orphan",
    )
