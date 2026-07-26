"""Unit tests for refresh_and_prioritize_missions_prompt — pure text, no I/O, no fakes needed."""
from src.Infrastructure.Mcp.Prompt.refresh_and_prioritize_missions_prompt import (
    refresh_and_prioritize_missions_prompt,
)


def test_triggers_refresh_before_reading_pipeline_status() -> None:
    text = refresh_and_prioritize_missions_prompt()

    assert text.index("start_mission_refresh") < text.index("mission-radar://pipeline")


def test_sequences_profile_missions_and_explain_tool_after_completion() -> None:
    text = refresh_and_prioritize_missions_prompt()

    assert "mission-radar://profile" in text
    assert "mission-radar://missions" in text
    assert "explain_mission_match" in text


def test_handles_already_running_pipeline_gracefully() -> None:
    text = refresh_and_prioritize_missions_prompt()

    assert "already running" in text


def test_stops_on_failed_status() -> None:
    text = refresh_and_prioritize_missions_prompt()

    assert "failed" in text
    assert "error_message" in text


def test_stays_out_of_artifact_generation_scope() -> None:
    text = refresh_and_prioritize_missions_prompt()

    assert "Do not draft any outreach or application content" in text
