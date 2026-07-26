from dataclasses import dataclass


@dataclass(frozen=True)
class Stack:
    """Normalized, deduplicated set of technologies."""

    technologies: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized = tuple(sorted(set(t.lower().strip() for t in self.technologies if t.strip())))
        # object.__setattr__ is required because frozen=True prevents direct assignment
        object.__setattr__(self, "technologies", normalized)

    @classmethod
    def from_list(cls, techs: list[str]) -> "Stack":
        return cls(technologies=tuple(techs))

    def contains(self, tech: str) -> bool:
        return tech.lower().strip() in self.technologies

    def __len__(self) -> int:
        return len(self.technologies)
