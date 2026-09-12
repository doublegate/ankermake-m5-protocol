import sys
from pathlib import Path


# Ensure plain `pytest` can import the repo's top-level modules on Windows
# without requiring a manual PYTHONPATH override.
REPO_ROOT = Path(__file__).resolve().parent.parent
repo_root_str = str(REPO_ROOT)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)
