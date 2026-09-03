"""
Coupon Sentinel - Database Setup

SQLAlchemy engine/session wiring for the persistent layer (users, subscriptions,
price observations, deal events, shopping lists, optimized plans, analytics).

This is separate from the existing mock-data optimizer (models.py, providers/,
engines/pricing_engine.py) which remains untouched and unauthenticated.

DATABASE_URL defaults to a local SQLite file so the app and tests run without
a running Postgres instance. Set DATABASE_URL to a postgresql:// URL in
production (Render Postgres, etc.).
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./coupon_sentinel.db")

# Render/Heroku-style URLs sometimes use the legacy "postgres://" scheme, which
# SQLAlchemy 2.x no longer accepts directly.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency yielding a request-scoped DB session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Convenience for local dev/tests; production uses Alembic."""
    import backend.db_models  # noqa: F401 — register models on Base.metadata

    Base.metadata.create_all(bind=engine)
