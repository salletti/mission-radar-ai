import sys
from pathlib import Path

# Adds backend/ to sys.path so backend modules are importable as `src.*`
# (mirrors the backend's own import convention: `from src.Application...`).
#
# Two layouts are supported:
# - local: repo_root/evaluation next to repo_root/backend
# - docker: evaluation/ mounted inside the backend container at /app/evaluation,
#   where backend's own content (src/, ...) already sits at /app
_EVAL_ROOT = Path(__file__).resolve().parent
_BACKEND_CANDIDATES = (
    _EVAL_ROOT.parent / "backend",
    _EVAL_ROOT.parent,
)
for _candidate in _BACKEND_CANDIDATES:
    if (_candidate / "src").is_dir():
        sys.path.insert(0, str(_candidate))
        break
