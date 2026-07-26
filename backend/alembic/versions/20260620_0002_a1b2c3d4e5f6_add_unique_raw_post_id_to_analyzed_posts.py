"""Add unique constraint on analyzed_posts.raw_post_id

Revision ID: a1b2c3d4e5f6
Revises: f3a1b2c4d5e6
Create Date: 2026-06-20 00:02:00.000000

Domain invariant: one RawPost → at most one AnalyzedPost.
get_by_raw_post_id() uses scalar_one_or_none() — this constraint enforces it at DB level.
"""
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "f3a1b2c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_analyzed_posts_raw_post_id",
        "analyzed_posts",
        ["raw_post_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_analyzed_posts_raw_post_id", "analyzed_posts", type_="unique")
