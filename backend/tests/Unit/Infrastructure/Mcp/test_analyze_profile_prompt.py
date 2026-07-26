"""Unit tests for analyze_profile_prompt — pure text, no I/O, no fakes needed."""
from src.Infrastructure.Mcp.Prompt.analyze_profile_prompt import analyze_profile_prompt


def test_references_profile_and_dashboard_resources() -> None:
    text = analyze_profile_prompt()

    assert "mission-radar://profile" in text
    assert "mission-radar://dashboard" in text


def test_lists_analysis_dimensions() -> None:
    text = analyze_profile_prompt()

    assert "target_tjm" in text
    assert "skills" in text
    assert "preferred_remote_mode" in text
