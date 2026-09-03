"""
Coupon Sentinel - Email Sending (Milestone 4)

Thin wrapper around Resend's REST API for transactional email (verification
links, etc.), called via httpx directly rather than pulling in an SDK for a
single POST-with-JSON call. Falls back to SendGrid if RESEND_API_KEY is
unset but SENDGRID_API_KEY is.

Same guarded pattern as Stripe/Kroger: importing this module never requires
credentials — only actually calling send_email() does, and it fails with a
clear 503 rather than silently dropping the email.
"""

import os

import httpx
from fastapi import HTTPException, status

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")


def email_provider_configured() -> bool:
    return bool(RESEND_API_KEY or SENDGRID_API_KEY)


def send_email(to: str, subject: str, html: str) -> dict:
    if RESEND_API_KEY:
        return _send_via_resend(to, subject, html)
    if SENDGRID_API_KEY:
        return _send_via_sendgrid(to, subject, html)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No email provider configured (RESEND_API_KEY / SENDGRID_API_KEY missing)",
    )


def _send_via_resend(to: str, subject: str, html: str) -> dict:
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from": EMAIL_FROM, "to": [to], "subject": subject, "html": html},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def _send_via_sendgrid(to: str, subject: str, html: str) -> dict:
    response = httpx.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {SENDGRID_API_KEY}"},
        json={
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": EMAIL_FROM},
            "subject": subject,
            "content": [{"type": "text/html", "value": html}],
        },
        timeout=10.0,
    )
    response.raise_for_status()
    return {"status": "sent"}
