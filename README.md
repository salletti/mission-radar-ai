# Mission Radar AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![React](https://img.shields.io/badge/React-18-61DAFB.svg)

Agent de veille de missions freelance : scraping LinkedIn via Apify, analyse hybride rules + LLM, matching sémantique profil ↔ mission, digest email quotidien.

Le projet sert de terrain d'entraînement pour une transition Symfony/PHP → AI engineering : Clean Architecture stricte, pipeline LLM hybride (règles pures + complétion LLM sous seuil de confiance), pondération de matching recalibrable, serveur MCP, et pipeline d'évaluation IA (DeepEval).

---

## Stack technique

| Couche | Technologie |
|---|---|
| API | FastAPI + Python 3.12 |
| Scraping | Apify API (`harvestapi/linkedin-post-search`) + tenacity |
| Broker | RabbitMQ (Celery) |
| Cache | Redis (cache sémantique) |
| Scheduler | Celery Beat |
| Base de données | PostgreSQL + SQLAlchemy async + Alembic |
| LLM dev / prod | Groq / Claude API (Anthropic) — swappable via `LLM_PROVIDER` |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Authentification | Auth0 (JWT / OAuth2) — REST + MCP |
| MCP | FastMCP |
| Observabilité | Langfuse |
| Évaluation AI | DeepEval |
| Frontend | React 18 + Vite + TypeScript + react-query |
| Email | Jinja2 + Resend |
| Conteneurisation | Docker + Docker Compose |

---

## Architecture

```
Domain/ ← Application/ ← Infrastructure/
```

Clean Architecture stricte : le `Domain` ne dépend de rien, l'`Application` ne dépend que du `Domain` et de ses propres interfaces (`Gateway` ABC), l'`Infrastructure` implémente ces interfaces (SQLAlchemy, FastAPI, Groq, Apify, Auth0…).

```
mission-radar-ai/
├── backend/
│   ├── src/
│   │   ├── Domain/            # Entités, Value Objects, Services purs, Repository (ABC)
│   │   ├── Application/       # Use Cases, DTO, Gateway (ABC)
│   │   └── Infrastructure/
│   │       ├── Api/           # Routers FastAPI
│   │       ├── Commands/      # CLI (collect_posts, analyze_post, match_missions…)
│   │       ├── Config/        # Settings, connexion base de données
│   │       ├── External/      # Apify, LLM (Groq), Mailer (Resend), Auth0, Embedding, Observability (Langfuse)
│   │       ├── Mcp/           # Serveur MCP (FastMCP) — Resources, Tools, Prompts
│   │       ├── Messaging/     # Clients RabbitMQ, Redis
│   │       ├── Persistence/   # Modèles SQLAlchemy, mappers, repositories
│   │       └── Worker/        # Tâches et scheduler Celery
│   ├── tests/                 # Unit/ + Integration/ — miroir exact de src/
│   └── alembic/                # Migrations
├── frontend/
│   └── src/
│       ├── api/                # Client HTTP
│       ├── app/                # Providers (Auth0, react-query), router
│       └── features/           # auth, dashboard, history, missions, onboarding, pipeline, summary
├── evaluation/                 # Plateforme d'évaluation AI (DeepEval, métriques, gold dataset)
├── docs/                       # Documentation détaillée
└── docker-compose.yml
```

---

## Quick Start

```bash
# Copier les variables d'environnement
cp .env.example .env
cp frontend/.env.example frontend/.env
# Remplir les clés dans .env (voir commentaires inline pour où les obtenir)

# Construire et démarrer
docker compose up --build

# Arrêter
docker compose down
```

### URLs

| Service | URL |
|---|---|
| API backend | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |
| RabbitMQ UI | http://localhost:15672 |

### Commandes utiles

```bash
# Health check
curl http://localhost:8000/health

# Shell backend
docker compose exec backend bash

# Tests unitaires
docker compose exec backend pytest tests/Unit/ -v

# Tests d'intégration
docker compose exec backend pytest tests/Integration/ -v

# Logs Celery worker
docker compose logs -f celery_worker

# Migrations Alembic
docker compose exec backend alembic upgrade head
```

---

## État du projet

| Version | Contenu | Statut |
|---|---|---|
| **V1 — MVP** | Fondations, Domain/Application layers, onboarding CV, scraping Apify + Celery, analyse hybride rules + LLM, scoring et matching, dashboard React | ✅ Terminé |
| **V2 — Qualité & Automatisation** | Dashboard complet (refresh, historique, explainability, summary), digest email quotidien, pipeline d'évaluation AI (DeepEval) | ✅ Terminé — reste : feedback 👍/👎 + recalibrage des poids (⏳), CI GitHub Actions sur le Gold Dataset (⏳) |
| **V3 — Extensibilité** | Observabilité Langfuse en production, serveur MCP (Resources/Tools/Prompts), authentification Auth0 (REST + MCP) | ✅ Terminé |

Détail complet phase par phase (1 à 10.4.7) : [`docs/PHASES.md`](docs/PHASES.md).

---

## Documentation détaillée

- [`docs/PHASES.md`](docs/PHASES.md) — historique complet du développement, phase par phase, avec parallèles Symfony/PHP pour chaque choix d'architecture
- [`docs/AUTH0_INTEGRATION.md`](docs/AUTH0_INTEGRATION.md) — guide de configuration du tenant Auth0

---

## Licence

Distribué sous licence MIT — voir [`LICENSE`](LICENSE).
