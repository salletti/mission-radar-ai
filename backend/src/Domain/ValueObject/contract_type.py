from enum import Enum


class ContractType(str, Enum):
    FREELANCE      = "freelance"
    PERMANENT      = "permanent"      # CDI en France
    FIXED_TERM     = "fixed_term"     # CDD en France
    INTERNSHIP     = "internship"
    APPRENTICESHIP = "apprenticeship"
    UNKNOWN        = "unknown"
