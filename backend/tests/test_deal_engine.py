"""Tests for deterministic effective-price and savings calculations."""

from datetime import datetime, timezone

import pytest

from backend.deal_models import ConfidenceLabel, DealType, EvidenceType, PriceObservation, derive_confidence_label
from backend.engines.deal_engine import (
    aggregate_observation_confidence,
    build_deal_from_observations,
    calculate_effective_price,
    calculate_savings_amount,
    calculate_savings_percentage,
    extract_documented_discounts,
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
        with pytest.raises(ValueError, match="at least one PriceObservation"):
            build_deal_from_observations(
                deal_id="deal-empty",
                product_id="prod-1",
                retailer="Target",
                deal_type=DealType.SALE,
                observations=[],
            )

    def test_builds_with_observations(self):
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
        )
        assert deal.observed_at == observed
        assert deal.observation_ids == ["obs-1"]
        assert deal.current_price == 5.0

    def test_discounts_derived_from_observation_provenance(self):
        observed = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
        shelf = PriceObservation(
            id="obs-shelf",
            product_id="prod-1",
            retailer="Target",
            observed_price=4.99,
            observed_at=observed,
            evidence_type=EvidenceType.RETAILER_PUBLIC,
            confidence=0.85,
        )
        coupon = PriceObservation(
            id="obs-coupon",
            product_id="prod-1",
            retailer="Target",
            observed_price=4.99,
            observed_at=observed,
            evidence_type=EvidenceType.COUPON_FEED,
            confidence=0.70,
            documented_coupon_value=1.00,
        )
        rebate = PriceObservation(
            id="obs-rebate",
            product_id="prod-1",
            retailer="Target",
            observed_price=4.99,
            observed_at=observed,
            evidence_type=EvidenceType.REBATE_FEED,
            confidence=0.70,
            documented_rebate_value=1.00,
        )
        deal = build_deal_from_observations(
            deal_id="deal-stack",
            product_id="prod-1",
            retailer="Target",
            deal_type=DealType.STACK,
            observations=[shelf, coupon, rebate],
        )
        assert deal.coupon_value == 1.00
        assert deal.rebate_value == 1.00
        assert deal.effective_price == 2.99
        assert len(deal.observation_ids) == 3


class TestConfidenceAggregation:
    def test_community_report_penalized_not_verified(self):
        observed = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
        obs = PriceObservation(
            id="obs-community",
            product_id="prod-1",
            retailer="Target",
            observed_price=5.0,
            observed_at=observed,
            evidence_type=EvidenceType.COMMUNITY_REPORT,
            confidence=1.0,
        )
        score = aggregate_observation_confidence([obs], now=observed)
        assert score == 0.45
        assert derive_confidence_label(score) == ConfidenceLabel.LOW

    def test_extract_documented_discounts(self):
        observed = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
        observations = [
            PriceObservation(
                id="a",
                product_id="p",
                retailer="Target",
                observed_price=10.0,
                observed_at=observed,
                evidence_type=EvidenceType.COUPON_FEED,
                confidence=0.7,
                documented_coupon_value=2.0,
            ),
            PriceObservation(
                id="b",
                product_id="p",
                retailer="Target",
                observed_price=10.0,
                observed_at=observed,
                evidence_type=EvidenceType.REBATE_FEED,
                confidence=0.7,
                documented_rebate_value=1.5,
            ),
        ]
        assert extract_documented_discounts(observations) == (2.0, 1.5, 0.0)


class TestSavingsCalculations:
    def test_savings_amount(self):
        assert calculate_savings_amount(14.99, 9.99) == 5.0

    def test_savings_percentage_rounding(self):
        assert calculate_savings_percentage(14.99, 6.99) == 53.4

    def test_savings_percentage_zero_regular(self):
        assert calculate_savings_percentage(0.0, 5.0) == 0.0

    def test_savings_amount_never_negative(self):
        assert calculate_savings_amount(5.0, 10.0) == 0.0
