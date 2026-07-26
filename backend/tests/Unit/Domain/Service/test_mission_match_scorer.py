"""Unit tests for MissionMatchScorer — no I/O, no real embeddings, no DB."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Service.mission_match_scorer import MissionMatchScorer
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)
_UNSET = object()  # sentinel to distinguish "not provided" from explicit None


# ---------------------------------------------------------------------------
# Fake
# ---------------------------------------------------------------------------


class FakeEmbeddingGateway(EmbeddingGateway):
    def __init__(self, similarity: float = 0.9) -> None:
        self._similarity = similarity

    async def embed_text(self, text: str) -> list[float]:
        return [0.1] * 384

    async def compute_similarity(self, embedding_a: list[float], embedding_b: list[float]) -> float:
        return self._similarity


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_profile(
    contract_type: ContractType = ContractType.FREELANCE,
    remote_mode: RemoteMode = RemoteMode.FULL_REMOTE,
    target_tjm: float = 700.0,
    embedding: object = _UNSET,
) -> UserProfile:
    resolved_embedding = [0.1] * 384 if embedding is _UNSET else embedding  # type: ignore[assignment]
    return UserProfile(
        email=f"{uuid4()}@test.com",
        full_name="Test User",
        title="Senior Python Engineer",
        years_experience=10,
        preferred_contract_type=contract_type,
        target_tjm=target_tjm,
        preferred_remote_mode=remote_mode,
        skills=Stack.from_list(["python", "fastapi"]),
        availability=_AVAILABILITY,
        embedding=resolved_embedding,
    )


def _make_mission(
    contract_type: ContractType = ContractType.FREELANCE,
    remote_mode: RemoteMode = RemoteMode.FULL_REMOTE,
    detected_tjm: float | None = 700.0,
    embedding: object = _UNSET,
) -> AnalyzedPost:
    resolved_embedding = [0.1] * 384 if embedding is _UNSET else embedding  # type: ignore[assignment]
    return AnalyzedPost(
        raw_post_id=uuid4(),
        summary="Mission Python full remote.",
        detected_contract_type=contract_type,
        detected_remote_mode=remote_mode,
        detected_tjm=detected_tjm,
        embedding=resolved_embedding,
    )


def _scorer(similarity: float = 0.9) -> MissionMatchScorer:
    return MissionMatchScorer(embedding_gateway=FakeEmbeddingGateway(similarity=similarity))


# ---------------------------------------------------------------------------
# Tests — 5 cas spec + cas limites
# ---------------------------------------------------------------------------


class TestMissionMatchScorerCasPrincipaux:
    @pytest.mark.asyncio
    async def test_cas1_profil_parfait(self):
        """Cas 1 — tout compatible, similarité haute → final_score > 0.9."""
        scorer = _scorer(similarity=0.9)
        profile = _make_profile()
        mission = _make_mission()

        result = await scorer.calculate(profile, mission)

        # 0.9*0.70 + 1.0*0.15 + 1.0*0.10 + 1.0*0.05 = 0.93
        assert result.final_score == pytest.approx(0.93)
        assert result.final_score > 0.9

    @pytest.mark.asyncio
    async def test_cas2_contrat_incompatible(self):
        """Cas 2 — contrat PERMANENT vs FREELANCE → score inférieur au cas 1."""
        scorer = _scorer(similarity=0.9)
        profile = _make_profile(contract_type=ContractType.FREELANCE)
        mission = _make_mission(contract_type=ContractType.PERMANENT)

        result = await scorer.calculate(profile, mission)

        assert result.contract_score == 0.0
        assert result.final_score < 0.93

    @pytest.mark.asyncio
    async def test_cas3_remote_incompatible(self):
        """Cas 3 — FULL_REMOTE vs ONSITE → score inférieur au cas 1."""
        scorer = _scorer(similarity=0.9)
        profile = _make_profile(remote_mode=RemoteMode.FULL_REMOTE)
        mission = _make_mission(remote_mode=RemoteMode.ONSITE)

        result = await scorer.calculate(profile, mission)

        assert result.remote_score == 0.0
        assert result.final_score < 0.93

    @pytest.mark.asyncio
    async def test_cas4_tjm_tres_eloigne(self):
        """Cas 4 — écart TJM 300 € (> tolérance 200 €) → tjm_score = 0.0."""
        scorer = _scorer(similarity=0.9)
        profile = _make_profile(target_tjm=700.0)
        mission = _make_mission(detected_tjm=400.0)

        result = await scorer.calculate(profile, mission)

        assert result.tjm_score == 0.0
        assert result.final_score < 0.93

    @pytest.mark.asyncio
    async def test_cas5_embedding_faible(self):
        """Cas 5 — similarité sémantique très basse → final_score fortement dégradé."""
        scorer = _scorer(similarity=0.1)
        profile = _make_profile()
        mission = _make_mission()

        result = await scorer.calculate(profile, mission)

        assert result.semantic_score == pytest.approx(0.1)
        # 0.1*0.70 + 1.0*0.15 + 1.0*0.10 + 1.0*0.05 = 0.37
        assert result.final_score < 0.4


class TestMissionMatchScorerCasLimites:
    @pytest.mark.asyncio
    async def test_embedding_profile_none_retourne_zero(self):
        scorer = _scorer()
        profile = _make_profile(embedding=None)
        mission = _make_mission()

        result = await scorer.calculate(profile, mission)

        assert result.semantic_score == 0.0

    @pytest.mark.asyncio
    async def test_embedding_mission_none_retourne_zero(self):
        scorer = _scorer()
        profile = _make_profile()
        mission = _make_mission(embedding=None)

        result = await scorer.calculate(profile, mission)

        assert result.semantic_score == 0.0

    @pytest.mark.asyncio
    async def test_contract_unknown_neutre(self):
        scorer = _scorer()
        mission = _make_mission(contract_type=ContractType.UNKNOWN)

        result = await scorer.calculate(_make_profile(), mission)

        assert result.contract_score == 0.5

    @pytest.mark.asyncio
    async def test_remote_unknown_neutre(self):
        scorer = _scorer()
        mission = _make_mission(remote_mode=RemoteMode.UNKNOWN)

        result = await scorer.calculate(_make_profile(), mission)

        assert result.remote_score == 0.5

    @pytest.mark.asyncio
    async def test_tjm_none_neutre(self):
        scorer = _scorer()
        mission = _make_mission(detected_tjm=None)

        result = await scorer.calculate(_make_profile(), mission)

        assert result.tjm_score == 0.5

    @pytest.mark.asyncio
    async def test_tjm_ecart_zero(self):
        scorer = _scorer()
        profile = _make_profile(target_tjm=700.0)
        mission = _make_mission(detected_tjm=700.0)

        result = await scorer.calculate(profile, mission)

        assert result.tjm_score == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_tjm_ecart_100_euros(self):
        scorer = _scorer()
        profile = _make_profile(target_tjm=700.0)
        mission = _make_mission(detected_tjm=600.0)

        result = await scorer.calculate(profile, mission)

        assert result.tjm_score == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_tjm_ecart_200_euros_donne_zero(self):
        scorer = _scorer()
        profile = _make_profile(target_tjm=700.0)
        mission = _make_mission(detected_tjm=500.0)

        result = await scorer.calculate(profile, mission)

        assert result.tjm_score == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_retourne_match_score_value_object(self):
        from src.Domain.ValueObject.match_score import MatchScore

        scorer = _scorer()
        result = await scorer.calculate(_make_profile(), _make_mission())

        assert isinstance(result, MatchScore)
