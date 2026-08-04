"""Unit tests for DigestMissionSelector — no I/O, no DB, no external services."""
from datetime import datetime, timezone
from uuid import uuid4


from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Service.digest_mission_selector import DigestMissionSelector, TOP_MISSIONS
from src.Domain.ValueObject.match_score import MatchScore


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_match(semantic_score: float = 0.8) -> MissionMatch:
    score = MatchScore(
        semantic_score=semantic_score,
        contract_score=1.0,
        remote_score=1.0,
        tjm_score=1.0,
    )
    return MissionMatch(
        user_profile_id=uuid4(),
        analyzed_post_id=uuid4(),
        match_score=score,
        created_at=datetime.now(timezone.utc),
    )


def _selector() -> DigestMissionSelector:
    return DigestMissionSelector()


# ---------------------------------------------------------------------------
# Tests — empty input
# ---------------------------------------------------------------------------


class TestDigestMissionSelectorEmptyInput:
    def test_empty_list_returns_empty(self):
        result = _selector().select([])
        assert result == []


# ---------------------------------------------------------------------------
# Tests — ordering
# ---------------------------------------------------------------------------


class TestDigestMissionSelectorOrdering:
    def test_returns_missions_sorted_by_score_descending(self):
        low = _make_match(semantic_score=0.3)
        high = _make_match(semantic_score=0.9)
        mid = _make_match(semantic_score=0.6)

        result = _selector().select([low, high, mid])

        assert result[0] is high
        assert result[1] is mid
        assert result[2] is low

    def test_highest_score_is_first(self):
        matches = [_make_match(semantic_score=0.9 - i * 0.1) for i in range(5)]
        result = _selector().select(matches)
        assert result[0].final_score >= result[-1].final_score


# ---------------------------------------------------------------------------
# Tests — limiting
# ---------------------------------------------------------------------------


class TestDigestMissionSelectorLimiting:
    def test_returns_at_most_max_count(self):
        matches = [_make_match() for _ in range(15)]
        result = _selector().select(matches, max_count=5)
        assert len(result) == 5

    def test_default_max_count_is_top_missions_constant(self):
        matches = [_make_match() for _ in range(TOP_MISSIONS + 5)]
        result = _selector().select(matches)
        assert len(result) == TOP_MISSIONS

    def test_returns_all_when_fewer_than_max(self):
        matches = [_make_match() for _ in range(3)]
        result = _selector().select(matches, max_count=TOP_MISSIONS)
        assert len(result) == 3

    def test_returns_all_when_exactly_max(self):
        matches = [_make_match() for _ in range(TOP_MISSIONS)]
        result = _selector().select(matches)
        assert len(result) == TOP_MISSIONS

    def test_custom_max_count_respected(self):
        matches = [_make_match() for _ in range(20)]
        result = _selector().select(matches, max_count=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Tests — top N are the highest scores
# ---------------------------------------------------------------------------


class TestDigestMissionSelectorTopN:
    def test_top_3_are_highest_scored(self):
        scores = [0.9, 0.2, 0.8, 0.1, 0.7]
        matches = [_make_match(semantic_score=s) for s in scores]

        result = _selector().select(matches, max_count=3)
        result_scores = [m.final_score for m in result]

        assert result_scores[0] > result_scores[1] > result_scores[2]

    def test_top_missions_constant_is_10(self):
        assert TOP_MISSIONS == 10


# ---------------------------------------------------------------------------
# Tests — exclusion of already-sent missions
# ---------------------------------------------------------------------------


class TestDigestMissionSelectorExclusion:
    def test_excluded_match_is_removed_from_result(self):
        keep = _make_match(semantic_score=0.5)
        excluded = _make_match(semantic_score=0.9)

        result = _selector().select(
            [keep, excluded],
            excluded_analyzed_post_ids=frozenset({excluded.analyzed_post_id}),
        )

        assert result == [keep]

    def test_all_matches_excluded_returns_empty_list(self):
        matches = [_make_match() for _ in range(3)]
        excluded_ids = frozenset(m.analyzed_post_id for m in matches)

        result = _selector().select(matches, excluded_analyzed_post_ids=excluded_ids)

        assert result == []

    def test_top_n_recomputed_after_exclusion(self):
        matches = [_make_match(semantic_score=0.9 - i * 0.05) for i in range(12)]
        excluded_ids = frozenset(m.analyzed_post_id for m in matches[:3])

        result = _selector().select(matches, excluded_analyzed_post_ids=excluded_ids)

        assert len(result) == 9
        assert all(m.analyzed_post_id not in excluded_ids for m in result)
        result_scores = [m.final_score for m in result]
        assert result_scores == sorted(result_scores, reverse=True)

    def test_default_excluded_set_is_empty_and_preserves_existing_behavior(self):
        matches = [_make_match(semantic_score=0.9 - i * 0.1) for i in range(5)]
        result = _selector().select(matches)
        assert len(result) == 5
