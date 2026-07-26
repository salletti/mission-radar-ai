from enum import Enum


class RemoteMode(str, Enum):
    FULL_REMOTE = "full_remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"
