from dataclasses import dataclass


@dataclass(frozen=True)
class LookupUserByEmailQuery:
    email: str
