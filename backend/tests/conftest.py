"""Pytest configuration for Coupon Sentinel backend."""

import sys
from pathlib import Path

# Repository root (parent of backend/) — required for `backend.*` imports when
# running `cd backend && pytest` as documented in README.
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import backend.db_models  # noqa: E402,F401 — register models on Base.metadata
from backend.app import app  # noqa: E402
from backend.database import Base, get_db  # noqa: E402


@pytest.fixture
def db_client():
    """
    TestClient backed by a fresh in-memory SQLite DB, isolated per test.

    A single, function-scoped fixture (rather than each test module wiring
    its own module-level `app.dependency_overrides[get_db]`) avoids two test
    modules silently clobbering each other's override — the last-imported
    module would otherwise "win" globally while an earlier module's fixture
    keeps creating tables on a DB no request ever reaches.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app), session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
