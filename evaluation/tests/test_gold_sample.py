"""Tests for GoldSample dataclass and load_gold_dataset() loader."""
import json
from pathlib import Path

import pytest

from models.gold_sample import GoldSample, load_gold_dataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_sample(**kwargs) -> dict:
    base = {
        "raw_post_id": "urn:li:activity:1111111111111111111",
        "post_content": "Mission freelance Python Senior chez Accenture, Paris, hybride, TJM 650€/j.",
        "expected_contract": "freelance",
        "expected_remote": "hybrid",
        "expected_stack": ["Python", "FastAPI"],
        "expected_company": "Accenture",
        "expected_title": "Développeur Python Senior",
        "expected_location": "Paris, France",
        "expected_tjm": 650.0,
        "expected_salary": None,
    }
    base.update(kwargs)
    return base


def _write_dataset(tmp_path: Path, samples: list[dict], version: str = "1.1") -> Path:
    path = tmp_path / "gold_dataset.json"
    path.write_text(
        json.dumps({"version": version, "samples": samples}),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Nominal loading
# ---------------------------------------------------------------------------


def test_load_valid_dataset_returns_gold_sample_list(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample()])
    samples = load_gold_dataset(path)
    assert len(samples) == 1
    assert isinstance(samples[0], GoldSample)


def test_load_empty_samples_returns_empty_list(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [])
    assert load_gold_dataset(path) == []


def test_loaded_samples_count_matches_json(tmp_path: Path) -> None:
    raw = [_make_valid_sample(raw_post_id=f"urn:li:activity:{i}") for i in range(5)]
    path = _write_dataset(tmp_path, raw)
    assert len(load_gold_dataset(path)) == 5


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------


def test_field_raw_post_id(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(raw_post_id="urn:li:activity:9999")])
    assert load_gold_dataset(path)[0].raw_post_id == "urn:li:activity:9999"


def test_field_expected_contract(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(expected_contract="permanent")])
    assert load_gold_dataset(path)[0].expected_contract == "permanent"


def test_field_expected_remote(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(expected_remote="full_remote")])
    assert load_gold_dataset(path)[0].expected_remote == "full_remote"


def test_field_expected_stack_normalized_to_lowercase(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(expected_stack=["Python", "FastAPI", "PostgreSQL"])])
    assert load_gold_dataset(path)[0].expected_stack == ["python", "fastapi", "postgresql"]


def test_field_expected_company_nullable(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(expected_company=None)])
    assert load_gold_dataset(path)[0].expected_company is None


def test_field_expected_tjm(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(expected_tjm=700.0)])
    assert load_gold_dataset(path)[0].expected_tjm == 700.0


def test_field_expected_salary_nullable(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(expected_salary=None)])
    assert load_gold_dataset(path)[0].expected_salary is None


def test_field_expected_salary_set(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(expected_salary=65000.0, expected_tjm=None)])
    sample = load_gold_dataset(path)[0]
    assert sample.expected_salary == 65000.0
    assert sample.expected_tjm is None


# ---------------------------------------------------------------------------
# Stack normalization
# ---------------------------------------------------------------------------


def test_stack_items_lowercased_on_load(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(expected_stack=["DOCKER", "Vue.js", "TypeScript"])])
    assert load_gold_dataset(path)[0].expected_stack == ["docker", "vue.js", "typescript"]


def test_stack_defaults_to_empty_list_when_absent(tmp_path: Path) -> None:
    sample = _make_valid_sample()
    del sample["expected_stack"]
    path = _write_dataset(tmp_path, [sample])
    assert load_gold_dataset(path)[0].expected_stack == []


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_duplicate_raw_post_id_raises_value_error(tmp_path: Path) -> None:
    same_id = "urn:li:activity:duplicate"
    path = _write_dataset(
        tmp_path,
        [
            _make_valid_sample(raw_post_id=same_id),
            _make_valid_sample(raw_post_id=same_id),
        ],
    )
    with pytest.raises(ValueError, match="Duplicate raw_post_id"):
        load_gold_dataset(path)


def test_empty_raw_post_id_raises_value_error(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(raw_post_id="")])
    with pytest.raises(ValueError, match="raw_post_id cannot be empty"):
        load_gold_dataset(path)


def test_whitespace_raw_post_id_raises_value_error(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(raw_post_id="   ")])
    with pytest.raises(ValueError, match="raw_post_id cannot be empty"):
        load_gold_dataset(path)


def test_missing_required_field_raises_value_error(tmp_path: Path) -> None:
    sample = _make_valid_sample()
    del sample["expected_contract"]
    path = _write_dataset(tmp_path, [sample])
    with pytest.raises(ValueError, match="Missing required field"):
        load_gold_dataset(path)


def test_missing_expected_remote_raises_value_error(tmp_path: Path) -> None:
    sample = _make_valid_sample()
    del sample["expected_remote"]
    path = _write_dataset(tmp_path, [sample])
    with pytest.raises(ValueError, match="Missing required field"):
        load_gold_dataset(path)


def test_missing_post_content_raises_value_error(tmp_path: Path) -> None:
    sample = _make_valid_sample()
    del sample["post_content"]
    path = _write_dataset(tmp_path, [sample])
    with pytest.raises(ValueError, match="Missing required field"):
        load_gold_dataset(path)


def test_empty_post_content_raises_value_error(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(post_content="")])
    with pytest.raises(ValueError, match="post_content cannot be empty"):
        load_gold_dataset(path)


def test_whitespace_post_content_raises_value_error(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(post_content="   ")])
    with pytest.raises(ValueError, match="post_content cannot be empty"):
        load_gold_dataset(path)


def test_field_post_content(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample(post_content="Mission Python freelance.")])
    assert load_gold_dataset(path)[0].post_content == "Mission Python freelance."


def test_unsupported_schema_version_raises_value_error(tmp_path: Path) -> None:
    path = _write_dataset(tmp_path, [_make_valid_sample()], version="99.0")
    with pytest.raises(ValueError, match="Unsupported gold dataset version"):
        load_gold_dataset(path)


def test_invalid_json_raises_json_decode_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(Exception):
        load_gold_dataset(path)


def test_file_not_found_raises_file_not_found_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_gold_dataset(tmp_path / "does_not_exist.json")
