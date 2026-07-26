"""Compare analyze_post extraction quality between two Groq models on the gold dataset:

- llama-3.3-70b-versatile (baseline, JSON mode, no schema guarantee)
- openai/gpt-oss-20b       (candidate, strict json_schema / constrained decoding)

Both models are on Groq's free tier — this is a quality comparison, not a cost
tradeoff. Reuses the existing evaluation infrastructure (EvaluationEngine,
ExtractionMetricsCalculator) as-is; this script only wires two model arms and
reports the results side by side.

Usage:
    GROQ_API_KEY=xxx python evaluation/scripts/compare_groq_models.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_EVAL_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_CANDIDATES = (_EVAL_ROOT.parent / "backend", _EVAL_ROOT.parent)
for _candidate in _BACKEND_CANDIDATES:
    if (_candidate / "src").is_dir():
        sys.path.insert(0, str(_candidate))
        break
sys.path.insert(0, str(_EVAL_ROOT))

from models.evaluation_report import EvaluationReport  # noqa: E402
from models.gold_sample import GoldSample, load_gold_dataset  # noqa: E402
from metrics.extraction_metrics_calculator import ExtractionMetricsCalculator  # noqa: E402
from runners.evaluation_engine import EvaluationEngine  # noqa: E402
from src.Domain.Entity.raw_post import RawPost  # noqa: E402
from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import (  # noqa: E402
    SentenceTransformerEmbeddingGateway,
)
from src.Infrastructure.External.LLM.groq_llm_gateway import GroqLLMGateway  # noqa: E402

GOLD_DATASET_PATH = _EVAL_ROOT / "datasets" / "gold_dataset.json"
REPORTS_DIR = _EVAL_ROOT / "reports"
THROTTLE_SECONDS = 1.0  # Groq free tier rate limits

MODELS: dict[str, dict] = {
    "llama-3.3-70b-versatile (json_object)": {
        "model": "llama-3.3-70b-versatile",
        "strict_json_schema": False,
    },
    "openai/gpt-oss-20b (strict json_schema)": {
        "model": "openai/gpt-oss-20b",
        "strict_json_schema": True,
    },
}


@dataclass
class ArmReport:
    label: str
    model_kwargs: dict
    extraction_report: EvaluationReport | None
    results: list = field(default_factory=list)  # list[EvaluationResult], per successful sample
    failures: list[tuple[str, str]] = field(default_factory=list)
    n_samples: int = 0

    @property
    def failure_rate(self) -> float:
        return len(self.failures) / self.n_samples if self.n_samples else 0.0


def _raw_post_from_sample(sample: GoldSample) -> RawPost:
    now = datetime.now(timezone.utc)
    return RawPost(
        source="linkedin",
        external_id=sample.raw_post_id,
        author_name="unknown",
        author_url="",
        content=sample.post_content,
        post_url="",
        published_at=now,
        scraped_at=now,
    )


async def run_arm(
    label: str,
    model_kwargs: dict,
    samples: list[GoldSample],
    embedding_gateway: SentenceTransformerEmbeddingGateway,
    api_key: str,
) -> ArmReport:
    print(f"\n=== Running arm: {label} ===")
    gateway = GroqLLMGateway(api_key=api_key, **model_kwargs)
    engine = EvaluationEngine(llm_gateway=gateway, embedding_gateway=embedding_gateway)

    results = []
    failures: list[tuple[str, str]] = []
    for sample in samples:
        raw_post = _raw_post_from_sample(sample)
        try:
            results.append(await engine.evaluate_sample(sample, raw_post))
            print(f"  OK   {sample.raw_post_id}")
        except Exception as exc:  # noqa: BLE001 — one failing sample must not abort the campaign
            failures.append((sample.raw_post_id, repr(exc)))
            print(f"  FAIL {sample.raw_post_id}: {exc!r}")
        await asyncio.sleep(THROTTLE_SECONDS)

    extraction_report = ExtractionMetricsCalculator().calculate(results) if results else None
    return ArmReport(
        label=label,
        model_kwargs=model_kwargs,
        extraction_report=extraction_report,
        results=results,
        failures=failures,
        n_samples=len(samples),
    )


def print_comparison_table(arms: list[ArmReport]) -> None:
    print("\n=== Comparaison ===")
    header = "metric".ljust(22) + "".join(a.label.ljust(42) for a in arms)
    print(header)
    print("-" * len(header))

    def row(label: str, values: list[str]) -> str:
        return label.ljust(22) + "".join(v.ljust(42) for v in values)

    print(row("échecs extraction", [f"{len(a.failures)}/{a.n_samples}" for a in arms]))
    for field_name, attr in [
        ("overall_accuracy", "overall_accuracy"),
        ("company_accuracy", "company_accuracy"),
        ("title_accuracy", "title_accuracy"),
        ("contract_accuracy", "contract_accuracy"),
        ("location_accuracy", "location_accuracy"),
        ("remote_accuracy", "remote_accuracy"),
        ("tjm_accuracy", "tjm_accuracy"),
        ("stack_precision", "stack_precision"),
        ("stack_recall", "stack_recall"),
        ("stack_f1", "stack_f1"),
    ]:
        values = [
            f"{getattr(a.extraction_report.extraction_metrics, attr):.3f}" if a.extraction_report else "n/a"
            for a in arms
        ]
        print(row(field_name, values))


def build_markdown_report(arms: list[ArmReport], generated_at: datetime) -> str:
    lines = [
        "# Comparaison Groq — llama-3.3-70b-versatile vs openai/gpt-oss-20b (strict)",
        "",
        f"- Généré le : {generated_at.isoformat()}",
        f"- Gold dataset : `{GOLD_DATASET_PATH.relative_to(_EVAL_ROOT.parent)}`",
        f"- Échantillons : {arms[0].n_samples if arms else 0}",
        f"- Modèles comparés : {', '.join(a.label for a in arms)}",
        "",
        "## Métriques",
        "",
    ]

    header_cells = ["Métrique"] + [a.label for a in arms]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("|" + "---|" * len(header_cells))

    lines.append(
        "| Échecs d'extraction | "
        + " | ".join(f"{len(a.failures)}/{a.n_samples}" for a in arms)
        + " |"
    )

    metric_rows = [
        ("Overall accuracy", "overall_accuracy"),
        ("Company accuracy", "company_accuracy"),
        ("Title accuracy", "title_accuracy"),
        ("Contract accuracy", "contract_accuracy"),
        ("Location accuracy", "location_accuracy"),
        ("Remote accuracy", "remote_accuracy"),
        ("TJM accuracy", "tjm_accuracy"),
        ("Stack precision", "stack_precision"),
        ("Stack recall", "stack_recall"),
        ("Stack F1", "stack_f1"),
    ]
    for display_name, attr in metric_rows:
        cells = [
            f"{getattr(a.extraction_report.extraction_metrics, attr):.3f}" if a.extraction_report else "n/a"
            for a in arms
        ]
        lines.append(f"| {display_name} | " + " | ".join(cells) + " |")

    lines += ["", "## Échecs d'extraction par modèle", ""]
    for arm in arms:
        lines.append(f"### {arm.label}")
        if not arm.failures:
            lines.append("Aucun échec.")
        else:
            for raw_post_id, error in arm.failures:
                lines.append(f"- `{raw_post_id}` — {error}")
        lines.append("")

    lines += ["## Détail par échantillon (champs en écart)", ""]
    for arm in arms:
        lines.append(f"### {arm.label}")
        mismatches = [r for r in arm.results if not _result_is_perfect(r)]
        if not mismatches:
            lines.append("Aucun écart — tous les champs corrects sur tous les échantillons.")
        else:
            for result in mismatches:
                lines.append(f"- `{result.sample_id}`")
                for field_name in ("company", "title", "contract", "location", "remote", "tjm"):
                    fr = getattr(result, field_name)
                    if not fr.correct:
                        lines.append(f"  - {field_name} : attendu={fr.expected!r} / obtenu={fr.actual!r}")
                if not result.stack.correct:
                    if result.stack.missing:
                        lines.append(f"  - stack manquant : {result.stack.missing}")
                    if result.stack.unexpected:
                        lines.append(f"  - stack inattendu : {result.stack.unexpected}")
        lines.append("")

    lines += [
        "## Limites connues",
        "",
        "- 8 des 16 échantillons sont rédigés (texte propre) et 8 sont issus de vrais posts LinkedIn "
        "(fixtures Apify `linkedin_posts_python_freelance_paris.json`, mode `APIFY_PROVIDER=mock`) — "
        "TJM/company y sont souvent `null` (annotés honnêtement, valeur non exploitable dans le texte "
        "source réel).",
        "- Métrique \"mission recall\" non calculée — le gold dataset ne contient que des échantillons "
        "positifs (16/16 missions).",
        "- Scope limité à la qualité d'extraction (accuracy champs, précision/recall stack, taux d'échec "
        "JSON) — pas de comparaison DeepEval (hallucination/faithfulness) dans cette itération.",
        "- La comparaison de champs textuels (title, company, location) est une égalité stricte "
        "(insensible à la casse) — une reformulation sémantiquement correcte mais différente du libellé "
        "attendu compte comme incorrecte.",
    ]
    return "\n".join(lines) + "\n"


def _result_is_perfect(result) -> bool:
    scalar_fields = ("company", "title", "contract", "location", "remote", "tjm")
    return all(getattr(result, f).correct for f in scalar_fields) and result.stack.correct


async def main() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    samples = load_gold_dataset(GOLD_DATASET_PATH)
    embedding_gateway = SentenceTransformerEmbeddingGateway()

    arms = []
    for label, model_kwargs in MODELS.items():
        arm = await run_arm(label, model_kwargs, samples, embedding_gateway, api_key)
        arms.append(arm)

    print_comparison_table(arms)

    generated_at = datetime.now(timezone.utc)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"groq_model_comparison_{generated_at.strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(build_markdown_report(arms, generated_at), encoding="utf-8")
    print(f"\nRapport Markdown sauvegardé : {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
