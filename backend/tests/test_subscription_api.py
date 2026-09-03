"""Tests for subscription/billing endpoints and the Stripe wrapper engine."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.db_models import Subscription, User
from backend.engines import subscription_engine


def _auth_headers(client, email="billing@example.com"):
    tokens = client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class TestPlansEndpoint:
    def test_list_plans_returns_tier_matrix(self, db_client):
        client, _ = db_client
        response = client.get("/api/subscriptions/plans")
        assert response.status_code == 200
        tiers = {plan["tier"] for plan in response.json()["plans"]}
        assert tiers == {"free", "pro", "premium"}


class TestSubscriptionStatusEndpoint:
    def test_no_subscription_returns_nulls(self, db_client):
        client, _ = db_client
        response = client.get("/api/user/subscription", headers=_auth_headers(client, "nosub@example.com"))
        assert response.status_code == 200
        assert response.json() == {"status": None, "tier": None}

    def test_requires_auth(self, db_client):
        client, _ = db_client
        response = client.get("/api/user/subscription")
        assert response.status_code == 401

    def test_surfaces_incomplete_subscription_even_though_tier_is_free(self, db_client):
        """This is the whole point of the endpoint: a stuck 'incomplete'
        subscription doesn't touch user.tier, so the frontend needs a way to
        see it independent of tier to show a cancel button."""
        client, session_factory = db_client
        headers = _auth_headers(client, "stuck@example.com")
        db = session_factory()
        user = db.query(User).filter_by(email="stuck@example.com").first()
        assert user.tier == "free"
        db.add(Subscription(user_id=user.id, tier="pro", stripe_subscription_id="sub_x", status="incomplete"))
        db.commit()
        db.close()

        response = client.get("/api/user/subscription", headers=headers)
        assert response.json() == {"status": "incomplete", "tier": "pro"}


class TestSubscriptionEndpointsWithoutStripeConfigured:
    """Without STRIPE_SECRET_KEY set, billing endpoints fail loudly (503), not silently."""

    def test_create_subscription_requires_auth(self, db_client):
        client, _ = db_client
        response = client.post("/api/user/subscription", json={"tier": "pro"})
        assert response.status_code == 401

    def test_create_subscription_rejects_free_tier(self, db_client):
        client, _ = db_client
        response = client.post(
            "/api/user/subscription", json={"tier": "free"}, headers=_auth_headers(client)
        )
        assert response.status_code == 400

    def test_create_subscription_without_stripe_key_returns_503(self, db_client):
        client, _ = db_client
        response = client.post(
            "/api/user/subscription",
            json={"tier": "pro"},
            headers=_auth_headers(client, "nostripe@example.com"),
        )
        assert response.status_code == 503

    def test_cancel_without_active_subscription_requires_stripe(self, db_client):
        client, _ = db_client
        response = client.delete(
            "/api/user/subscription", headers=_auth_headers(client, "cancel@example.com")
        )
        assert response.status_code == 503

    def test_webhook_without_config_returns_503(self, db_client):
        client, _ = db_client
        response = client.post(
            "/api/webhooks/stripe", content=b"{}", headers={"stripe-signature": "x"}
        )
        assert response.status_code == 503


class TestSubscriptionEngineWithMockedStripe:
    """Exercise the actual billing logic with stripe.* calls mocked out."""

    def test_create_subscription_persists_local_record(self, db_client, monkeypatch):
        _, session_factory = db_client
        db = session_factory()
        user = User(email="mocked@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        monkeypatch.setattr(subscription_engine, "STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setenv("STRIPE_PRICE_ID_PRO", "price_test_pro")

        fake_customer = MagicMock(id="cus_123")
        fake_payment_intent = MagicMock(client_secret="secret_abc")
        fake_invoice = MagicMock(payment_intent=fake_payment_intent)
        fake_subscription = MagicMock(id="sub_123", status="incomplete", latest_invoice=fake_invoice)

        monkeypatch.setattr(subscription_engine.stripe.Customer, "create", lambda **kw: fake_customer)
        captured_kwargs = {}

        def _fake_subscription_create(**kw):
            captured_kwargs.update(kw)
            return fake_subscription

        monkeypatch.setattr(subscription_engine.stripe.Subscription, "create", _fake_subscription_create)

        result = subscription_engine.create_subscription(user, "pro", db)

        assert result["subscription_id"] == "sub_123"
        assert result["client_secret"] == "secret_abc"
        assert user.stripe_customer_id == "cus_123"
        assert captured_kwargs["idempotency_key"]  # sent so retries can't double-create in Stripe

        record = db.query(Subscription).filter_by(user_id=user.id).first()
        assert record is not None
        assert record.tier == "pro"
        assert record.status == "incomplete"
        db.close()

    def test_create_subscription_rejects_when_already_subscribed(self, db_client, monkeypatch):
        _, session_factory = db_client
        db = session_factory()
        user = User(email="dupe@example.com", password_hash="x", stripe_customer_id="cus_existing")
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(Subscription(user_id=user.id, tier="pro", stripe_subscription_id="sub_existing", status="active"))
        db.commit()

        monkeypatch.setattr(subscription_engine, "STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setenv("STRIPE_PRICE_ID_PRO", "price_test_pro")

        create_calls = []
        monkeypatch.setattr(
            subscription_engine.stripe.Subscription,
            "create",
            lambda **kw: create_calls.append(kw),
        )

        with pytest.raises(HTTPException) as exc_info:
            subscription_engine.create_subscription(user, "pro", db)

        assert exc_info.value.status_code == 409
        assert create_calls == []  # never called Stripe once a duplicate was detected
        db.close()

    @pytest.mark.parametrize("blocking_status", ["active", "incomplete", "trialing", "past_due"])
    def test_cancel_finds_subscription_in_any_open_status(self, db_client, monkeypatch, blocking_status):
        """A user stuck in e.g. 'incomplete' must be able to cancel their way out —
        cancel_subscription's query has to match create_subscription's blocking set."""
        _, session_factory = db_client
        db = session_factory()
        user = User(email=f"cancel-{blocking_status}@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(
            Subscription(
                user_id=user.id, tier="pro", stripe_subscription_id="sub_stuck", status=blocking_status
            )
        )
        db.commit()

        monkeypatch.setattr(subscription_engine, "STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setattr(subscription_engine.stripe.Subscription, "delete", lambda sub_id: None)

        record = subscription_engine.cancel_subscription(user, db)

        assert record.status == "canceled"
        assert user.tier == "free"
        db.close()

    def test_webhook_subscription_deleted_downgrades_user_to_free(self, db_client, monkeypatch):
        _, session_factory = db_client
        db = session_factory()
        user = User(email="downgrade@example.com", password_hash="x", tier="pro")
        db.add(user)
        db.commit()
        db.refresh(user)

        sub_record = Subscription(
            user_id=user.id, tier="pro", stripe_subscription_id="sub_999", status="active"
        )
        db.add(sub_record)
        db.commit()

        monkeypatch.setattr(subscription_engine, "STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setattr(subscription_engine, "STRIPE_WEBHOOK_SECRET", "whsec_fake")

        fake_event = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_999", "status": "canceled"}},
        }
        monkeypatch.setattr(
            subscription_engine.stripe.Webhook, "construct_event", lambda *a, **kw: fake_event
        )

        result = subscription_engine.handle_webhook_event(b"{}", "sig", db)

        assert result["type"] == "customer.subscription.deleted"
        db.refresh(user)
        db.refresh(sub_record)
        assert sub_record.status == "canceled"
        assert user.tier == "free"
        db.close()
