"""Manual test script for the CV extraction pipeline.

Usage:
    python scripts/test_cv_extraction.py path/to/cv.pdf

Requires:
    GROQ_API_KEY environment variable set.
"""
import asyncio
import os
import sys
from pprint import pprint

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.Infrastructure.External.CV.pdfminer_cv_extractor_gateway import (
    PdfMinerCVExtractorGateway,
)
from src.Infrastructure.External.LLM.groq_llm_gateway import GroqLLMGateway
from src.Infrastructure.External.Observability.langfuse.factory import get_langfuse_tracer


async def main(file_path: str) -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting text from: {file_path}")
    cv_extractor = PdfMinerCVExtractorGateway()
    cv_text = await cv_extractor.extract_text(file_path)
    print(f"Extracted {len(cv_text)} characters.\n")

    print("Calling Groq LLM...")
    llm = GroqLLMGateway(api_key=api_key, tracer=get_langfuse_tracer())
    profile = await llm.extract_profile_from_cv(cv_text)

    print("\n--- CVProfile extracted ---")
    pprint(
        {
            "email": profile.email,
            "full_name": profile.full_name,
            "title": profile.title,
            "years_experience": profile.years_experience,
            "preferred_contract_type": profile.preferred_contract_type,
            "target_tjm": profile.target_tjm,
            "preferred_remote_mode": profile.preferred_remote_mode,
            "skills": list(profile.skills),
            "availability": profile.availability.isoformat(),
            "location": profile.location,
        }
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} path/to/cv.pdf", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
