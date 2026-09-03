"""Tests for /api/deal-events (Milestone 3) — infer + list against real DB rows."""

from datetime import datetime, timedelta, timezone

from backend.db_models import PriceObservationRecord


def _seed_observation(db, product_id, store_id, price, days_ago=0, source="kroger_api"):
    obs = PriceObservationRecord(
        product_id=product_id,
        store_id=store_id,
        price=price,
        source=source,
        confidence=0.95,
        timestamp=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


class TestInferDealEvents:
    def test_infer_persists_price_drop_deal(self, db_client):
        client, session_factory = db_client
        db = session_factory()
        _seed_observation(db, "paper-towels-12ct", "kroger-01400943", 4.00, days_ago=10)
        _seed_observation(db, "paper-towels-12ct", "kroger-01400943", 4.00, days_ago=5)
        _seed_observation(db, "paper-towels-12ct", "kroger-01400943", 3.00, days_ago=0)
        db.close()

        response = client.post("/api/deal-events/infer")
        assert response.status_code == 200
        data = response.json()
        assert data["observations_considered"] == 3
        assert data["count"] == 1
        assert data["deals"][0]["deal_type"] == "price_drop"
        assert data["deals"][0]["effective_price"] == 3.00
        assert data["deals"][0]["savings_amount"] == 1.00

    def test_infer_with_no_observations_returns_empty(self, db_client):
        client, _ = db_client
        response = client.post("/api/deal-events/infer")
        assert response.status_code == 200
        assert response.json() == {"deals": [], "count": 0, "observations_considered": 0}

    def test_infer_scoped_to_product_id(self, db_client):
        client, session_factory = db_client
        db = session_factory()
        _seed_observation(db, "paper-towels-12ct", "s1", 4.00, days_ago=10)
        _seed_observation(db, "paper-towels-12ct", "s1", 4.00, days_ago=5)
        _seed_observation(db, "paper-towels-12ct", "s1", 3.00, days_ago=0)
        _seed_observation(db, "eggs-dozen", "s1", 4.00, days_ago=5)
        _seed_observation(db, "eggs-dozen", "s1", 3.00, days_ago=0)
        db.close()

        response = client.post("/api/deal-events/infer", params={"product_id": "paper-towels-12ct"})
        data = response.json()
        assert data["observations_considered"] == 3
        assert data["count"] == 1
        assert data["deals"][0]["product_id"] == "paper-towels-12ct"


class TestListDealEvents:
    def test_list_returns_persisted_deals(self, db_client):
        client, session_factory = db_client
        db = session_factory()
        _seed_observation(db, "paper-towels-12ct", "s1", 4.00, days_ago=10)
        _seed_observation(db, "paper-towels-12ct", "s1", 4.00, days_ago=5)
        _seed_observation(db, "paper-towels-12ct", "s1", 3.00, days_ago=0)
        db.close()

        infer_response = client.post("/api/deal-events/infer")
        assert infer_response.json()["count"] == 1

        list_response = client.get("/api/deal-events")
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["count"] == 1
        assert data["deals"][0]["product_id"] == "paper-towels-12ct"

    def test_list_empty_before_any_inference(self, db_client):
        client, _ = db_client
        response = client.get("/api/deal-events")
        assert response.status_code == 200
        assert response.json() == {"deals": [], "count": 0}

    def test_list_filters_by_deal_type(self, db_client):
        client, session_factory = db_client
        db = session_factory()
        _seed_observation(db, "paper-towels-12ct", "s1", 4.00, days_ago=10)
        _seed_observation(db, "paper-towels-12ct", "s1", 4.00, days_ago=5)
        _seed_observation(db, "paper-towels-12ct", "s1", 3.00, days_ago=0)
        db.close()
        client.post("/api/deal-events/infer")

        response = client.get("/api/deal-events", params={"deal_type": "coupon"})
        assert response.json()["count"] == 0

        response = client.get("/api/deal-events", params={"deal_type": "price_drop"})
        assert response.json()["count"] == 1
