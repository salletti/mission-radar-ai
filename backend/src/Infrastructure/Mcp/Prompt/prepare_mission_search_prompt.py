def prepare_mission_search_prompt(keyword: str | None = None) -> str:
    """MCP Prompt for prepare_mission_search — pure text, no dependencies. Never
    searches itself: only sequences the freshness check before the actual search
    Tool call, and passes the caller's keyword through as text."""
    keyword_instruction = (
        f'Then call the `search_mission_history` Tool with `keyword="{keyword}"`.'
        if keyword
        else "Then call the `search_mission_history` Tool with `keyword=None` to browse "
        "the full history unfiltered, or ask the user what keyword (title, company, "
        "or technology) they want to search for."
    )
    return (
        "Before searching, read the `mission-radar://pipeline` Resource to check data "
        "freshness. If `last_run` is `None`, or its `finished_at` looks old, tell the "
        "user their mission data may be stale before presenting any search results — "
        "searching on stale data can give a false sense of completeness.\n\n"
        f"{keyword_instruction}\n\n"
        "Present results ranked by `global_score`, and mention `detected_stack` and "
        "`detected_tjm` for each match so the user can quickly judge relevance."
    )
