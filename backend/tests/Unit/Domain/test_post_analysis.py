import pytest

from src.Domain.Exception.domain_exceptions import EmptyAnalysisSummaryError
from src.Domain.ValueObject.post_analysis import PostAnalysis


def _make_result(**kwargs) -> PostAnalysis:
    defaults = {
        "summary": "Mission Python senior remote",
        "required_skills": (),
        "nice_to_have_skills": (),
        "is_job_offer": True,
    }
    return PostAnalysis(**{**defaults, **kwargs})


class TestPostAnalysis:
    def test_creation_valide(self):
        result = _make_result()
        assert result.summary == "Mission Python senior remote"
        assert result.required_skills == ()
        assert result.nice_to_have_skills == ()

    def test_is_job_offer_true(self):
        result = _make_result(is_job_offer=True)
        assert result.is_job_offer is True

    def test_is_job_offer_false(self):
        result = _make_result(is_job_offer=False)
        assert result.is_job_offer is False

    def test_is_job_offer_defaults_to_false(self):
        result = PostAnalysis(
            summary="Post quelconque",
            required_skills=(),
            nice_to_have_skills=(),
        )
        assert result.is_job_offer is False

    def test_champs_optionnels_absents(self):
        result = _make_result()
        assert result.title is None
        assert result.company is None
        assert result.location is None
        assert result.contract_type is None
        assert result.seniority is None
        assert result.remote_policy is None
        assert result.daily_rate is None

    def test_required_skills_toujours_tuple(self):
        result = _make_result(required_skills=("Python", "FastAPI"))
        assert isinstance(result.required_skills, tuple)

    def test_nice_to_have_skills_toujours_tuple(self):
        result = _make_result(nice_to_have_skills=("Docker",))
        assert isinstance(result.nice_to_have_skills, tuple)

    def test_summary_vide_refuse(self):
        with pytest.raises(EmptyAnalysisSummaryError):
            _make_result(summary="")

    def test_summary_whitespace_refuse(self):
        with pytest.raises(EmptyAnalysisSummaryError):
            _make_result(summary="   ")

    def test_est_frozen(self):
        result = _make_result()
        with pytest.raises(Exception):
            result.summary = "autre chose"  # type: ignore[misc]


class TestPostAnalysisFromLLMPayload:
    def test_from_payload_complet(self):
        payload = {
            "is_job_offer": True,
            "title": "Senior Python Developer",
            "company": "ACME",
            "location": "Paris",
            "contract_type": "Freelance",
            "summary": "Mission Python senior en full remote",
            "required_skills": ["Python", "FastAPI"],
            "nice_to_have_skills": ["Docker", "Kubernetes"],
            "seniority": "Senior",
            "remote_policy": "Full remote",
            "daily_rate": "600-700€/j",
        }
        result = PostAnalysis.from_llm_payload(payload)
        assert result.is_job_offer is True
        assert result.title == "Senior Python Developer"
        assert result.company == "ACME"
        assert result.location == "Paris"
        assert result.contract_type == "Freelance"
        assert result.summary == "Mission Python senior en full remote"
        assert result.required_skills == ("Python", "FastAPI")
        assert result.nice_to_have_skills == ("Docker", "Kubernetes")
        assert result.seniority == "Senior"
        assert result.remote_policy == "Full remote"
        assert result.daily_rate == "600-700€/j"

    def test_is_job_offer_false_in_payload(self):
        payload = {"is_job_offer": False, "summary": "Post de networking, pas une offre."}
        result = PostAnalysis.from_llm_payload(payload)
        assert result.is_job_offer is False

    def test_is_job_offer_absent_defaults_to_false(self):
        payload = {"summary": "Mission Python."}
        result = PostAnalysis.from_llm_payload(payload)
        assert result.is_job_offer is False

    def test_nettoyage_strings(self):
        payload = {
            "title": " Senior Python Developer ",
            "company": " ACME ",
            "summary": " Mission Python senior ",
        }
        result = PostAnalysis.from_llm_payload(payload)
        assert result.title == "Senior Python Developer"
        assert result.company == "ACME"
        assert result.summary == "Mission Python senior"

    def test_required_skills_nettoyees(self):
        payload = {
            "summary": "Mission backend",
            "required_skills": [" Python ", " FastAPI "],
        }
        result = PostAnalysis.from_llm_payload(payload)
        assert result.required_skills == ("Python", "FastAPI")

    def test_required_skills_absent_remplace_par_tuple_vide(self):
        payload = {"summary": "Mission backend"}
        result = PostAnalysis.from_llm_payload(payload)
        assert result.required_skills == ()

    def test_nice_to_have_absent_remplace_par_tuple_vide(self):
        payload = {"summary": "Mission backend"}
        result = PostAnalysis.from_llm_payload(payload)
        assert result.nice_to_have_skills == ()

    def test_champs_vides_deviennent_none(self):
        payload = {
            "summary": "Mission backend",
            "company": "",
            "location": "  ",
            "daily_rate": "",
        }
        result = PostAnalysis.from_llm_payload(payload)
        assert result.company is None
        assert result.location is None
        assert result.daily_rate is None

    def test_summary_absent_refuse(self):
        with pytest.raises(EmptyAnalysisSummaryError):
            PostAnalysis.from_llm_payload({})
