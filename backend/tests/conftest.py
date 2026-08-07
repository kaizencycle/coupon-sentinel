"""Pytest configuration for Coupon Sentinel backend."""

import sys
from pathlib import Path

# Repository root (parent of backend/) — required for `backend.*` imports when
# running `cd backend && pytest` as documented in README.
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
