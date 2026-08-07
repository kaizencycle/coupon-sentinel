"""Tests for penny/pull semantics and mock deal fixtures."""

from backend.deal_models import DealType, EvidenceType
from backend.providers.mock_deal_data import (
    get_mock_deal_events,
    get_mock_price_observations,
)


class TestPennyPullSemantics:
    def test_penny_or_pull_does_not_confirm_inventory(self):
        penny_deals = [
            d for d in get_mock_deal_events()
            if d.deal_type == DealType.PENNY_OR_PULL
        ]
        assert len(penny_deals) >= 1
        for deal in penny_deals:
            assert deal.inventory_confirmed is False

    def test_penny_observation_exists(self):
        penny_obs = [
            o for o in get_mock_price_observations()
            if o.observed_price == 0.01
        ]
        assert len(penny_obs) >= 1


class TestMockFixtures:
    def test_receipt_backed_observation_exists(self):
        receipts = [
            o for o in get_mock_price_observations()
            if o.evidence_type == EvidenceType.RECEIPT
        ]
        assert len(receipts) >= 1
        assert receipts[0].retailer == "Target"
        assert receipts[0].zip_code == "11429"

    def test_clearance_observation_exists(self):
        clearance_deals = [
            d for d in get_mock_deal_events()
            if d.deal_type == DealType.CLEARANCE
        ]
        assert len(clearance_deals) >= 1

    def test_two_observations_same_sku_location(self):
        milk_obs = [
            o for o in get_mock_price_observations()
            if o.product_id == "prod-gv-milk"
            and o.retailer == "Walmart"
            and o.zip_code == "11566"
        ]
        assert len(milk_obs) >= 2

    def test_price_anomaly_exists(self):
        anomalies = [
            d for d in get_mock_deal_events()
            if d.deal_type == DealType.PRICE_ANOMALY
        ]
        assert len(anomalies) >= 1

    def test_tide_stack_deal_traceable_to_observations(self):
        tide = next(d for d in get_mock_deal_events() if d.id == "deal-tide-stack")
        assert len(tide.observation_ids) >= 3
        assert tide.effective_price == 6.99
        assert tide.coupon_value == 3.00
        assert tide.rebate_value == 2.00
        assert tide.deal_type == DealType.STACK

    def test_chips_rebate_stack_discounts_trace_to_observations(self):
        chips = next(d for d in get_mock_deal_events() if d.id == "deal-chips-rebate-stack")
        assert chips.coupon_value == 1.00
        assert chips.rebate_value == 1.00
        assert chips.effective_price == 2.99
        assert "obs-chips-coupon-feed" in chips.observation_ids
        assert "obs-chips-rebate-feed" in chips.observation_ids
