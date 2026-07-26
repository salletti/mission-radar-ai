"""Integration tests for SqlAlchemyAnalyzedPostRepository — requires running PostgreSQL."""
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Infrastructure.Persistence.Repository.analyzed_post_repository import SqlAlchemyAnalyzedPostRepository
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from tests.Integration.Repository.conftest import make_analyzed_post, make_raw_post


@pytest.mark.asyncio
async def test_save_and_get_by_id(db_session: AsyncSession) -> None:
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)

    raw = make_raw_post()
    await raw_repo.save(raw)

    analyzed = make_analyzed_post(raw_post_id=raw.id)
    await analyzed_repo.save(analyzed)

    await db_session.flush()
    db_session.expire_all()

    fetched = await analyzed_repo.get_by_id(analyzed.id)
    assert fetched is not None
    assert fetched.id == analyzed.id
    assert fetched.summary == "Mission Python full remote."
    assert fetched.detected_tjm == pytest.approx(700.0)
    assert fetched.detected_contract_type == ContractType.FREELANCE
    assert fetched.detected_remote_mode == RemoteMode.FULL_REMOTE
    assert "python" in fetched.detected_stack
    assert fetched.title == "Lead Python Engineer"
    assert fetched.seniority == "senior"
    assert fetched.created_at == analyzed.created_at


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_absent(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalyzedPostRepository(db_session)
    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_by_raw_post_id(db_session: AsyncSession) -> None:
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)

    raw = make_raw_post()
    await raw_repo.save(raw)
    analyzed = make_analyzed_post(raw_post_id=raw.id)
    await analyzed_repo.save(analyzed)

    fetched = await analyzed_repo.get_by_raw_post_id(raw.id)
    assert fetched is not None
    assert fetched.raw_post_id == raw.id


@pytest.mark.asyncio
async def test_get_by_raw_post_id_returns_none_when_absent(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalyzedPostRepository(db_session)
    result = await repo.get_by_raw_post_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_list_missions_returns_all_saved_posts(db_session: AsyncSession) -> None:
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)

    raw1 = make_raw_post()
    raw2 = make_raw_post()
    await raw_repo.save(raw1)
    await raw_repo.save(raw2)

    post1 = make_analyzed_post(raw_post_id=raw1.id)
    post2 = make_analyzed_post(
        raw_post_id=raw2.id,
        detected_stack=(),
        detected_contract_type=ContractType.UNKNOWN,
        detected_remote_mode=RemoteMode.UNKNOWN,
        summary="Autre mission.",
        title=None,
        seniority=None,
    )
    await analyzed_repo.save(post1)
    await analyzed_repo.save(post2)

    results = await analyzed_repo.list_missions(limit=100)
    result_ids = {r.id for r in results}

    assert post1.id in result_ids
    assert post2.id in result_ids


@pytest.mark.asyncio
async def test_list_missions_respects_limit(db_session: AsyncSession) -> None:
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)

    for _ in range(5):
        raw = make_raw_post()
        await raw_repo.save(raw)
        await analyzed_repo.save(make_analyzed_post(raw_post_id=raw.id))

    results = await analyzed_repo.list_missions(limit=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_save_with_embedding_none(db_session: AsyncSession) -> None:
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)

    raw = make_raw_post()
    await raw_repo.save(raw)
    analyzed = make_analyzed_post(raw_post_id=raw.id, embedding=None)
    await analyzed_repo.save(analyzed)

    await db_session.flush()
    db_session.expire_all()

    fetched = await analyzed_repo.get_by_id(analyzed.id)
    assert fetched is not None
    assert fetched.embedding is None


@pytest.mark.asyncio
async def test_save_with_embedding_vector(db_session: AsyncSession) -> None:
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)

    raw = make_raw_post()
    await raw_repo.save(raw)
    vector = [0.1, 0.2, 0.3]
    analyzed = make_analyzed_post(raw_post_id=raw.id, embedding=vector)
    await analyzed_repo.save(analyzed)

    await db_session.flush()
    db_session.expire_all()

    fetched = await analyzed_repo.get_by_id(analyzed.id)
    assert fetched is not None
    assert fetched.embedding == pytest.approx(vector)


@pytest.mark.asyncio
async def test_embedding_round_trip(db_session: AsyncSession) -> None:
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)

    raw = make_raw_post()
    await raw_repo.save(raw)
    original = [float(i) / 384 for i in range(384)]
    analyzed = make_analyzed_post(raw_post_id=raw.id, embedding=original)
    await analyzed_repo.save(analyzed)

    await db_session.flush()
    db_session.expire_all()

    fetched = await analyzed_repo.get_by_id(analyzed.id)
    assert fetched is not None
    assert fetched.embedding == pytest.approx(original, rel=1e-5)


@pytest.mark.asyncio
async def test_no_confidence_score_or_is_mission_fields(db_session: AsyncSession) -> None:
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)

    raw = make_raw_post()
    await raw_repo.save(raw)
    analyzed = make_analyzed_post(raw_post_id=raw.id)
    await analyzed_repo.save(analyzed)

    fetched = await analyzed_repo.get_by_id(analyzed.id)
    assert fetched is not None
    assert not hasattr(fetched, "confidence_score")
    assert not hasattr(fetched, "is_mission")
