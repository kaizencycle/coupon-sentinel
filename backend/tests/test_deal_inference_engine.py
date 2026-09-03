"""Tests for the Milestone-3 deal inference engine (backend/engines/deal_inference_engine.py).

Operates on the Milestone 1 DB schema (PriceObservationRecord/DealEventRecord),
not the PR-1/2/3 mock fixture evidence layer — see module docstring for why
these are deliberately separate.
"""

from datetime import datetime, timedelta, timezone

from backend.engines.deal_inference_engine import (
    compute_baseline_price,
    group_observations,
    infer_coupon_deals,
    infer_deals,
    infer_price_drop_deals,
)
from backend.models import Coupon, CouponType, DiscountType


def _obs(product_id="milk-gallon", store_id="kroger-01400943", price=3.99, days_ago=0, obs_id=None):
    class _FakeObservation:
        pass

    o = _FakeObservation()
    o.id = obs_id
    o.product_id = product_id
    o.store_id = store_id
    o.price = price
    o.timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return o


class TestComputeBaselinePrice:
    def test_returns_none_below_minimum_samples(self):
        assert compute_baseline_price([_obs(price=3.99)]) is None

    def test_median_of_all_but_latest(self):
        observations = [
            _obs(price=3.99, days_ago=10),
            _obs(price=4.49, days_ago=5),
            _obs(price=2.00, days_ago=0),  # latest — excluded from baseline
        ]
        # baseline = median(3.99, 4.49) = 4.24
        assert compute_baseline_price(observations) == 4.24


class TestInferPriceDropDeals:
    def test_detects_significant_drop(self):
        observations = [
            _obs(obs_id=1, price=4.00, days_ago=10),
            _obs(obs_id=2, price=4.00, days_ago=5),
            _obs(obs_id=3, price=3.00, days_ago=0),  # 25% below baseline of 4.00
        ]
        grouped = group_observations(observations)
        deals = infer_price_drop_deals(grouped)

        assert len(deals) == 1
        deal = deals[0]
        assert deal["deal_type"] == "price_drop"
        assert deal["effective_price"] == 3.00
        assert deal["savings_amount"] == 1.00
        assert deal["evidence_ids"] == [3]

    def test_ignores_minor_fluctuation_below_threshold(self):
        observations = [
            _obs(obs_id=1, price=4.00, days_ago=10),
            _obs(obs_id=2, price=4.00, days_ago=5),
            _obs(obs_id=3, price=3.90, days_ago=0),  # 2.5% drop — below 10% threshold
        ]
        grouped = group_observations(observations)
        assert infer_price_drop_deals(grouped) == []

    def test_no_deal_with_insufficient_history(self):
        grouped = group_observations([_obs(obs_id=1, price=3.99)])
        assert infer_price_drop_deals(grouped) == []

    def test_separate_groups_evaluated_independently(self):
        observations = [
            _obs(obs_id=1, product_id="milk", store_id="storeA", price=4.00, days_ago=5),
            _obs(obs_id=2, product_id="milk", store_id="storeA", price=3.00, days_ago=0),
            _obs(obs_id=3, product_id="milk", store_id="storeB", price=4.00, days_ago=5),
            _obs(obs_id=4, product_id="milk", store_id="storeB", price=4.10, days_ago=0),
        ]
        grouped = group_observations(observations)
        deals = infer_price_drop_deals(grouped)
        assert len(deals) == 1
        assert deals[0]["store_id"] == "storeA"


class TestInferCouponDeals:
    def _coupon(self, item_filter="milk", value=0.50, discount_type=DiscountType.AMOUNT_OFF, store_scope="any"):
        return Coupon(
            id=f"c-{item_filter}",
            coupon_type=CouponType.MANUFACTURER,
            discount_type=discount_type,
            store_scope=store_scope,
            description="test coupon",
            item_filter=item_filter,
            value=value,
        )

    def test_matches_and_applies_amount_off(self):
        observations = [_obs(obs_id=1, product_id="whole-milk-1gal", price=4.00)]
        grouped = group_observations(observations)
        deals = infer_coupon_deals(grouped, [self._coupon(item_filter="milk", value=0.75)])

        assert len(deals) == 1
        assert deals[0]["deal_type"] == "coupon"
        assert deals[0]["effective_price"] == 3.25
        assert deals[0]["savings_amount"] == 0.75

    def test_percent_off_computed_against_price(self):
        observations = [_obs(obs_id=1, product_id="coffee-12oz", price=10.00)]
        grouped = group_observations(observations)
        coupon = self._coupon(item_filter="coffee", value=0.20, discount_type=DiscountType.PERCENT_OFF)
        deals = infer_coupon_deals(grouped, [coupon])

        assert deals[0]["savings_amount"] == 2.00
        assert deals[0]["effective_price"] == 8.00

    def test_no_match_no_deal(self):
        observations = [_obs(obs_id=1, product_id="paper-towels", price=12.00)]
        grouped = group_observations(observations)
        deals = infer_coupon_deals(grouped, [self._coupon(item_filter="milk")])
        assert deals == []

    def test_store_scoped_coupon_respects_scope(self):
        observations = [_obs(obs_id=1, product_id="milk-gallon", store_id="target-01", price=4.00)]
        grouped = group_observations(observations)
        coupon = self._coupon(item_filter="milk", store_scope="walmart-01")
        assert infer_coupon_deals(grouped, [coupon]) == []

    def test_picks_best_of_multiple_matching_coupons(self):
        observations = [_obs(obs_id=1, product_id="milk-gallon", price=4.00)]
        grouped = group_observations(observations)
        coupons = [self._coupon(value=0.25), self._coupon(value=1.00)]
        deals = infer_coupon_deals(grouped, coupons)
        assert deals[0]["savings_amount"] == 1.00

    def test_discount_never_exceeds_price(self):
        observations = [_obs(obs_id=1, product_id="milk-gallon", price=0.50)]
        grouped = group_observations(observations)
        deals = infer_coupon_deals(grouped, [self._coupon(value=5.00)])
        assert deals[0]["effective_price"] == 0.0
        assert deals[0]["savings_amount"] == 0.50


class TestInferDeals:
    def test_combines_and_ranks_by_savings(self):
        observations = [
            _obs(obs_id=1, product_id="milk-gallon", store_id="s1", price=4.00, days_ago=10),
            _obs(obs_id=2, product_id="milk-gallon", store_id="s1", price=4.00, days_ago=5),
            _obs(obs_id=3, product_id="milk-gallon", store_id="s1", price=3.00, days_ago=0),  # $1.00 price-drop
            _obs(obs_id=4, product_id="coffee-12oz", store_id="s1", price=10.00, days_ago=0),  # coupon-only
        ]
        coupons = [
            Coupon(
                id="c-coffee",
                coupon_type=CouponType.MANUFACTURER,
                discount_type=DiscountType.AMOUNT_OFF,
                store_scope="any",
                description="coffee coupon",
                item_filter="coffee",
                value=2.50,
            )
        ]
        deals = infer_deals(observations, coupons)

        assert len(deals) == 2
        # Ranked descending by savings_amount: coffee coupon ($2.50) before milk price-drop ($1.00)
        assert deals[0]["savings_amount"] == 2.50
        assert deals[1]["savings_amount"] == 1.00
