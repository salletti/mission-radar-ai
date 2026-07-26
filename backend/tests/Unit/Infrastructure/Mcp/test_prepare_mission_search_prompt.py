"""Unit tests for prepare_mission_search_prompt — pure text, no I/O, no fakes needed."""
from src.Infrastructure.Mcp.Prompt.prepare_mission_search_prompt import prepare_mission_search_prompt


def test_always_checks_pipeline_freshness_first() -> None:
    text = prepare_mission_search_prompt()

    assert "mission-radar://pipeline" in text
    assert "search_mission_history" in text


def test_without_keyword_tells_model_to_browse_or_ask() -> None:
    text = prepare_mission_search_prompt(keyword=None)

    assert "keyword=None" in text


def test_with_keyword_embeds_it_in_the_tool_call_instruction() -> None:
    text = prepare_mission_search_prompt(keyword="kubernetes")

    assert 'keyword="kubernetes"' in text
