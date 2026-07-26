"""add_search_queries_table

Revision ID: e9f1a2b3c4d5
Revises: 3a60da7c9068
Create Date: 2026-06-18 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e9f1a2b3c4d5'
down_revision: Union[str, None] = '3a60da7c9068'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'search_queries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_profile_id', sa.UUID(), nullable=False),
        sa.Column('query', sa.String(length=500), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('limit', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_profile_id'], ['user_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_profile_id', 'query', 'source', name='uq_search_query_profile_query_source'),
    )
    op.create_index('ix_search_queries_user_profile_id', 'search_queries', ['user_profile_id'], unique=False)
    op.create_index('ix_search_queries_source', 'search_queries', ['source'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_search_queries_source', table_name='search_queries')
    op.drop_index('ix_search_queries_user_profile_id', table_name='search_queries')
    op.drop_table('search_queries')
