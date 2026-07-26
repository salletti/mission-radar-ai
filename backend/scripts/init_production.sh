#!/usr/bin/env bash
# One-shot post-deploy step: applies pending Alembic migrations.
# Run manually after the first deploy (and after any deploy that adds a
# migration). Either from a shell already inside the backend container
# (Coolify's per-service terminal): bash scripts/init_production.sh
# — or from the host: docker compose -f docker-compose.prod.yml exec backend bash scripts/init_production.sh
set -euo pipefail

alembic upgrade head
