from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.Infrastructure.Persistence.SQLAlchemy.Models.analyzed_post_model import AnalyzedPostModel
from src.Infrastructure.Persistence.SQLAlchemy.Models.mission_match_model import MissionMatchModel
from src.Infrastructure.Persistence.SQLAlchemy.Models.raw_post_model import RawPostModel
from src.Infrastructure.Persistence.SQLAlchemy.Models.user_profile_model import UserProfileModel


async def seed_demo_data(session: AsyncSession) -> None:
    """Insert demo fixtures — idempotent, safe to run multiple times."""
    count = await session.scalar(select(func.count()).select_from(UserProfileModel))
    if count and count > 0:
        return

    now = datetime.now(timezone.utc)

    profile = UserProfileModel(
        id=uuid4(),
        email="demo@mission-radar.ai",
        full_name="Stefano Demo",
        title="Lead Engineer Python / FastAPI",
        years_experience=15,
        preferred_contract_type="freelance",
        target_tjm=750.0,
        preferred_remote_mode="full_remote",
        location="Paris, France",
        availability=datetime(2026, 7, 1, tzinfo=timezone.utc),
        skills=["Python", "FastAPI", "Docker", "PostgreSQL", "RabbitMQ", "Redis", "Celery"],
        embedding=None,
    )
    session.add(profile)
    await session.flush()

    raw_posts = [
        RawPostModel(
            id=uuid4(),
            source="linkedin",
            external_id="post_001",
            author_name="Marie Dupont",
            author_url="https://linkedin.com/in/marie-dupont",
            content="🚀 Mission freelance — Lead Python/FastAPI, 100% remote, TJM 700-750€/j. Stack : Python, FastAPI, PostgreSQL, Redis. Démarrage ASAP. #freelance #python",
            post_url="https://linkedin.com/posts/post_001",
            published_at=datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc),
            scraped_at=now,
        ),
        RawPostModel(
            id=uuid4(),
            source="linkedin",
            external_id="post_002",
            author_name="Jean Martin",
            author_url="https://linkedin.com/in/jean-martin",
            content="Recherche Expert Backend Python pour mission 6 mois. Télétravail partiel (2j/sem). TJM 650€. Compétences : Django, Docker, Kubernetes.",
            post_url="https://linkedin.com/posts/post_002",
            published_at=datetime(2026, 6, 11, 14, 30, tzinfo=timezone.utc),
            scraped_at=now,
        ),
        RawPostModel(
            id=uuid4(),
            source="linkedin",
            external_id="post_003",
            author_name="Sophie Bernard",
            author_url="https://linkedin.com/in/sophie-bernard",
            content="Nous recrutons un Architecte Logiciel Python. CDI. Paris. Expérience 10 ans requis. Stack moderne, belle équipe.",
            post_url="https://linkedin.com/posts/post_003",
            published_at=datetime(2026, 6, 12, 8, 0, tzinfo=timezone.utc),
            scraped_at=now,
        ),
    ]
    session.add_all(raw_posts)
    await session.flush()

    analyzed_posts = [
        AnalyzedPostModel(
            id=uuid4(),
            raw_post_id=raw_posts[0].id,
            summary="Mission freelance Python/FastAPI full remote, TJM 700-750€/j, démarrage ASAP.",
            detected_stack=["fastapi", "postgresql", "python", "redis"],
            detected_tjm_amount=725.0,
            detected_contract_type="freelance",
            detected_remote_mode="full_remote",
            title="Lead Python/FastAPI",
            company=None,
            location=None,
            seniority="lead",
        ),
        AnalyzedPostModel(
            id=uuid4(),
            raw_post_id=raw_posts[1].id,
            summary="Mission 6 mois Backend Python, télétravail partiel, TJM 650€.",
            detected_stack=["django", "docker", "kubernetes", "python"],
            detected_tjm_amount=650.0,
            detected_contract_type="freelance",
            detected_remote_mode="hybrid",
            title="Expert Backend Python",
            company=None,
            location=None,
            seniority="senior",
        ),
        AnalyzedPostModel(
            id=uuid4(),
            raw_post_id=raw_posts[2].id,
            summary="Offre CDI Architecte Python Paris — pas une mission freelance.",
            detected_stack=["python"],
            detected_tjm_amount=None,
            detected_contract_type="permanent",
            detected_remote_mode="onsite",
            title="Architecte Logiciel Python",
            company=None,
            location="Paris",
            seniority="senior",
        ),
    ]
    session.add_all(analyzed_posts)
    await session.flush()

    mission_matches = [
        MissionMatchModel(
            id=uuid4(),
            user_profile_id=profile.id,
            analyzed_post_id=analyzed_posts[0].id,
            semantic_score=0.91,
            stack_score=0.88,
            contract_score=1.0,
            tjm_score=0.97,
            remote_score=1.0,
            global_score=0.935,
        ),
        MissionMatchModel(
            id=uuid4(),
            user_profile_id=profile.id,
            analyzed_post_id=analyzed_posts[1].id,
            semantic_score=0.72,
            stack_score=0.60,
            contract_score=1.0,
            tjm_score=0.80,
            remote_score=0.50,
            global_score=0.712,
        ),
        MissionMatchModel(
            id=uuid4(),
            user_profile_id=profile.id,
            analyzed_post_id=analyzed_posts[2].id,
            semantic_score=0.65,
            stack_score=0.50,
            contract_score=0.0,
            tjm_score=0.0,
            remote_score=0.0,
            global_score=0.41,
        ),
    ]
    session.add_all(mission_matches)
    await session.flush()
