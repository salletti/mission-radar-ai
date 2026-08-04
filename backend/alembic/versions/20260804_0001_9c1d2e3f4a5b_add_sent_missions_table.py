"""add sent_missions table

Revision ID: 9c1d2e3f4a5b
Revises: 056eb3cd5bd7
Create Date: 2026-08-04 00:00:00.000000

Table de suivi des missions déjà envoyées à un utilisateur dans un digest.
Clé stable sur analyzed_post_id (contrairement à MissionMatch, recréé à chaque run de
MatchMissions) — sert de base à l'exclusion définitive côté DigestMissionSelector.
La contrainte UNIQUE(user_profile_id, analyzed_post_id) garantit l'absence de doublons.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "9c1d2e3f4a5b"
down_revision: str | None = "056eb3cd5bd7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sent_missions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_profile_id", UUID(as_uuid=True), nullable=False),
        sa.Column("analyzed_post_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_profile_id"],
            ["user_profiles.id"],
            name="fk_sent_missions_user_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["analyzed_post_id"],
            ["analyzed_posts.id"],
            name="fk_sent_missions_analyzed_post_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_profile_id", "analyzed_post_id", name="uq_sent_missions_user_analyzed_post"),
    )
    op.create_index("ix_sent_missions_user_profile_id", "sent_missions", ["user_profile_id"])
    op.create_index("ix_sent_missions_analyzed_post_id", "sent_missions", ["analyzed_post_id"])


def downgrade() -> None:
    op.drop_index("ix_sent_missions_analyzed_post_id", table_name="sent_missions")
    op.drop_index("ix_sent_missions_user_profile_id", table_name="sent_missions")
    op.drop_table("sent_missions")
