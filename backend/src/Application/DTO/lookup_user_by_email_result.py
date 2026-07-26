from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LookupUserByEmailResult:
    exists: bool
    user_id: Optional[str]
