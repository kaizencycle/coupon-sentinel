"""Tests for deal intelligence API endpoints."""

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


class TestDealAPI:
    def test_root_returns_api_index(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Coupon Sentinel API"
        assert data["health"] == "/health"
        assert data["docs"] == "/docs"

    def test_list_deals(self):
        response = client.get("/api/deals")
        assert response.status_code == 200
        data = response.json()
        assert data["is_mock_data"] is True
        assert data["count"] > 0
        assert "deals" in data
        deal = data["deals"][0]
        assert "effective_price" in deal
        assert "confidence_label" in deal
        assert "evidence_summary" in deal

    def test_get_deal_by_id(self):
        response = client.get("/api/deals/deal-tide-stack")
        assert response.status_code == 200
        deal = response.json()["deal"]
        assert deal["id"] == "deal-tide-stack"
        assert deal["product_name"] == "Tide Pods Laundry Detergent"
        assert deal["receipt_verified"] is True

    def test_get_deal_not_found(self):
        response = client.get("/api/deals/nonexistent")
        assert response.status_code == 404

    def test_list_price_observations(self):
        response = client.get("/api/price-observations")
        assert response.status_code == 200
        data = response.json()
        assert data["is_mock_data"] is True
        assert data["count"] > 0

    def test_filter_deals_by_retailer(self):
        response = client.get("/api/deals?retailer=Target")
        assert response.status_code == 200
        for deal in response.json()["deals"]:
            assert deal["retailer"] == "Target"

    def test_optimize_still_works(self):
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
        assert response.json()["grand_total"] > 0
