"""Tests for PR-3 product identity bridge and deal-aware optimize endpoint."""

import json

from fastapi.testclient import TestClient

from backend.app import app
from backend.engines import optimize_shopping_list
from backend.models import OptimizeRequest, ShoppingItem
from backend.providers import get_mock_coupons, get_mock_store_items

client = TestClient(app)

_WALMART_REQUEST = {
    "shopping_list": [
        {"name": "whole milk", "quantity": 1, "unit": "gallon", "flexible": True},
        {"name": "eggs", "quantity": 12, "unit": "count", "flexible": True},
        {"name": "whole wheat bread", "quantity": 1, "unit": "count", "flexible": True},
        {"name": "chicken", "quantity": 1, "unit": "lb", "flexible": True},
    ],
    "zip_code": "11566",
    "preferred_stores": ["Walmart"],
    "allow_multi_store": False,
    "rebate_apps": [],
}


class TestOptimizeRegression:
    def test_optimize_endpoint_matches_engine_output(self):
        request = OptimizeRequest(
            shopping_list=[
                ShoppingItem(name="milk", quantity=1, unit="gallon", flexible=True),
                ShoppingItem(name="eggs", quantity=12, unit="count", flexible=True),
            ],
            zip_code="11566",
            preferred_stores=["Walmart"],
            allow_multi_store=False,
            rebate_apps=[],
        )
        direct = optimize_shopping_list(
            request,
            get_mock_store_items(),
            get_mock_coupons(),
        ).model_dump(mode="json")

        api = client.post("/api/optimize", json=request.model_dump(mode="json")).json()
        assert api == direct
        assert "deal_context" not in json.dumps(api)

    def test_optimize_response_has_no_deal_context_key(self):
        response = client.post("/api/optimize", json=_WALMART_REQUEST)
        assert response.status_code == 200
        assert "deal_context" not in response.text


class TestOptimizeWithDealContext:
    def test_bridged_items_receive_deal_context(self):
        response = client.post("/api/optimize/with-deal-context", json=_WALMART_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data["is_mock_data"] is True

        items_by_name = {}
        for plan in data["plans"]:
            for item in plan["items"]:
                name = item["requested_item"]["name"]
                items_by_name[name] = item

        assert items_by_name["whole milk"]["deal_context"] is not None
        assert items_by_name["whole milk"]["deal_context"]["product_id"] == "prod-gv-milk"
        assert "signal" in items_by_name["whole milk"]["deal_context"]

        assert items_by_name["eggs"]["deal_context"] is not None
        assert items_by_name["eggs"]["deal_context"]["product_id"] == "prod-gv-eggs"

        assert items_by_name["whole wheat bread"]["deal_context"] is not None
        assert items_by_name["whole wheat bread"]["deal_context"]["product_id"] == "prod-gv-wheat-bread"

    def test_unbridged_item_deal_context_is_null(self):
        response = client.post("/api/optimize/with-deal-context", json=_WALMART_REQUEST)
        assert response.status_code == 200

        chicken_items = []
        for plan in response.json()["plans"]:
            for item in plan["items"]:
                if item["requested_item"]["name"] == "chicken":
                    chicken_items.append(item)

        assert len(chicken_items) == 1
        assert chicken_items[0]["deal_context"] is None
        assert chicken_items[0]["chosen_product"].get("product_id") is None

    def test_anomaly_lookup_built_once_per_request(self):
        """Endpoint handler calls build_anomalies_by_product_id once (not per item)."""
        import inspect
        from backend import app as app_module

        source = inspect.getsource(app_module.optimize_with_deal_context)
        assert source.count("build_anomalies_by_product_id(") == 1
