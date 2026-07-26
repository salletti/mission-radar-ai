def prioritize_today_missions_prompt() -> str:
    """MCP Prompt for prioritize_today_missions — pure text, no dependencies. Never
    ranks or explains missions itself: only sequences the Resources/Tool calls
    (profile for context, missions for the candidate list, explain_mission_match
    for the top few) that the model needs to help the user prioritize."""
    return (
        "Read `mission-radar://profile` for context (target TJM, preferred contract "
        "type, remote preference, skills), then `mission-radar://missions` for today's "
        "top-scored missions.\n\n"
        "Sort the missions by `global_score`, and for the 2-3 highest-scored ones, call "
        "`explain_mission_match` with their `mission_match_id` to get the score "
        "breakdown and matched/missing skills.\n\n"
        "Produce a ranked shortlist: for each mission, give its title, company, score, "
        "and a one-line reason (from the explanation) why it deserves attention today. "
        "If two missions score similarly, use the profile context (TJM fit, remote "
        "match, stack overlap) to break the tie and explain the choice. Do not draft "
        "any outreach or application content — this Prompt only helps the user decide "
        "what to look at first."
    )
