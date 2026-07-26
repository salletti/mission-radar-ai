from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Infrastructure.Persistence.SQLAlchemy.base import Base

if TYPE_CHECKING:
    from src.Infrastructure.Persistence.SQLAlchemy.Models.raw_post_model import RawPostModel
    from src.Infrastructure.Persistence.SQLAlchemy.Models.search_query_model import SearchQueryModel


class SearchQueryRawPostModel(Base):
    """Table de liaison SearchQuery ↔ RawPost.

    Trace quels posts ont été remontés par quelle query, sans dupliquer RawPost ni AnalyzedPost.
    Pas de TimestampedMixin : une liaison n'est jamais modifiée, seulement créée ou supprimée.
    """

    __tablename__ = "search_query_raw_posts"
    __table_args__ = (
        UniqueConstraint("search_query_id", "raw_post_id", name="uq_sqrp_search_query_raw_post"),
        Index("ix_sqrp_search_query_id", "search_query_id"),
        Index("ix_sqrp_raw_post_id", "raw_post_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    search_query_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("search_queries.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_post_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("raw_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    search_query: Mapped["SearchQueryModel"] = relationship(back_populates="search_query_raw_posts")
    raw_post: Mapped["RawPostModel"] = relationship(back_populates="search_query_raw_posts")
