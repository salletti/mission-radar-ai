import sys
from pathlib import Path

# Ensure evaluation/ root is on sys.path so `from models.gold_sample import ...` works
sys.path.insert(0, str(Path(__file__).parent.parent))
