---
name: python-ai-clean-architecture
description: Utiliser pour concevoir, implémenter ou revoir une application Python AI avec Clean Architecture, notamment avec FastAPI, LLM, base de données, workers asynchrones, gateways ABC et tests par couche.
---

# Skill — Python AI Clean Architecture

## Quand utiliser ce skill

Utilise ce skill pour tout projet Python AI qui nécessite une architecture
maintenable et testable : FastAPI + LLM + base de données + workers async.

S'applique à : agents AI, pipelines RAG, systèmes d'évaluation, API AI, scrapers intelligents.

---

## Principe fondamental

```
Domain/ ← Application/ ← Infrastructure/
```

Les flèches indiquent le sens des dépendances. Elles ne s'inversent jamais.

| Couche | Rôle | Dépendances autorisées |
|---|---|---|
| `Domain/` | Logique métier pure | stdlib Python + Pydantic + dataclasses |
| `Application/` | Orchestration + gateways (ABC) | Domain uniquement |
| `Infrastructure/` | Implémentations concrètes | Tout (SQLAlchemy, FastAPI, Groq...) |

---

## Structure de référence

```
backend/
├── src/
│   ├── Domain/
│   │   ├── Entity/          # entités métier pures
│   │   ├── ValueObject/     # objets valeur immuables
│   │   ├── Repository/      # interfaces ABC (pas d'implémentation)
│   │   ├── Service/         # logique métier pure, sans I/O
│   │   └── Exception/       # exceptions domaine
│   │
│   ├── Application/
│   │   ├── UseCase/         # orchestration des cas d'usage
│   │   ├── Command/         # commandes (écriture)
│   │   ├── Query/           # requêtes (lecture)
│   │   ├── DTO/             # objets de transfert
│   │   └── Gateway/         # interfaces ABC pour dépendances externes
│   │
│   └── Infrastructure/
│       ├── Persistence/
│       │   ├── SQLAlchemy/  # modèles ORM
│       │   └── Repository/  # implémentations concrètes des repositories
│       ├── Api/
│       │   └── Controller/  # routers FastAPI + schemas Pydantic inline
│       ├── External/        # clients externes (LLM, APIs, email...)
│       └── Worker/          # Celery tasks
│
├── tests/
│   ├── Unit/                # Domain + Application sans I/O
│   ├── Integration/         # Infrastructure avec vraie DB
│   └── Fixtures/            # données mockées pour les tests
│
├── alembic/
├── requirements/
│   ├── base.txt
│   └── dev.txt
└── Dockerfile
```

---

## Règles strictes par couche

### Domain/

```python
# ✅ Autorisé
from pydantic import BaseModel
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

# ❌ Interdit
from sqlalchemy import ...
from fastapi import ...
import groq
import httpx
```

Pas d'I/O. Pas de réseau. Pas de base de données. Pas de framework.

### Application/

```python
# ✅ Autorisé
from src.Domain.Entity.user_profile import UserProfile
from src.Application.Gateway.llm_provider import LLMProvider  # ABC

# ❌ Interdit
from sqlalchemy import ...
from src.Infrastructure import ...
import groq
```

Orchestre sans connaître les détails techniques. Dépend uniquement des ABC définis dans `Gateway/`.

### Infrastructure/

```python
# ✅ Autorisé — tout
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter
import groq
from src.Application.Gateway.llm_provider import LLMProvider  # implémente l'ABC
from src.Domain.Entity.user_profile import UserProfile      # utilise les entités
```

Implémente les ABC. Connaît les frameworks. Ne contient pas de logique métier.

### Infrastructure/Api/Controller/

Schemas Pydantic directement dans les routers — pas de dossiers Request/Response/Transformer séparés. Pythonic avant tout.

```python
# ✅ Correct
from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter()

class MissionResponse(BaseModel):
    id: str
    score: float
    content: str

@router.get("/missions", response_model=list[MissionResponse])
async def get_missions():
    ...

# ❌ Sur-engineering inutile
# Request/ Response/ Transformer/ comme dossiers séparés
```

---

## Pattern ABC pour les gateways

Toutes les dépendances externes sont abstraites via ABC dans `Application/Gateway/`.
L'Infrastructure implémente. Le Domain et l'Application ne connaissent que l'ABC.

```python
# Application/Gateway/llm_provider.py
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str: ...

    @abstractmethod
    async def extract_structured(self, prompt: str, schema: type) -> dict: ...


# Application/Gateway/embedding_gateway.py
class EmbeddingGateway(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...


# Application/Gateway/scraper_gateway.py
class ScraperGateway(ABC):
    @abstractmethod
    async def scrape(self, query: str) -> list[dict]: ...


# Application/Gateway/mailer_gateway.py
class MailerGateway(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, html: str) -> None: ...


# Application/Gateway/observability_gateway.py
class ObservabilityGateway(ABC):
    @abstractmethod
    def trace(self, name: str, input: str, output: str, metadata: dict) -> None: ...
```

---

## Pattern Use Case

```python
# Application/UseCase/process_cv.py
from src.Domain.Entity.user_profile import UserProfile
from src.Application.Gateway.llm_provider import LLMProvider
from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Domain.Repository.user_profile_repository import UserProfileRepository

class ProcessCVUseCase:
    def __init__(
        self,
        llm: LLMProvider,           # ABC — pas GroqProvider directement
        embedder: EmbeddingGateway,    # ABC — pas SentenceTransformer directement
        repository: UserProfileRepository,  # ABC — pas SQLAlchemy directement
    ):
        self._llm = llm
        self._embedder = embedder
        self._repository = repository

    async def execute(self, cv_text: str) -> UserProfile:
        # logique métier ici
        extracted = await self._llm.extract_structured(cv_text, ProfileSchema)
        profile = UserProfile.from_extraction(extracted)
        embedding = await self._embedder.embed(profile.to_text())
        profile.set_embedding(embedding)
        await self._repository.save(profile)
        return profile
```

---

## Injection de dépendances FastAPI (≈ Service Container Symfony)

```python
# Infrastructure/Api/Controller/onboarding_controller.py
from fastapi import APIRouter, Depends
from src.Infrastructure.External.LLM.groq_provider import GroqProvider
from src.Infrastructure.External.Embedding.sentence_transformer import SentenceTransformerEmbedder
from src.Infrastructure.Persistence.Repository.user_profile_repository import SQLAlchemyUserProfileRepository
from src.Application.UseCase.process_cv import ProcessCVUseCase

router = APIRouter()

def get_process_cv_use_case() -> ProcessCVUseCase:
    return ProcessCVUseCase(
        llm=GroqProvider(),
        embedder=SentenceTransformerEmbedder(),
        repository=SQLAlchemyUserProfileRepository(),
    )

@router.post("/onboarding/cv")
async def upload_cv(
    use_case: ProcessCVUseCase = Depends(get_process_cv_use_case)
):
    ...
```

---

## Pattern Repository

```python
# Domain/Repository/user_profile_repository.py — interface ABC
from abc import ABC, abstractmethod
from src.Domain.Entity.user_profile import UserProfile

class UserProfileRepository(ABC):
    @abstractmethod
    async def save(self, profile: UserProfile) -> None: ...

    @abstractmethod
    async def find_by_id(self, id: str) -> UserProfile | None: ...


# Infrastructure/Persistence/Repository/user_profile_repository.py — implémentation
from sqlalchemy.ext.asyncio import AsyncSession
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.Entity.user_profile import UserProfile
from src.Infrastructure.Persistence.SQLAlchemy.user_profile_model import UserProfileModel

class SQLAlchemyUserProfileRepository(UserProfileRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, profile: UserProfile) -> None:
        model = UserProfileModel.from_entity(profile)
        self._session.add(model)
        await self._session.commit()

    async def find_by_id(self, id: str) -> UserProfile | None:
        model = await self._session.get(UserProfileModel, id)
        return model.to_entity() if model else None
```

---

## Parallèles Symfony → Python

| Symfony | Python |
|---|---|
| Interface PHP | ABC Python |
| Service Container + injection | FastAPI `Depends()` |
| Doctrine Entity | SQLAlchemy Model |
| Doctrine Repository | Repository ABC + implémentation SQLAlchemy |
| Migrations Doctrine | Alembic |
| Symfony Messenger + Handler | Celery task + RabbitMQ |
| Form + DTO | Pydantic schema |
| HttpClient | httpx async |
| EventDispatcher | Celery signals |
| Twig | Jinja2 |
| Bundle | Package Python |
| `services.yaml` | `Depends()` FastAPI |
| PHPUnit | pytest |
| PHPStan | mypy |
| PHP-CS-Fixer | ruff format |
| PSR standards | PEP 8 + ruff |

---

## Conventions de code

```python
# Nommage
class UserProfile:          # PascalCase pour les classes
    pass

user_profile.py             # snake_case pour les fichiers

async def get_profile():    # snake_case pour les fonctions
    pass

MAX_RETRY_COUNT = 3         # SCREAMING_SNAKE_CASE pour les constantes

# Type hints obligatoires sur toutes les fonctions publiques
async def match_mission(profile: UserProfile, post: RawPost) -> MatchScore:
    ...

# Docstrings sur les classes Domain et les Use Cases
class MatchMissionsUseCase:
    """
    Calcule le score de matching entre le profil utilisateur
    et les posts LinkedIn analysés du jour.
    """
```

---

## Stratégie de tests

```
tests/Unit/        → Domain + Application
                     pas de mock I/O
                     pas de DB
                     pas de réseau
                     rapide (< 1s)

tests/Integration/ → Infrastructure
                     vraie DB PostgreSQL
                     via Docker Compose
                     lent mais réaliste

tests/Fixtures/    → JSON mockés pour tests dev
                     ne jamais appeler les APIs réelles dans les tests
```

```python
# Unit test — Domain pur
def test_match_score_global():
    score = MatchScore(
        semantic_score=0.8,
        stack_score=0.9,
        contract_score=1.0,
        tjm_score=0.7,
        remote_score=1.0,
    )
    assert score.global_score == pytest.approx(0.86, abs=0.01)


# Unit test — Use Case avec mock ABC
async def test_process_cv_saves_profile():
    llm_mock = AsyncMock(spec=LLMProvider)
    llm_mock.extract_structured.return_value = {"stack": ["Python"], "tjm": 600}

    embedder_mock = AsyncMock(spec=EmbeddingGateway)
    embedder_mock.embed.return_value = [0.1] * 384

    repo_mock = AsyncMock(spec=UserProfileRepository)

    use_case = ProcessCVUseCase(llm_mock, embedder_mock, repo_mock)
    await use_case.execute("cv text here")

    repo_mock.save.assert_called_once()
```

---

## Commandes utiles

```bash
# Lancer tous les services
docker compose up --build

# Shell backend
docker compose exec backend bash

# Migrations
docker compose exec backend alembic upgrade head
docker compose exec backend alembic revision --autogenerate -m "add_mission_feedback"

# Tests unitaires
docker compose exec backend pytest tests/Unit/ -v

# Tests intégration
docker compose exec backend pytest tests/Integration/ -v

# Lint + format
docker compose exec backend ruff check src/
docker compose exec backend ruff format src/

# Type checking
docker compose exec backend mypy src/
```
