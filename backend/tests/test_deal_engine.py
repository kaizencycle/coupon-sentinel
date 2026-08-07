"""Tests for deterministic effective-price and savings calculations."""

import pytest

from backend.engines.deal_engine import (
    calculate_effective_price,
    calculate_savings_amount,
    calculate_savings_percentage,
)


class TestEffectivePrice:
    def test_standard_stack(self):
        """$14.99 - $3 coupon - $2 rebate = $9.99 effective."""
        assert calculate_effective_price(14.99, coupon_value=3.0, rebate_value=2.0) == 9.99

    def test_tide_stack_example(self):
        """Sale price with coupon and rebate stack."""
        assert calculate_effective_price(11.99, coupon_value=3.0, rebate_value=2.0) == 6.99

    def test_loyalty_included(self):
        assert calculate_effective_price(
            10.0, coupon_value=1.0, loyalty_savings=2.0, rebate_value=1.0
        ) == 6.0

    def test_no_negative_price(self):
        """Excess discounts must not produce invalid consumer totals."""
        assert calculate_effective_price(5.0, coupon_value=10.0) == 0.0
        assert calculate_effective_price(
            5.0, coupon_value=3.0, loyalty_savings=2.0, rebate_value=5.0
        ) == 0.0


class TestBuildDealFromObservations:
    def test_rejects_empty_observations(self):
        from backend.deal_models import DealType
        from backend.engines.deal_engine import build_deal_from_observations

        with pytest.raises(ValueError, match="at least one PriceObservation"):
            build_deal_from_observations(
                deal_id="deal-empty",
                product_id="prod-1",
                retailer="Target",
                deal_type=DealType.SALE,
                observations=[],
                current_price=5.0,
            )

    def test_builds_with_observations(self):
        from datetime import datetime, timezone

        from backend.deal_models import DealType, EvidenceType, PriceObservation
        from backend.engines.deal_engine import build_deal_from_observations

        observed = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
        obs = PriceObservation(
            id="obs-1",
            product_id="prod-1",
            retailer="Target",
            observed_price=5.0,
            observed_at=observed,
            evidence_type=EvidenceType.RETAILER_PUBLIC,
            confidence=0.8,
        )
        deal = build_deal_from_observations(
            deal_id="deal-ok",
            product_id="prod-1",
            retailer="Target",
            deal_type=DealType.SALE,
            observations=[obs],
            current_price=5.0,
        )
        assert deal.observed_at == observed
        assert deal.observation_ids == ["obs-1"]


class TestSavingsCalculations:
    def test_savings_amount(self):
        assert calculate_savings_amount(14.99, 9.99) == 5.0

    def test_savings_percentage_rounding(self):
        assert calculate_savings_percentage(14.99, 6.99) == 53.4

    def test_savings_percentage_zero_regular(self):
        assert calculate_savings_percentage(0.0, 5.0) == 0.0

    def test_savings_amount_never_negative(self):
        assert calculate_savings_amount(5.0, 10.0) == 0.0
