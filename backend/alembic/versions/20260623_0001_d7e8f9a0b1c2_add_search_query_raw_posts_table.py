"""add search_query_raw_posts table

Revision ID: d7e8f9a0b1c2
Revises: c4d5e6f7a8b9
Create Date: 2026-06-23 00:00:00.000000

Table de liaison SearchQuery ↔ RawPost.
Permet de tracer quels posts ont été remontés par quelle query sans dupliquer RawPost.
La contrainte UNIQUE(search_query_id, raw_post_id) garantit l'absence de doublons de liaison.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "d7e8f9a0b1c2"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_query_raw_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("search_query_id", UUID(as_uuid=True), nullable=False),
        sa.Column("raw_post_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["search_query_id"],
            ["search_queries.id"],
            name="fk_sqrp_search_query_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["raw_post_id"],
            ["raw_posts.id"],
            name="fk_sqrp_raw_post_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("search_query_id", "raw_post_id", name="uq_sqrp_search_query_raw_post"),
    )
    op.create_index("ix_sqrp_search_query_id", "search_query_raw_posts", ["search_query_id"])
    op.create_index("ix_sqrp_raw_post_id", "search_query_raw_posts", ["raw_post_id"])


def downgrade() -> None:
    op.drop_index("ix_sqrp_raw_post_id", table_name="search_query_raw_posts")
    op.drop_index("ix_sqrp_search_query_id", table_name="search_query_raw_posts")
    op.drop_table("search_query_raw_posts")
