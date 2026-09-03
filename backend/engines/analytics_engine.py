"""
Coupon Sentinel - Analytics Engine (Milestone 5)

track_event() always persists to the local analytics_events table — that
part is real and queryable with no external dependency (see
GET /api/analytics/savings, backend/analytics_routes.py). It additionally
best-effort forwards to Mixpanel's HTTP API when MIXPANEL_TOKEN is set.

Unlike Stripe/Kroger/email, forwarding failure never raises: analytics is
observability, not a user-facing feature, so a Mixpanel outage or a missing
token must never break the request that triggered the event. Unverified
against a real Mixpanel project — no token exists for this project yet.
"""

import logging
import os
import threading
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from backend.db_models import AnalyticsEvent

logger = logging.getLogger(__name__)

MIXPANEL_TOKEN = os.environ.get("MIXPANEL_TOKEN")
_MIXPANEL_TRACK_URL = "https://api.mixpanel.com/track"


def track_event(
    event_type: str,
    db: Session,
    user_id: Optional[int] = None,
    event_data: Optional[dict] = None,
) -> AnalyticsEvent:
    """Persist an analytics event and best-effort forward it to Mixpanel."""
    record = AnalyticsEvent(user_id=user_id, event_type=event_type, event_data=event_data or {})
    db.add(record)
    db.commit()
    db.refresh(record)

    if MIXPANEL_TOKEN:
        # track_event() is called synchronously from inside async route
        # handlers (register/login/optimize) as well as plain sync engine
        # functions (subscription_engine.py). A blocking httpx.post() here
        # would stall the single asyncio event loop — for up to the 5s
        # timeout below — for every other in-flight request, not just this
        # one. Fire-and-forget on a daemon thread keeps this genuinely
        # non-blocking regardless of caller context.
        threading.Thread(
            target=_forward_to_mixpanel,
            args=(event_type, user_id, event_data or {}),
            daemon=True,
        ).start()

    return record


def _forward_to_mixpanel(event_type: str, user_id: Optional[int], event_data: dict) -> None:
    payload = {
        "event": event_type,
        "properties": {
            "token": MIXPANEL_TOKEN,
            "distinct_id": str(user_id) if user_id is not None else "anonymous",
            **event_data,
        },
    }
    try:
        response = httpx.post(_MIXPANEL_TRACK_URL, json=[payload], timeout=5.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Mixpanel event forwarding failed for %s: %s", event_type, exc)
