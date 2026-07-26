def analyze_profile_prompt() -> str:
    """MCP Prompt for analyze_profile — pure text, no dependencies. Never reads data
    itself: only tells the model which Resources to read and which dimensions to
    evaluate. Business logic (what makes a profile "good") stays out of scope —
    the model reasons over the raw Resource payloads."""
    return (
        "Read the `mission-radar://profile` Resource, then the `mission-radar://dashboard` "
        "Resource for market context (how many missions matched recently, average score).\n\n"
        "Analyze the profile along these dimensions:\n"
        "- Stack coverage: is `skills` broad enough, or narrowly focused on one technology?\n"
        "- TJM positioning: does `target_tjm` look realistic given `years_experience` and "
        "`title`, and given the average score / mission volume seen in the dashboard?\n"
        "- Contract & remote fit: does `preferred_contract_type` and `preferred_remote_mode` "
        "look consistent with the missions the dashboard suggests are available?\n"
        "- Completeness: are `location` and `availability` filled in and current?\n\n"
        "Summarize with concrete, actionable suggestions — not just a restatement of the "
        "profile fields."
    )
