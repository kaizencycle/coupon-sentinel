"""Regression tests — existing shopping-list optimizer must remain functional."""

from backend.models import OptimizeRequest, ShoppingItem
from backend.engines.pricing_engine import optimize_shopping_list
from backend.providers import get_mock_store_items, get_mock_coupons


def test_optimizer_single_store_returns_plan():
    request = OptimizeRequest(
        shopping_list=[
            ShoppingItem(name="milk", quantity=1, unit="gallon", flexible=True),
            ShoppingItem(name="eggs", quantity=12, unit="count", flexible=True),
        ],
        zip_code="11566",
        preferred_stores=["Target", "Walmart"],
        allow_multi_store=False,
        rebate_apps=["Ibotta"],
    )
    result = optimize_shopping_list(
        request,
        get_mock_store_items(),
        get_mock_coupons(),
    )

    assert len(result.plans) == 1
    assert result.grand_total > 0
    assert result.total_savings >= 0
    assert len(result.action_steps) > 0


def test_optimizer_multi_store():
    request = OptimizeRequest(
        shopping_list=[
            ShoppingItem(name="milk", quantity=1, unit="gallon", flexible=True),
        ],
        zip_code="11566",
        preferred_stores=["Target", "Walmart"],
        allow_multi_store=True,
        rebate_apps=[],
    )
    result = optimize_shopping_list(
        request,
        get_mock_store_items(),
        get_mock_coupons(),
    )

    assert result.grand_total > 0
    assert len(result.plans) >= 1
