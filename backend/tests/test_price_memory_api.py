"""API tests for local price memory endpoints (PR-2)."""

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


class TestPriceMemoryAPI:
    def test_get_price_memory_baseline(self):
        response = client.get(
            "/api/price-memory/prod-tide-pods",
            params={"zip_code": "11429", "retailer": "Target"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_mock_data"] is True
        baseline = data["baseline"]
        assert baseline["product_id"] == "prod-tide-pods"
        assert baseline["sample_size"] >= 5
        assert baseline["median_price"] > 0

    def test_get_price_memory_not_found(self):
        response = client.get(
            "/api/price-memory/prod-missing",
            params={"zip_code": "00000", "retailer": "Target"},
        )
        assert response.status_code == 404

    def test_list_anomalies(self):
        response = client.get("/api/anomalies")
        assert response.status_code == 200
        data = response.json()
        assert data["is_mock_data"] is True
        assert data["count"] > 0
        assert "anomalies" in data

    def test_filter_anomalies_by_signal(self):
        response = client.get("/api/anomalies", params={"signal": "INSUFFICIENT_DATA"})
        assert response.status_code == 200
        for anomaly in response.json()["anomalies"]:
            assert anomaly["signal"] == "INSUFFICIENT_DATA"

    def test_milk_normal_signal_fixture(self):
        response = client.get(
            "/api/anomalies",
            params={
                "zip_code": "11566",
                "retailer": "Walmart",
                "signal": "NORMAL",
            },
        )
        assert response.status_code == 200
        milk = [
            a
            for a in response.json()["anomalies"]
            if a["product_id"] == "prod-gv-milk"
        ]
        assert len(milk) >= 1
        assert milk[0]["signal"] == "NORMAL"

    def test_pr1_optimize_still_works(self):
        response = client.post(
            "/api/optimize",
            json={
                "shopping_list": [
                    {"name": "milk", "quantity": 1, "unit": "gallon", "flexible": True}
                ],
                "zip_code": "11566",
                "preferred_stores": ["Target"],
                "allow_multi_store": False,
                "rebate_apps": [],
            },
        )
        assert response.status_code == 200

    def test_pr1_deals_still_works(self):
        response = client.get("/api/deals")
        assert response.status_code == 200
        assert response.json()["count"] > 0
