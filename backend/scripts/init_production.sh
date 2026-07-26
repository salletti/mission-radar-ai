#!/usr/bin/env bash
# One-shot post-deploy step: applies pending Alembic migrations.
# Run manually after the first deploy (and after any deploy that adds a
# migration), from the Coolify terminal or via:
#   docker compose -f docker-compose.prod.yml exec backend bash backend/scripts/init_production.sh
set -euo pipefail

alembic upgrade head
