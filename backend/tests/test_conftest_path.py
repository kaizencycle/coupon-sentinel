"""Verify pytest works from backend directory per README."""

import subprocess
import sys
from pathlib import Path


def test_pytest_collects_from_backend_directory():
    backend_dir = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "error" not in result.stdout.lower() or "tests collected" in result.stdout.lower()
