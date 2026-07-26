# CLAUDE.md — mission-radar-ai

## Contexte projet

Agent de veille de missions freelance qui scrape les posts LinkedIn via Apify,
analyse les opportunités avec un LLM, et les matche avec un profil CV utilisateur.

## Contexte développeur

- 15 ans de Symfony/PHP/DDD/Clean Architecture — faire des parallèles Symfony quand utile
- En conversion vers l'AI engineering — projets existants : FastAPI, LangChain, LangGraph, Qdrant, RAGAS, DeepEval
- Approche pédagogique : expliquer les choix d'architecture, valider chaque phase avant de passer à la suivante

## Stack technique

```
Backend        : FastAPI + Python 3.12
Scraping       : Apify API (harvestapi/linkedin-post-search) + tenacity (retry/backoff)
Broker         : RabbitMQ (Celery broker — queues, DLQ, retry) ≈ Symfony Messenger
Cache          : Redis (cache sémantique uniquement — pas broker)
Scheduler      : Celery + RabbitMQ
DB             : PostgreSQL + SQLAlchemy async + Alembic ≈ Doctrine + Migrations
LLM            : Groq en dev → Claude API en prod (swappable via ABC)
Embeddings     : sentence-transformers (all-MiniLM-L6-v2)
PDF            : pdfminer.six
Observabilité  : Langfuse
Évaluation AI  : DeepEval + GitHub Actions
MCP            : FastMCP (V3)
Auth           : Auth0 (JWT/OAuth2 — REST + MCP, Phase 10.4)
Frontend       : React + Vite + TypeScript + react-query + recharts
Email          : Jinja2 + Resend
```

## Structure du projet

```
mission-radar-ai/
├── backend/
│   ├── src/
│   │   ├── Domain/
│   │   │   ├── Entity/          # UserProfile, RawPost, AnalyzedPost, MissionMatch, PipelineRun...
│   │   │   ├── ValueObject/     # TJM, Stack, ContractType, MatchScore, PostAnalysis, DigestMission...
│   │   │   ├── Repository/      # interfaces abstraites (ABC)
│   │   │   ├── Service/         # logique métier pure, sans I/O (scoring, normalisation, digest...)
│   │   │   └── Exception/       # exceptions domaine
│   │   ├── Application/
│   │   │   ├── UseCase/         # ProcessCV, MatchMissions, GenerateDigest, StartMissionRefresh...
│   │   │   ├── DTO/             # Command/Query/Result DTO — pas de dossiers Command/ ou Query/ séparés
│   │   │   ├── Gateway/         # ABC : LLMGateway, ScraperGateway, MailerGateway, EmbeddingGateway, TokenVerifierGateway...
│   │   │   └── Exception/       # exceptions applicatives
│   │   └── Infrastructure/
│   │       ├── Api/
│   │       │   ├── Controller/  # routers FastAPI + schemas Pydantic inline
│   │       │   └── Dependency/  # FastAPI Depends() — assemblage des dépendances
│   │       ├── Commands/        # CLI (collect_posts, analyze_post, match_missions...)
│   │       ├── Config/          # Settings (pydantic-settings), connexion base de données
│   │       ├── External/
│   │       │   ├── Apify/       # ApifyScraperGateway + fixtures JSON mock
│   │       │   ├── Auth0/       # Auth0TokenVerifierGateway
│   │       │   ├── CV/          # PdfMinerCVExtractorGateway
│   │       │   ├── Embedding/   # SentenceTransformerEmbeddingGateway
│   │       │   ├── LLM/         # GroqLLMGateway (ClaudeProvider prévu)
│   │       │   ├── Mailer/      # ResendMailerGateway + templates Jinja2
│   │       │   └── Observability/ # LangfuseTracer / NullTracer
│   │       ├── Mcp/             # Serveur MCP (FastMCP) — Resources, Tools, Prompts, Identity, Transport
│   │       ├── Messaging/       # Clients RabbitMQ, Redis
│   │       ├── Persistence/
│   │       │   ├── SQLAlchemy/  # modèles ORM
│   │       │   ├── Mapper/      # Domain ↔ SQLAlchemy
│   │       │   ├── Repository/  # implémentations concrètes
│   │       │   └── Seeds/       # données de démo
│   │       └── Worker/          # Celery — tasks/, scheduler/, dispatchers/
│   ├── tests/
│   │   ├── Unit/                # miroir exact de src/ — aucun mock I/O
│   │   ├── Integration/
│   │   └── Fixtures/            # JSON Apify mockés (données 100% fictives) + CV PDF de test
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements/
│   │   ├── base.txt
│   │   └── dev.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                 # client HTTP
│   │   ├── app/                 # providers (Auth0, react-query), router
│   │   ├── context/
│   │   ├── features/            # auth, dashboard, history, missions, onboarding, pipeline, summary
│   │   └── shared/               # composants partagés (layouts...)
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── evaluation/                  # Plateforme d'évaluation AI (DeepEval, métriques, gold dataset) — hors Domain/Application
├── docs/                        # Documentation détaillée (PHASES.md, AUTH0_INTEGRATION.md)
├── docker-compose.yml
├── LICENSE
└── README.md
```

## Règles d'architecture — STRICT

```
Domain/ ← Application/ ← Infrastructure/
```

- `Domain/` : pas d'I/O — Pydantic et dataclasses autorisés — zéro import SQLAlchemy/FastAPI/Groq
- `Application/` : dépend uniquement de `Domain/` et de ses propres ABC — jamais d'import Infrastructure
- `Infrastructure/` : implémente les ABC — dépend de SQLAlchemy, Groq, Apify, FastAPI
- `Infrastructure/Api/Controller/` : schemas Pydantic directement dans les routers — pas de dossiers Request/Response/Transformer séparés
- Pythonic avant tout — pas de boilerplate inutile

## Pattern LLM Provider (ABC)

```python
# backend/src/Application/Gateway/llm_provider.py
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str: ...

    @abstractmethod
    async def extract_structured(self, prompt: str, schema: type) -> dict: ...
```

Implémentations dans `Infrastructure/External/LLM/` :
- `GroqProvider` — dev & prod légère (gratuit)
- `ClaudeProvider` — prod haute qualité (payant)

Swappable via variable d'environnement `LLM_PROVIDER=groq|claude`

Même principe pour `ScraperGateway`, `MailerGateway`, `EmbeddingGateway`, `ObservabilityGateway`.

## Pipeline d'analyse hybride rules + LLM

```
Post LinkedIn brut
        ↓
Rule Engine Python pur (re + dictionnaires — jamais de LLM ici)
  → regex TJM : "600€/j", "700 €/jour", "TJM 650", "600-700€"
  → dictionnaire stack : 200+ technos
  → heuristiques remote : "full remote", "télétravail", "100% remote"
  → détection mission : hashtags + verbes recrutement
        ↓
Confidence Score global (0.0 → 1.0)
        ↓
confidence >= 0.7 → résultat Rule Engine final (pas d'appel LLM)
confidence < 0.7  → LLM complète les champs faible confiance uniquement
                    merge(rule_result, llm_result)
                    champs haute confiance Rule Engine jamais écrasés
        ↓
Tracing Langfuse systématique
```

## Retry/backoff Apify (tenacity)

```
Appel Apify → échec → attendre 2s → retry
            → échec → attendre 4s → retry
            → échec → attendre 8s → retry
            → échec → Dead Letter Queue RabbitMQ
```

## Matching pondéré

```
global_score =
    semantic_score  × 0.4   (cosine similarity embedding CV vs post)
  + stack_score     × 0.3   (% stack post présente dans CV)
  + contract_score  × 0.1   (type contrat souhaité vs détecté)
  + tjm_score       × 0.1   (TJM cible vs TJM détecté)
  + remote_score    × 0.1   (préférence remote vs modalité post)
```

Les poids sont stockés en base et recalibrés automatiquement après 50 feedbacks 👍/👎.

## Parallèles Symfony → Python à utiliser

| Symfony | Python/projet |
|---|---|
| Messenger + Handler | Celery task + RabbitMQ |
| Doctrine Entity | SQLAlchemy Model |
| Doctrine Repository | Repository ABC + implémentation SQLAlchemy |
| Migrations Doctrine | Alembic |
| Service Container | FastAPI Depends() |
| Form + DTO | Pydantic schema |
| HttpClient | httpx async |
| EventDispatcher | Celery signals ou events |
| Interface PHP | ABC Python |
| Twig | Jinja2 |
| RabbitMQ + Messenger (L'Express) | Celery + RabbitMQ |

## Roadmap versions

```
MVP (V1) : phases 1-5
  Phase 1 : fondations + Docker + DB + health check
  Phase 2 : onboarding CV + formulaire profil
  Phase 3 : scraping quotidien Apify + Celery
  Phase 4 : analyse hybride rules + LLM + scoring
  Phase 5 : dashboard React

V2 : phases 6-8
  Phase 6 : feedback 👍/👎 + recalibrage poids
  Phase 7 : digest quotidien email
  Phase 8 : pipeline évaluation AI DeepEval + CI

V3 : phase 10
  Phase 10.0 : Bootstrap serveur MCP (fastmcp, IdentityResolver, whoami)
  Phase 10.1 : MCP Resources — GetUserProfile, Prompt Templates, Composite/Pipeline Tools, Discovery Tools
  Phase 10.2 : montage HTTP dans FastAPI (/mcp) + SharedSecretMiddleware (garde-fou temporaire, retiré en 10.4.5)
  Phase 10.3 : MCP Prompt Templates (analyze_profile, prepare_mission_search, explain_mission_fit, prioritize_today_missions)
  Phase 10.4 : Auth0 — source d'identité unique (React, API REST, serveur MCP), JwtIdentityResolver remplace EnvironmentIdentityResolver/SharedSecretMiddleware côté HTTP
```

## Librairies par phase

```
Phase 1 : sqlalchemy[asyncio], asyncpg, alembic
Phase 2 : pdfminer.six, groq, pydantic, sentence-transformers, react-hook-form, zod
Phase 3 : celery, apify-client, tenacity
Phase 4 : re (stdlib), groq, pydantic, sentence-transformers, langfuse
Phase 5 : react-query, recharts
Phase 6 : (pas de nouvelle lib)
Phase 7 : jinja2, resend
Phase 8 : deepeval, github-actions
Phase 10.0 : fastmcp
```

## Seuils évaluation AI (GitHub Actions)

```
précision extraction stack  >= 0.80
précision TJM               >= 0.75
recall missions             >= 0.85
hallucination rate          <= 0.10
```

## Conventions de code

- Nommage classes : PascalCase (`UserProfile`, `GroqProvider`)
- Nommage fichiers : snake_case (`user_profile.py`, `groq_provider.py`)
- Async partout dans Infrastructure — sync uniquement dans Domain et Application
- Type hints obligatoires sur toutes les fonctions publiques
- Docstrings sur les classes Domain et les Use Cases
- Tests unitaires dans `Unit/` sans aucun mock I/O
- Fixtures JSON Apify dans `Fixtures/` — ne jamais appeler l'API réelle dans les tests

## Commandes Docker utiles

```bash
# Démarrer tous les services
docker compose up --build

# Backend uniquement
docker compose exec backend bash

# Migrations
docker compose exec backend alembic upgrade head

# Nouvelle migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Tests unitaires
docker compose exec backend pytest tests/Unit/ -v

# Celery worker logs
docker compose logs -f celery_worker

# RabbitMQ Management UI
open http://localhost:15672
```

## Variables d'environnement requises

```bash
# LLM
LLM_PROVIDER=groq                    # groq | claude
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...         # optionnel en dev

# Apify
APIFY_API_TOKEN=apify_api_...

# Base de données
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/mission_radar

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Redis
REDIS_URL=redis://redis:6379

# Observabilité
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Email
RESEND_API_KEY=re_...

# App
APP_ENV=development                  # development | production
```
