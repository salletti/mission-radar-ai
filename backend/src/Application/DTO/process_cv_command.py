from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessCVCommand:
    email: str
    file_path: str
