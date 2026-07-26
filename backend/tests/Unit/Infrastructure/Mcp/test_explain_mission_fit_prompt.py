"""Unit tests for explain_mission_fit_prompt — pure text, no I/O, no fakes needed."""
from uuid import uuid4

from src.Infrastructure.Mcp.Prompt.explain_mission_fit_prompt import explain_mission_fit_prompt


def test_embeds_mission_match_id_in_the_tool_call_instruction() -> None:
    mission_match_id = uuid4()

    text = explain_mission_fit_prompt(mission_match_id)

    assert "explain_mission_match" in text
    assert str(mission_match_id) in text


def test_guides_plain_language_reframing_not_new_scoring() -> None:
    text = explain_mission_fit_prompt(uuid4())

    assert "matching_reasons" in text
    assert "missing_skills" in text
    assert "recommendations" in text
