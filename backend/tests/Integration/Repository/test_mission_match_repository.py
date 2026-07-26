"""Integration tests for SqlAlchemyMissionMatchRepository — requires running PostgreSQL."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.Infrastructure.Persistence.Repository.analyzed_post_repository import SqlAlchemyAnalyzedPostRepository
from src.Infrastructure.Persistence.Repository.mission_match_repository import SqlAlchemyMissionMatchRepository
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from tests.Integration.Repository.conftest import (
    make_analyzed_post,
    make_mission_match,
    make_raw_post,
    make_user_profile,
)


async def _setup_prerequisites(db_session):
    """Persist a user profile + raw post + analyzed post, return their entities."""
    profile = make_user_profile()
    raw = make_raw_post()
    await SqlAlchemyUserProfileRepository(db_session).save(profile)
    await SqlAlchemyRawPostRepository(db_session).save(raw)
    analyzed = make_analyzed_post(raw_post_id=raw.id)
    await SqlAlchemyAnalyzedPostRepository(db_session).save(analyzed)
    return profile, analyzed


@pytest.mark.asyncio
async def test_save_and_get_by_id(db_session: AsyncSession) -> None:
    profile, analyzed = await _setup_prerequisites(db_session)
    repo = SqlAlchemyMissionMatchRepository(db_session)

    match = make_mission_match(user_profile_id=profile.id, analyzed_post_id=analyzed.id)
    await repo.save(match)

    fetched = await repo.get_by_id(match.id)
    assert fetched is not None
    assert fetched.id == match.id
    assert fetched.final_score == pytest.approx(match.final_score)
    assert fetched.match_score.semantic_score == pytest.approx(0.85)


@pytest.mark.asyncio
async def test_get_by_user(db_session: AsyncSession) -> None:
    profile, analyzed = await _setup_prerequisites(db_session)
    repo = SqlAlchemyMissionMatchRepository(db_session)

    await repo.save(make_mission_match(user_profile_id=profile.id, analyzed_post_id=analyzed.id))

    matches = await repo.get_by_user(profile.id)
    assert len(matches) == 1
    assert matches[0].user_profile_id == profile.id


@pytest.mark.asyncio
async def test_get_by_post(db_session: AsyncSession) -> None:
    profile, analyzed = await _setup_prerequisites(db_session)
    repo = SqlAlchemyMissionMatchRepository(db_session)

    await repo.save(make_mission_match(user_profile_id=profile.id, analyzed_post_id=analyzed.id))

    matches = await repo.get_by_post(analyzed.id)
    assert len(matches) == 1
    assert matches[0].analyzed_post_id == analyzed.id


@pytest.mark.asyncio
async def test_get_best_matches_sorted_by_global_score(db_session: AsyncSession) -> None:
    profile = make_user_profile()
    raw1, raw2 = make_raw_post(), make_raw_post()
    await SqlAlchemyUserProfileRepository(db_session).save(profile)
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)
    await raw_repo.save(raw1)
    await raw_repo.save(raw2)
    analyzed1 = make_analyzed_post(raw_post_id=raw1.id)
    analyzed2 = make_analyzed_post(raw_post_id=raw2.id)
    await analyzed_repo.save(analyzed1)
    await analyzed_repo.save(analyzed2)

    repo = SqlAlchemyMissionMatchRepository(db_session)
    await repo.save(make_mission_match(user_profile_id=profile.id, analyzed_post_id=analyzed1.id, semantic_score=0.60))
    await repo.save(make_mission_match(user_profile_id=profile.id, analyzed_post_id=analyzed2.id, semantic_score=0.90))

    best = await repo.get_best_matches(profile.id, limit=2)
    assert len(best) == 2
    assert best[0].final_score >= best[1].final_score


@pytest.mark.asyncio
async def test_get_best_matches_respects_limit(db_session: AsyncSession) -> None:
    profile = make_user_profile()
    await SqlAlchemyUserProfileRepository(db_session).save(profile)
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)
    repo = SqlAlchemyMissionMatchRepository(db_session)

    for _ in range(4):
        raw = make_raw_post()
        await raw_repo.save(raw)
        analyzed = make_analyzed_post(raw_post_id=raw.id)
        await analyzed_repo.save(analyzed)
        await repo.save(make_mission_match(user_profile_id=profile.id, analyzed_post_id=analyzed.id))

    best = await repo.get_best_matches(profile.id, limit=2)
    assert len(best) == 2


@pytest.mark.asyncio
async def test_save_many(db_session: AsyncSession) -> None:
    profile = make_user_profile()
    await SqlAlchemyUserProfileRepository(db_session).save(profile)
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)
    repo = SqlAlchemyMissionMatchRepository(db_session)

    matches = []
    for _ in range(3):
        raw = make_raw_post()
        await raw_repo.save(raw)
        analyzed = make_analyzed_post(raw_post_id=raw.id)
        await analyzed_repo.save(analyzed)
        matches.append(make_mission_match(user_profile_id=profile.id, analyzed_post_id=analyzed.id))

    await repo.save_many(matches)

    stored = await repo.get_by_user(profile.id)
    assert len(stored) == 3


@pytest.mark.asyncio
async def test_delete_then_save_many_replaces_scores(db_session: AsyncSession) -> None:
    """Delete + save_many replaces the previous match (clean re-run semantics)."""
    profile, analyzed = await _setup_prerequisites(db_session)
    repo = SqlAlchemyMissionMatchRepository(db_session)

    match = make_mission_match(
        user_profile_id=profile.id, analyzed_post_id=analyzed.id, semantic_score=0.50
    )
    await repo.save_many([match])

    # Simulate re-run: delete old results, then save fresh ones
    await repo.delete_user_matches(profile.id)
    updated_match = make_mission_match(
        user_profile_id=profile.id, analyzed_post_id=analyzed.id, semantic_score=0.90
    )
    await repo.save_many([updated_match])

    stored = await repo.get_by_user(profile.id)
    assert len(stored) == 1
    assert stored[0].match_score.semantic_score == pytest.approx(0.90)


@pytest.mark.asyncio
async def test_delete_user_matches(db_session: AsyncSession) -> None:
    profile, analyzed = await _setup_prerequisites(db_session)
    repo = SqlAlchemyMissionMatchRepository(db_session)

    await repo.save(make_mission_match(user_profile_id=profile.id, analyzed_post_id=analyzed.id))
    assert len(await repo.get_by_user(profile.id)) == 1

    await repo.delete_user_matches(profile.id)
    assert len(await repo.get_by_user(profile.id)) == 0
