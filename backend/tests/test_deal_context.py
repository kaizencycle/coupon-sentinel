"""Tests for PR-3 product identity bridge and deal-aware optimize endpoint."""

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app import app
from backend.deal_models import EvidenceType, PriceObservation
from backend.engines import optimize_shopping_list
from backend.engines.deal_context_engine import attach_deal_context, build_market_observation_index
from backend.models import OptimizeRequest, ShoppingItem
from backend.price_memory_models import RecommendationSignal
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
        """Endpoint handler indexes market observations once (not per item)."""
        import inspect
        from backend import app as app_module

        source = inspect.getsource(app_module.optimize_with_deal_context)
        assert source.count("build_market_observation_index(") == 1
        assert source.count("group_observations_by_market(") == 0


class TestDealContextEngine:
    def _obs(
        self,
        obs_id: str,
        product_id: str,
        retailer: str,
        zip_code: str,
        price: float,
    ) -> PriceObservation:
        return PriceObservation(
            id=obs_id,
            product_id=product_id,
            retailer=retailer,
            zip_code=zip_code,
            observed_price=price,
            observed_at=datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc),
            evidence_type=EvidenceType.RETAILER_PUBLIC,
            confidence=0.85,
        )

    def test_multi_market_index_does_not_drop_other_markets(self):
        observations = [
            self._obs("w1", "prod-gv-milk", "Walmart", "11566", 3.48),
            self._obs("w2", "prod-gv-milk", "Walmart", "11566", 3.48),
            self._obs("w3", "prod-gv-milk", "Walmart", "11566", 3.48),
            self._obs("t1", "prod-gv-milk", "Target", "11429", 4.99),
            self._obs("t2", "prod-gv-milk", "Target", "11429", 4.99),
            self._obs("t3", "prod-gv-milk", "Target", "11429", 4.99),
        ]
        index = build_market_observation_index(observations)

        walmart_item = optimize_shopping_list(
            OptimizeRequest(
                shopping_list=[
                    ShoppingItem(name="whole milk", quantity=1, unit="gallon", flexible=True),
                ],
                zip_code="11566",
                preferred_stores=["Walmart"],
                allow_multi_store=False,
                rebate_apps=[],
            ),
            get_mock_store_items(),
            get_mock_coupons(),
        ).plans[0].items[0]

        target_item = walmart_item.model_copy(
            update={
                "chosen_product": walmart_item.chosen_product.model_copy(
                    update={"store_name": "Target", "price": 4.99}
                )
            }
        )

        walmart_ctx = attach_deal_context(walmart_item, index, zip_code="11566")
        target_ctx = attach_deal_context(target_item, index, zip_code="11429")

        assert walmart_ctx is not None
        assert target_ctx is not None
        assert walmart_ctx.baseline_median_price == 3.48
        assert target_ctx.baseline_median_price == 4.99

    def test_deal_context_uses_chosen_product_price_not_max_observation(self):
        observations = [
            self._obs("low-1", "prod-gv-milk", "Walmart", "11566", 10.0),
            self._obs("low-2", "prod-gv-milk", "Walmart", "11566", 10.0),
            self._obs("low-3", "prod-gv-milk", "Walmart", "11566", 10.0),
            self._obs("high", "prod-gv-milk", "Walmart", "11566", 15.0),
        ]
        index = build_market_observation_index(observations)

        item = optimize_shopping_list(
            OptimizeRequest(
                shopping_list=[
                    ShoppingItem(name="whole milk", quantity=1, unit="gallon", flexible=True),
                ],
                zip_code="11566",
                preferred_stores=["Walmart"],
                allow_multi_store=False,
                rebate_apps=[],
            ),
            get_mock_store_items(),
            get_mock_coupons(),
        ).plans[0].items[0]
        item = item.model_copy(
            update={
                "chosen_product": item.chosen_product.model_copy(update={"price": 8.0})
            }
        )

        ctx = attach_deal_context(item, index, zip_code="11566")

        assert ctx is not None
        # Median baseline is 10.0; shelf price 8.0 → 20% below baseline (not max obs 15.0).
        assert ctx.baseline_median_price == 10.0
        assert ctx.deviation_pct == 20.0
        assert ctx.signal == RecommendationSignal.GOOD_DEAL
