"""
Coupon Sentinel - User / Subscription Routes

Profile, subscription management, and the Stripe webhook receiver. Split out
from app.py (which stays focused on the unauthenticated mock-data optimizer)
to keep the real-user, real-money code path in one reviewable place.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import UserProfile, get_current_user
from backend.database import get_db
from backend.db_models import User
from backend.engines.subscription_engine import (
    PLAN_CATALOG,
    cancel_subscription,
    create_subscription,
    handle_webhook_event,
)

router = APIRouter(tags=["user"])


class CreateSubscriptionRequest(BaseModel):
    tier: str


@router.get("/api/user/profile", response_model=UserProfile)
async def get_profile(user: User = Depends(get_current_user)):
    return user


@router.get("/api/subscriptions/plans")
async def list_plans():
    return {"plans": list(PLAN_CATALOG.values())}


@router.post("/api/user/subscription", status_code=status.HTTP_201_CREATED)
async def create_user_subscription(
    request: CreateSubscriptionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.tier not in PLAN_CATALOG or request.tier == "free":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tier must be 'pro' or 'premium'")

    return create_subscription(user, request.tier, db)


@router.delete("/api/user/subscription")
async def delete_user_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = cancel_subscription(user, db)
    return {"status": record.status, "tier": user.tier}


@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    return handle_webhook_event(payload, sig_header, db)
