from uuid import uuid4

import pytest

from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.ValueObject.match_score import MatchScore


def _match_score(**kwargs) -> MatchScore:
    defaults = dict(semantic_score=0.8, contract_score=0.9, remote_score=1.0, tjm_score=0.6)
    return MatchScore(**{**defaults, **kwargs})


class TestMissionMatchFactory:
    def test_factory_generates_id(self):
        match = MissionMatch.create(uuid4(), uuid4(), _match_score())
        assert match.id is not None

    def test_factory_generates_unique_ids(self):
        score = _match_score()
        a = MissionMatch.create(uuid4(), uuid4(), score)
        b = MissionMatch.create(uuid4(), uuid4(), score)
        assert a.id != b.id

    def test_factory_sets_created_at(self):
        match = MissionMatch.create(uuid4(), uuid4(), _match_score())
        assert match.created_at is not None

    def test_factory_stores_user_profile_id(self):
        user_id = uuid4()
        match = MissionMatch.create(user_id, uuid4(), _match_score())
        assert match.user_profile_id == user_id

    def test_factory_stores_analyzed_post_id(self):
        post_id = uuid4()
        match = MissionMatch.create(uuid4(), post_id, _match_score())
        assert match.analyzed_post_id == post_id

    def test_factory_stores_match_score(self):
        score = _match_score()
        match = MissionMatch.create(uuid4(), uuid4(), score)
        assert match.match_score == score


class TestMissionMatchFinalScore:
    def test_final_score_delegates_to_match_score(self):
        score = _match_score()
        match = MissionMatch.create(uuid4(), uuid4(), score)
        assert match.final_score == score.final_score

    def test_final_score_reflects_match_score_components(self):
        score = _match_score(semantic_score=1.0, contract_score=0.0, remote_score=0.0, tjm_score=0.0)
        match = MissionMatch.create(uuid4(), uuid4(), score)
        assert match.final_score == pytest.approx(0.70)


class TestMissionMatchImmutability:
    def test_match_score_is_not_copied(self):
        score = _match_score()
        match = MissionMatch.create(uuid4(), uuid4(), score)
        assert match.match_score is score
