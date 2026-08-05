#!/usr/bin/env bash
# Applies pending Alembic migrations. Normally unnecessary: the `migrate`
# service in docker-compose.prod.yml runs this automatically before backend/
# celery_worker/celery_beat start on every deploy. Kept as a manual fallback
# (e.g. to check/repair migration state without a full redeploy). Either from
# a shell already inside the backend container (Coolify's per-service
# terminal): bash scripts/init_production.sh — or from the host:
# docker compose -f docker-compose.prod.yml exec backend bash scripts/init_production.sh
set -euo pipefail

alembic upgrade head
