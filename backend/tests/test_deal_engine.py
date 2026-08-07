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


class TestSavingsCalculations:
    def test_savings_amount(self):
        assert calculate_savings_amount(14.99, 9.99) == 5.0

    def test_savings_percentage_rounding(self):
        assert calculate_savings_percentage(14.99, 6.99) == 53.4

    def test_savings_percentage_zero_regular(self):
        assert calculate_savings_percentage(0.0, 5.0) == 0.0

    def test_savings_amount_never_negative(self):
        assert calculate_savings_amount(5.0, 10.0) == 0.0
