#!/bin/bash
# Start script for Render deployment
# Sets PYTHONPATH to ensure backend module can be imported

export PYTHONPATH=.
exec uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}
