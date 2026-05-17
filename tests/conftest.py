"""Pytest configuration for tests directory."""

import sys
from pathlib import Path

# Add project root and src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_dir) not in sys.path:
    sys.path.insert(1, str(src_dir))
