from uuid import UUID


class RepositoryError(Exception):
    """Base class for all Infrastructure persistence exceptions."""


class DatabaseError(RepositoryError):
    """Wraps unexpected SQLAlchemy errors so they never leak to the Domain or Application layer."""


class EntityNotFoundError(RepositoryError):
    """Raised when a mandatory entity lookup returns no result."""

    def __init__(self, entity_type: str, entity_id: UUID | str) -> None:
        super().__init__(f"{entity_type} not found: {entity_id}")
        self.entity_type = entity_type
        self.entity_id = entity_id
