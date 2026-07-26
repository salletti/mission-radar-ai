"""Strict JSON Schema for analyze_post, used with Groq's structured-outputs
constrained decoding (response_format={"type": "json_schema", ...}).

Mirrors the payload shape expected by PostAnalysis.from_llm_payload. Groq's
strict mode requires every property in `required` (including nullable ones,
typed as ["string", "null"]) and `additionalProperties: false`.
"""
from __future__ import annotations

ANALYZE_POST_JSON_SCHEMA: dict = {
    "type": "json_schema",
    "json_schema": {
        "name": "analyze_post_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "is_job_offer": {"type": "boolean"},
                "title": {"type": ["string", "null"]},
                "company": {"type": ["string", "null"]},
                "location": {"type": ["string", "null"]},
                "contract_type": {"type": ["string", "null"]},
                "summary": {"type": "string"},
                "required_skills": {"type": "array", "items": {"type": "string"}},
                "nice_to_have_skills": {"type": "array", "items": {"type": "string"}},
                "seniority": {"type": ["string", "null"]},
                "remote_policy": {"type": ["string", "null"]},
                "daily_rate": {"type": ["string", "null"]},
            },
            "required": [
                "is_job_offer",
                "title",
                "company",
                "location",
                "contract_type",
                "summary",
                "required_skills",
                "nice_to_have_skills",
                "seniority",
                "remote_policy",
                "daily_rate",
            ],
            "additionalProperties": False,
        },
    },
}
