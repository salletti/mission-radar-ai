"""Refactor analyzed_posts: remove is_mission/confidence_score, add summary/title/company/location/seniority

Revision ID: f3a1b2c4d5e6
Revises: e9f1a2b3c4d5
Create Date: 2026-06-20 00:00:00.000000

Architecture decision: AnalyzedPost now represents a normalized mission post produced
by MissionNormalizer. Non-job-offer posts are never persisted (is_job_offer gate).
confidence_score removed — no clear business meaning.
"""
from alembic import op
import sqlalchemy as sa

revision = "f3a1b2c4d5e6"
down_revision = "e9f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop indexes that reference removed columns
    op.drop_index("ix_analyzed_posts_is_mission", table_name="analyzed_posts")
    op.drop_index("ix_analyzed_posts_confidence_score", table_name="analyzed_posts")

    # Remove old columns
    op.drop_column("analyzed_posts", "is_mission")
    op.drop_column("analyzed_posts", "confidence_score")

    # Rename analysis_summary → summary
    op.alter_column("analyzed_posts", "analysis_summary", new_column_name="summary")

    # Add new enrichment columns (nullable — dev env has no existing data)
    op.add_column("analyzed_posts", sa.Column("title", sa.String(255), nullable=True))
    op.add_column("analyzed_posts", sa.Column("company", sa.String(255), nullable=True))
    op.add_column("analyzed_posts", sa.Column("location", sa.String(255), nullable=True))
    op.add_column("analyzed_posts", sa.Column("seniority", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("analyzed_posts", "seniority")
    op.drop_column("analyzed_posts", "location")
    op.drop_column("analyzed_posts", "company")
    op.drop_column("analyzed_posts", "title")

    op.alter_column("analyzed_posts", "summary", new_column_name="analysis_summary")

    op.add_column(
        "analyzed_posts",
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "analyzed_posts",
        sa.Column("is_mission", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_analyzed_posts_confidence_score", "analyzed_posts", ["confidence_score"])
    op.create_index("ix_analyzed_posts_is_mission", "analyzed_posts", ["is_mission"])
