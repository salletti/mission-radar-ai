import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Rend les imports src.* disponibles depuis n'importe quel répertoire de travail
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.Infrastructure.Config.settings import settings
from src.Infrastructure.Persistence.SQLAlchemy.base import Base
from src.Infrastructure.Persistence.SQLAlchemy.Models import (  # noqa: F401
    UserProfileModel, RawPostModel, AnalyzedPostModel, MissionMatchModel, SearchQueryModel, SearchQueryRawPostModel,
    PipelineRunModel, DigestHistoryModel, ExternalIdentityModel,
)

config = context.config

# Les settings Python ont la priorité sur sqlalchemy.url dans alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Base.metadata ≈ mapping Doctrine : Alembic compare ce metadata avec le schéma réel pour --autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Mode hors ligne : génère le SQL sans connexion DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Mode en ligne : connexion async réelle à PostgreSQL."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool obligatoire pour Alembic — pas de pool persistant
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
