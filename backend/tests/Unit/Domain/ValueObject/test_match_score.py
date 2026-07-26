import pytest

from src.Domain.Exception.domain_exceptions import InvalidScoreError
from src.Domain.ValueObject.match_score import MatchScore


def _score(**kwargs) -> MatchScore:
    defaults = dict(semantic_score=0.8, contract_score=0.6, remote_score=1.0, tjm_score=0.5)
    return MatchScore(**{**defaults, **kwargs})


class TestMatchScoreValidation:
    def test_valid_creation(self):
        score = _score()
        assert score.semantic_score == 0.8
        assert score.contract_score == 0.6
        assert score.remote_score == 1.0
        assert score.tjm_score == 0.5

    def test_boundary_zero_is_valid(self):
        score = _score(semantic_score=0.0)
        assert score.semantic_score == 0.0

    def test_boundary_one_is_valid(self):
        score = _score(semantic_score=1.0)
        assert score.semantic_score == 1.0

    def test_refuses_score_below_zero(self):
        with pytest.raises(InvalidScoreError):
            _score(semantic_score=-0.01)

    def test_refuses_score_above_one(self):
        with pytest.raises(InvalidScoreError):
            _score(contract_score=1.01)

    def test_refuses_each_field_independently(self):
        for field in ("semantic_score", "contract_score", "remote_score", "tjm_score"):
            with pytest.raises(InvalidScoreError):
                _score(**{field: 1.5})

    def test_is_frozen(self):
        score = _score()
        with pytest.raises(Exception):
            score.semantic_score = 0.5  # type: ignore[misc]


class TestMatchScoreFinalScore:
    def test_final_score_all_ones(self):
        score = MatchScore(semantic_score=1.0, contract_score=1.0, remote_score=1.0, tjm_score=1.0)
        assert score.final_score == pytest.approx(1.0)

    def test_final_score_all_zeros(self):
        score = MatchScore(semantic_score=0.0, contract_score=0.0, remote_score=0.0, tjm_score=0.0)
        assert score.final_score == pytest.approx(0.0)

    def test_final_score_semantic_weight(self):
        # semantic=1.0, weight=0.70 — others=0
        score = MatchScore(semantic_score=1.0, contract_score=0.0, remote_score=0.0, tjm_score=0.0)
        assert score.final_score == pytest.approx(0.70)

    def test_final_score_contract_weight(self):
        # contract=1.0, weight=0.15 — others=0
        score = MatchScore(semantic_score=0.0, contract_score=1.0, remote_score=0.0, tjm_score=0.0)
        assert score.final_score == pytest.approx(0.15)

    def test_final_score_remote_weight(self):
        # remote=1.0, weight=0.10 — others=0
        score = MatchScore(semantic_score=0.0, contract_score=0.0, remote_score=1.0, tjm_score=0.0)
        assert score.final_score == pytest.approx(0.10)

    def test_final_score_tjm_weight(self):
        # tjm=1.0, weight=0.05 — others=0
        score = MatchScore(semantic_score=0.0, contract_score=0.0, remote_score=0.0, tjm_score=1.0)
        assert score.final_score == pytest.approx(0.05)

    def test_final_score_rounded_to_4_decimals(self):
        # 0.9 * 0.70 + 0.8 * 0.15 + 0.7 * 0.10 + 0.6 * 0.05 = 0.63 + 0.12 + 0.07 + 0.03 = 0.85
        score = MatchScore(semantic_score=0.9, contract_score=0.8, remote_score=0.7, tjm_score=0.6)
        assert score.final_score == pytest.approx(0.85, abs=1e-4)
        assert isinstance(score.final_score, float)
        # verify at most 4 decimal places
        assert len(str(score.final_score).split(".")[-1]) <= 4

    def test_complete_example_from_spec(self):
        # Spec example: semantic=0.9, contract=1.0, remote=1.0, tjm=1.0
        # 0.9*0.70 + 1.0*0.15 + 1.0*0.10 + 1.0*0.05 = 0.630 + 0.150 + 0.100 + 0.050 = 0.9300
        score = MatchScore(semantic_score=0.9, contract_score=1.0, remote_score=1.0, tjm_score=1.0)
        assert score.final_score == pytest.approx(0.9300)
