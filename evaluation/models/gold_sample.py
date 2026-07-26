from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_SCHEMA_VERSION = "1.1"


@dataclass
class GoldSample:
    """Manually annotated LinkedIn post — ground truth for AI evaluation."""

    raw_post_id: str
    post_content: str  # the LinkedIn post text to feed the extraction pipeline
    expected_contract: str  # "freelance" | "permanent" | "fixed_term" | "unknown"
    expected_remote: str  # "full_remote" | "hybrid" | "onsite" | "unknown"
    expected_stack: list[str]  # normalized to lowercase
    expected_company: str | None = None
    expected_title: str | None = None
    expected_location: str | None = None
    expected_tjm: float | None = None
    expected_salary: float | None = None


def load_gold_dataset(path: Path) -> list[GoldSample]:
    """Load and validate GoldSample records from a versioned JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))

    version = data.get("version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(f"Unsupported gold dataset version: {version!r}")

    seen_ids: set[str] = set()
    samples: list[GoldSample] = []
    for item in data.get("samples", []):
        sample = _parse_sample(item)
        if sample.raw_post_id in seen_ids:
            raise ValueError(f"Duplicate raw_post_id: {sample.raw_post_id!r}")
        seen_ids.add(sample.raw_post_id)
        samples.append(sample)

    return samples


def _parse_sample(item: dict) -> GoldSample:
    try:
        raw_post_id = item["raw_post_id"]
        post_content = item["post_content"]
        expected_contract = item["expected_contract"]
        expected_remote = item["expected_remote"]
    except KeyError as exc:
        raise ValueError(f"Missing required field in gold sample: {exc}") from exc

    if not raw_post_id or not raw_post_id.strip():
        raise ValueError("raw_post_id cannot be empty")

    if not post_content or not post_content.strip():
        raise ValueError("post_content cannot be empty")

    return GoldSample(
        raw_post_id=raw_post_id,
        post_content=post_content,
        expected_contract=expected_contract,
        expected_remote=expected_remote,
        expected_stack=[t.lower() for t in item.get("expected_stack", [])],
        expected_company=item.get("expected_company"),
        expected_title=item.get("expected_title"),
        expected_location=item.get("expected_location"),
        expected_tjm=item.get("expected_tjm"),
        expected_salary=item.get("expected_salary"),
    )
