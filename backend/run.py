#!/usr/bin/env python3
"""
Entry point for Render deployment.
Ensures Python path is set correctly before starting the app.
"""
import sys
import os
from pathlib import Path

# Get the directory containing this script (backend/)
backend_dir = Path(__file__).parent.absolute()
# Get the repo root (parent of backend/)
repo_root = backend_dir.parent.absolute()

# Add repo root to Python path if not already there
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Verify backend module can be imported
try:
    import backend.app
except ImportError as e:
    print(f"Error importing backend.app: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Backend directory exists: {backend_dir.exists()}")
    print(f"Repo root exists: {repo_root.exists()}")
    sys.exit(1)

# Now import and run uvicorn
if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
