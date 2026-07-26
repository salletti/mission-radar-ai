"""add_external_identities_table

Revision ID: 056eb3cd5bd7
Revises: b2c3d4e5f6a7
Create Date: 2026-07-23 20:37:39.661174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "056eb3cd5bd7"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "external_identities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_profile_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "subject", name="uq_external_identities_provider_subject"),
    )
    op.create_index("ix_external_identities_user_profile_id", "external_identities", ["user_profile_id"])


def downgrade() -> None:
    op.drop_index("ix_external_identities_user_profile_id", table_name="external_identities")
    op.drop_table("external_identities")
