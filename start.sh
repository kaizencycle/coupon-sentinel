#!/bin/bash
# Start script for Render deployment
# Sets PYTHONPATH to ensure backend module can be imported

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory (repo root)
cd "$SCRIPT_DIR" || exit 1

# Set PYTHONPATH to include current directory
export PYTHONPATH="${PYTHONPATH}:${SCRIPT_DIR}:."

# Verify backend directory exists
if [ ! -d "backend" ]; then
    echo "Error: backend directory not found in $SCRIPT_DIR"
    echo "Current directory contents:"
    ls -la
    exit 1
fi

# Try using WSGI entry point first (standard)
if [ -f "wsgi.py" ]; then
    exec python3 -m uvicorn wsgi:app --host 0.0.0.0 --port ${PORT:-8000}
elif [ -f "backend/run.py" ]; then
    exec python3 backend/run.py
else
    # Fallback to direct uvicorn
    exec python3 -m uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}
fi
