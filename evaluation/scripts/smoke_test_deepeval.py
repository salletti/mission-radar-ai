"""Smoke test — one real DeepEval evaluation call against Groq.

Not part of the automated test suite (evaluation/tests/ uses fakes only,
zero LLM calls). This script makes exactly one real network call to Groq to
prove the DeepEvalAdapter wiring works end-to-end. Used by the manual
"Evaluation" GitHub Actions workflow (workflow_dispatch only — never runs
on push/PR).

Usage:
    GROQ_API_KEY=xxx python evaluation/scripts/smoke_test_deepeval.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

_EVAL_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_CANDIDATES = (_EVAL_ROOT.parent / "backend", _EVAL_ROOT.parent)
for _candidate in _BACKEND_CANDIDATES:
    if (_candidate / "src").is_dir():
        sys.path.insert(0, str(_candidate))
        break
sys.path.insert(0, str(_EVAL_ROOT))

from src.Domain.Entity.analyzed_post import AnalyzedPost  # noqa: E402
from src.Domain.Entity.raw_post import RawPost  # noqa: E402
from src.Domain.ValueObject.contract_type import ContractType  # noqa: E402
from src.Domain.ValueObject.remote_mode import RemoteMode  # noqa: E402
from integrations.deepeval.deepeval_adapter import DeepEvalAdapter  # noqa: E402


def main() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    raw_post = RawPost(
        source="linkedin",
        external_id="smoke-test-1",
        author_name="Recruiter",
        author_url="",
        content="Mission Python Senior freelance Paris hybride 650€/j",
        post_url="",
        published_at=datetime.now(timezone.utc),
        scraped_at=datetime.now(timezone.utc),
    )
    analyzed_post = AnalyzedPost(
        raw_post_id=uuid4(),
        summary="Mission freelance Python Senior à Paris",
        detected_stack=("python", "fastapi"),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.HYBRID,
        title="Développeur Python Senior",
        company="Accenture",
        location="Paris",
        detected_tjm=650.0,
    )

    adapter = DeepEvalAdapter(groq_api_key=api_key)
    report = asyncio.run(adapter.evaluate(raw_post, analyzed_post))
    print(report)


if __name__ == "__main__":
    main()
