from src.Domain.Entity.search_query import SearchQuery
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.ValueObject.contract_type import ContractType

_MAX_QUERIES = 5
_DEFAULT_LIMIT = 50
_DEFAULT_SOURCE = "linkedin"


def _join(*parts: str) -> str:
    return " ".join(p for p in parts if p)


class HeuristicSearchQueryGenerator:
    """Domain Service : derives SearchQuery list from a UserProfile.

    Pure — no I/O, no external dependencies. Called by Use Cases.
    ≈ Domain Service Symfony (service class in the Domain namespace).

    Rules:
      - Query 1: always from profile.title
      - Queries 2–N: from profile.skills.technologies (alphabetically sorted, first N)
      - "freelance" keyword added only for ContractType.FREELANCE
      - location appended only when non-empty
      - Exact duplicates removed
      - Total capped at _MAX_QUERIES (5)
    """

    def generate(self, profile: UserProfile) -> list[SearchQuery]:
        query_strings = self._build_query_strings(profile)
        return [
            SearchQuery(
                user_profile_id=profile.id,
                query=q,
                source=_DEFAULT_SOURCE,
                limit=_DEFAULT_LIMIT,
            )
            for q in query_strings
        ]

    def _build_query_strings(self, profile: UserProfile) -> list[str]:
        contract = "freelance" if profile.preferred_contract_type == ContractType.FREELANCE else ""
        location = (profile.location or "").lower().strip()

        seen: set[str] = set()
        results: list[str] = []

        def _add(text: str) -> None:
            q = _join(text.lower().strip(), contract, location)
            if q and q not in seen:
                seen.add(q)
                results.append(q)

        _add(profile.title)

        for skill in profile.skills.technologies:
            if len(results) >= _MAX_QUERIES:
                break
            _add(skill)

        return results
