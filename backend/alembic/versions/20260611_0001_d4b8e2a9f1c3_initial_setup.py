"""initial_setup

Revision ID: d4b8e2a9f1c3
Revises:
Create Date: 2026-06-11 00:01:00.000000

"""
from alembic import op
from typing import Sequence, Union

revision: str = "d4b8e2a9f1c3"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
