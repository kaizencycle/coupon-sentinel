"""Tests for GET /api/analytics/savings and the analytics/persistence side
effects of POST /api/optimize (Milestone 5)."""

from backend.db_models import AnalyticsEvent, OptimizedPlanRecord, ShoppingListRecord


def _register(client, email="analytics@example.com"):
    return client.post("/api/auth/register", json={"email": email, "password": "password123"}).json()


def _optimize_payload():
    return {
        "shopping_list": [{"name": "milk", "quantity": 1, "unit": "gallon", "flexible": True}],
        "zip_code": "11566",
        "preferred_stores": ["Target"],
        "allow_multi_store": False,
        "rebate_apps": [],
    }


class TestSavingsSummary:
    def test_requires_auth(self, db_client):
        client, _ = db_client
        response = client.get("/api/analytics/savings")
        assert response.status_code == 401

    def test_zero_before_any_optimization(self, db_client):
        client, _ = db_client
        tokens = _register(client, "nosaves@example.com")
        response = client.get(
            "/api/analytics/savings", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 200
        assert response.json() == {
            "optimization_count": 0,
            "total_savings": 0.0,
            "average_savings_per_optimization": 0.0,
        }

    def test_aggregates_after_authenticated_optimizations(self, db_client):
        client, session_factory = db_client
        tokens = _register(client, "saver@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        for _ in range(2):
            response = client.post("/api/optimize", json=_optimize_payload(), headers=headers)
            assert response.status_code == 200

        summary = client.get("/api/analytics/savings", headers=headers).json()
        assert summary["optimization_count"] == 2
        assert summary["total_savings"] > 0
        assert summary["average_savings_per_optimization"] == round(summary["total_savings"] / 2, 2)

        db = session_factory()
        assert db.query(OptimizedPlanRecord).count() == 2
        assert db.query(ShoppingListRecord).count() == 2
        db.close()


class TestOptimizeAnalyticsSideEffects:
    def test_anonymous_call_still_works_and_tracks_event(self, db_client):
        client, session_factory = db_client
        response = client.post("/api/optimize", json=_optimize_payload())
        assert response.status_code == 200

        db = session_factory()
        events = db.query(AnalyticsEvent).filter_by(event_type="optimize").all()
        assert len(events) == 1
        assert events[0].user_id is None
        assert events[0].event_data["item_count"] == 1
        # Anonymous calls must not persist a plan/list — nothing to attribute it to.
        assert db.query(OptimizedPlanRecord).count() == 0
        db.close()

    def test_authenticated_call_persists_and_tracks_with_user_id(self, db_client):
        client, session_factory = db_client
        tokens = _register(client, "tracked@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        response = client.post("/api/optimize", json=_optimize_payload(), headers=headers)
        assert response.status_code == 200

        db = session_factory()
        events = db.query(AnalyticsEvent).filter_by(event_type="optimize").all()
        assert len(events) == 1
        assert events[0].user_id is not None
        assert db.query(OptimizedPlanRecord).count() == 1
        db.close()


class TestAuthAndSubscriptionEventsTracked:
    def test_register_tracks_signup_event(self, db_client):
        client, session_factory = db_client
        _register(client, "eventreg@example.com")
        db = session_factory()
        assert db.query(AnalyticsEvent).filter_by(event_type="signup").count() == 1
        db.close()

    def test_login_tracks_login_event(self, db_client):
        client, session_factory = db_client
        _register(client, "eventlogin@example.com")
        client.post("/api/auth/login", json={"email": "eventlogin@example.com", "password": "password123"})
        db = session_factory()
        assert db.query(AnalyticsEvent).filter_by(event_type="login").count() == 1
        db.close()
