"""Unit tests for prioritize_today_missions_prompt — pure text, no I/O, no fakes needed."""
from src.Infrastructure.Mcp.Prompt.prioritize_today_missions_prompt import prioritize_today_missions_prompt


def test_sequences_profile_missions_and_explain_tool() -> None:
    text = prioritize_today_missions_prompt()

    assert "mission-radar://profile" in text
    assert "mission-radar://missions" in text
    assert "explain_mission_match" in text


def test_stays_out_of_artifact_generation_scope() -> None:
    text = prioritize_today_missions_prompt()

    assert "Do not draft any outreach or application content" in text
