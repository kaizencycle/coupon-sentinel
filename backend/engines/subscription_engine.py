"""
Coupon Sentinel - Subscription / Billing Engine

Thin wrapper around the Stripe API for customer + subscription lifecycle and
webhook handling. All Stripe calls are guarded behind _require_stripe() so
importing this module (and running the app/tests) never requires real Stripe
keys — only actually creating/canceling a subscription does.

STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET / STRIPE_PRICE_ID_PRO /
STRIPE_PRICE_ID_PREMIUM are production secrets Michael provides; they are
never committed to the repo (see .env.example).
"""

import os
from typing import Optional

import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.db_models import Subscription, User

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

_TIER_PRICE_ENV_VAR = {
    "pro": "STRIPE_PRICE_ID_PRO",
    "premium": "STRIPE_PRICE_ID_PREMIUM",
}

# Local subscription states that mean "this user already has a subscription in
# flight or active" — a second create_subscription() call must not start a
# second Stripe subscription while one of these exists.
_OPEN_SUBSCRIPTION_STATUSES = {"active", "incomplete", "trialing", "past_due"}

# Tier feature matrix — mirrors the Phase 1 handoff spec. Static/no DB lookup
# needed since these are product decisions, not per-user data.
PLAN_CATALOG = {
    "free": {
        "tier": "free",
        "name": "Free",
        "monthly_price_usd": 0,
        "shopping_lists": 1,
        "store_comparison": "1 store",
        "coupons": "None",
        "price_history_days": 0,
        "deal_alerts": "No",
        "multi_store_optimize": False,
        "savings_tracking": False,
        "export_plans": False,
        "api_access": False,
    },
    "pro": {
        "tier": "pro",
        "name": "Pro",
        "monthly_price_usd": 2.99,
        "shopping_lists": 5,
        "store_comparison": "All stores",
        "coupons": "Basic",
        "price_history_days": 7,
        "deal_alerts": "Daily",
        "multi_store_optimize": True,
        "savings_tracking": True,
        "export_plans": False,
        "api_access": False,
    },
    "premium": {
        "tier": "premium",
        "name": "Premium",
        "monthly_price_usd": 7.99,
        "shopping_lists": "Unlimited",
        "store_comparison": "All stores",
        "coupons": "Advanced",
        "price_history_days": 30,
        "deal_alerts": "Real-time",
        "multi_store_optimize": True,
        "savings_tracking": True,
        "export_plans": True,
        "api_access": True,
    },
}


def _require_stripe() -> None:
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured (STRIPE_SECRET_KEY missing). Set it in the environment.",
        )
    stripe.api_key = STRIPE_SECRET_KEY


def get_or_create_stripe_customer(user: User, db: Session) -> str:
    """Return the user's Stripe customer id, creating one in Stripe if needed."""
    _require_stripe()
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
    user.stripe_customer_id = customer.id
    db.commit()
    return customer.id


def create_subscription(user: User, tier: str, db: Session) -> dict:
    """Create a Stripe subscription in default_incomplete state and record it locally."""
    _require_stripe()

    price_env_var = _TIER_PRICE_ENV_VAR.get(tier)
    if price_env_var is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown tier: {tier}")

    price_id = os.environ.get(price_env_var)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{price_env_var} is not configured",
        )

    existing = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status.in_(_OPEN_SUBSCRIPTION_STATUSES))
        .order_by(Subscription.id.desc())
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"User already has a {existing.status} subscription "
                f"(id={existing.stripe_subscription_id}, tier={existing.tier}). "
                "Cancel it before creating a new one."
            ),
        )

    customer_id = get_or_create_stripe_customer(user, db)

    # Idempotency key scoped to (user, tier, how many subscriptions this user
    # has had before): a retried request for the *same* attempt (timeout,
    # double-click) reuses the key and Stripe returns the same subscription
    # instead of creating a second one; a genuinely new attempt after a prior
    # subscription was resolved (canceled, etc.) gets a fresh key.
    attempt_count = db.query(Subscription).filter(Subscription.user_id == user.id).count()
    idempotency_key = f"create-sub-user{user.id}-{tier}-attempt{attempt_count}"

    stripe_subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        payment_behavior="default_incomplete",
        expand=["latest_invoice.payment_intent"],
        idempotency_key=idempotency_key,
    )

    record = Subscription(
        user_id=user.id,
        tier=tier,
        stripe_subscription_id=stripe_subscription.id,
        status=stripe_subscription.status,
    )
    db.add(record)
    db.commit()

    payment_intent = stripe_subscription.latest_invoice.payment_intent
    return {
        "subscription_id": stripe_subscription.id,
        "status": stripe_subscription.status,
        "client_secret": payment_intent.client_secret if payment_intent else None,
    }


def cancel_subscription(user: User, db: Session) -> Subscription:
    """Cancel the user's active Stripe subscription and downgrade to free."""
    _require_stripe()

    record = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.id.desc())
        .first()
    )
    if record is None or not record.stripe_subscription_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found")

    stripe.Subscription.delete(record.stripe_subscription_id)
    record.status = "canceled"
    user.tier = "free"
    db.commit()
    return record


def _sync_subscription_status(stripe_subscription: dict, db: Session, force_status: Optional[str] = None) -> None:
    stripe_subscription_id = stripe_subscription.get("id")
    if not stripe_subscription_id:
        return

    record = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_subscription_id).first()
    if record is None:
        return

    record.status = force_status or stripe_subscription.get("status", record.status)

    user = db.get(User, record.user_id)
    if user is not None:
        user.tier = record.tier if record.status == "active" else "free"

    db.commit()


def handle_webhook_event(payload: bytes, sig_header: str, db: Session) -> dict:
    """Verify and process a Stripe webhook event, updating local subscription state."""
    _require_stripe()

    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STRIPE_WEBHOOK_SECRET is not configured",
        )

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload or signature")

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        _sync_subscription_status(data_object, db)
    elif event_type == "customer.subscription.deleted":
        _sync_subscription_status(data_object, db, force_status="canceled")
    elif event_type == "invoice.payment_failed":
        stripe_subscription_id = data_object.get("subscription")
        if stripe_subscription_id:
            record = (
                db.query(Subscription)
                .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
                .first()
            )
            if record is not None:
                record.status = "past_due"
                db.commit()

    return {"status": "received", "type": event_type}
