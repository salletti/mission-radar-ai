from uuid import UUID


def explain_mission_fit_prompt(mission_match_id: UUID) -> str:
    """MCP Prompt for explain_mission_fit — pure text, no dependencies. Never
    computes the explanation itself: only tells the model to call the existing
    `explain_mission_match` Tool and how to reframe its structured output for a
    human decision, without inventing new scoring criteria."""
    return (
        f"Call the `explain_mission_match` Tool with `mission_match_id=\"{mission_match_id}\"`.\n\n"
        "Reframe the structured result as a plain-language explanation aimed at helping "
        "the user decide whether to pursue this mission:\n"
        "- Lead with `matching_reasons` and `matched_skills` — what makes this a good fit.\n"
        "- Be honest about `missing_skills` and `warnings` — don't downplay them.\n"
        "- Use `score_breakdown` to explain *why* the score is what it is (which "
        "dimension — skills, experience, location, contract, daily rate — drove it "
        "up or down), not just restate the number.\n"
        "- Close with the Tool's own `recommendations`, not a new verdict you invent.\n\n"
        "Avoid jargon from the scoring internals (e.g. raw weight percentages) — "
        "translate them into what they mean for this specific mission."
    )
