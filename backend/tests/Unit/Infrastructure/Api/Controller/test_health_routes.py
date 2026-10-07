"""Vérifie les chemins exposés par le router health — sans appel aux services (Postgres, RabbitMQ, Redis)."""
from src.Infrastructure.Api.Controller.health import router


def test_health_expose_le_chemin_interne_et_le_chemin_public_sous_api() -> None:
    paths = {route.path for route in router.routes}

    assert "/health" in paths  # healthcheck Docker
    assert "/api/health" in paths  # relayé par nginx (location /api/)
