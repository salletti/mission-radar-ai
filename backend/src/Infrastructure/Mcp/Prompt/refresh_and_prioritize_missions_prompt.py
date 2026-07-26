def refresh_and_prioritize_missions_prompt() -> str:
    """MCP Prompt for refresh_and_prioritize_missions — pure text, no dependencies. Never
    triggers or polls anything itself: only sequences the start_mission_refresh Tool call,
    a pipeline status check, and the same Resources/Tool as prioritize_today_missions."""
    return (
        "First, call the `start_mission_refresh` Tool to trigger a fresh mission search. If "
        "it raises an error because a pipeline is already running for this user, that's "
        "expected — skip triggering and move on to checking its status instead of retrying.\n\n"
        "Then read `mission-radar://pipeline` to check progress. If `last_run.status` is not "
        "yet `completed` or `failed`, tell the user the refresh is still running and stop "
        "here — do not poll in a tight loop, wait for the user to ask again.\n\n"
        "If `last_run.status` is `failed`, tell the user the refresh failed (mention "
        "`error_message` if present) and stop here.\n\n"
        "Once `last_run.status` is `completed`, read `mission-radar://profile` for context "
        "(target TJM, preferred contract type, remote preference, skills), then "
        "`mission-radar://missions` for today's top-scored missions. Sort by `global_score`, "
        "and for the 2-3 highest-scored ones, call `explain_mission_match` with their "
        "`mission_match_id` to get the score breakdown and matched/missing skills.\n\n"
        "Produce a ranked shortlist: for each mission, give its title, company, score, and a "
        "one-line reason (from the explanation) why it deserves attention today. Do not draft "
        "any outreach or application content — this Prompt only helps the user decide what to "
        "look at first after a fresh refresh."
    )
