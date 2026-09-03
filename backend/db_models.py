"""
Coupon Sentinel - Persistent ORM Models (Phase 1, Milestone 1)

SQLAlchemy models backing authentication, billing, and the evidence layer's
durable storage. Distinct from the read-only mock-data Pydantic models in
models.py and deal_models.py — those remain the unauthenticated demo/optimizer
path; these tables are the real persistence layer real users' data lives in.

Naming note: PriceObservationRecord / DealEventRecord are deliberately suffixed
with "Record" to avoid colliding with the in-memory evidence-layer Pydantic
classes PriceObservation / DealEvent in deal_models.py.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    shopping_lists: Mapped[list["ShoppingListRecord"]] = relationship(back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(50), nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="incomplete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    renewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscriptions")


class PriceObservationRecord(Base):
    """Durable evidence-layer observation (see deal_models.PriceObservation for the API shape)."""

    __tablename__ = "price_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    package_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)


class DealEventRecord(Base):
    """Durable interpreted-layer deal event, linked back to its evidence observations."""

    __tablename__ = "deal_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    deal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    savings_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ShoppingListRecord(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    items: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship(back_populates="shopping_lists")


class OptimizedPlanRecord(Base):
    __tablename__ = "optimized_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    shopping_list_id: Mapped[int] = mapped_column(ForeignKey("shopping_lists.id"), nullable=False)
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    total_savings: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_data: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
