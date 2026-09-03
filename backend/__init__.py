# Coupon Sentinel Backend Package

# Load .env before any submodule reads os.environ at import time (database.py,
# auth.py, subscription_engine.py, kroger.py all do). __init__.py always runs
# before `backend.<submodule>` imports, so this is the one place that's
# guaranteed to run first regardless of entry point (app.py, alembic env.py,
# pytest, run.py). No-ops if .env doesn't exist — real deployments (Render,
# docker-compose) set env vars directly, this is for local dev convenience.
from dotenv import load_dotenv

load_dotenv()
