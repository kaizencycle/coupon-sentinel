"""
Coupon Sentinel - Deal Inference Engine (Milestone 3)

Turns persisted price_observations (the Milestone 1 DB schema, populated by
Milestone 2's Kroger client) into deal_events: a price-drop event when the
latest observation is meaningfully below the product's local baseline, and a
coupon event for each matching applicable coupon.

Deliberately separate from the richer, already-merged PR-1/2/3 evidence
layer (backend/deal_models.py, backend/engines/price_memory_engine.py,
backend/providers/mock_deal_data.py), which operates on mock fixture data
with its own (zip_code/retailer/evidence_type/confidence) schema. Unifying
the two evidence layers is real future work, not something to collapse here
without a DB schema redesign — this module is the literal Milestone-3
deliverable from the phase-1 handoff: it works against the real
Postgres-backed price_observations table, not fixtures.

Known limitation: coupon matching is a coarse substring match of a coupon's
item_filter (e.g. "milk", "coffee") against product_id. This works for
human-readable product identifiers but Kroger's real product IDs are opaque
UPC-style numbers, so coupon matches against real Kroger data will rarely
fire until a product name/category field is added to the observation
schema — tracked as follow-up, not solved here.
"""

from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from backend.db_models import DealEventRecord, PriceObservationRecord
from backend.models import Coupon, DiscountType

# >= this much below baseline counts as a "price_drop" deal. Deliberately
# coarser than PR-2's price_memory_engine thresholds (40%/15%) since this
# engine has no confidence/freshness weighting yet — a simple, conservative
# single threshold until real Kroger data volume justifies more nuance.
PRICE_DROP_THRESHOLD_PCT = 10.0

# Fewer observations than this for a (product_id, store_id) group -> no
# baseline can be computed, so no price-drop detection (not a false "no deal").
MIN_OBSERVATIONS_FOR_BASELINE = 2

GroupKey = tuple[str, str]  # (product_id, store_id)


def group_observations(observations: list[PriceObservationRecord]) -> dict[GroupKey, list[PriceObservationRecord]]:
    grouped: dict[GroupKey, list[PriceObservationRecord]] = defaultdict(list)
    for obs in observations:
        grouped[(obs.product_id, obs.store_id)].append(obs)
    return dict(grouped)


def compute_baseline_price(observations: list[PriceObservationRecord]) -> Optional[float]:
    """
    Median of all observations *except* the most recent one, so the baseline
    doesn't include the very price we're checking against it. All-time, no
    decay — same philosophy as PR-2's compute_local_baseline, simplified
    (no per-market grouping; that's the caller's job via group_observations).
    """
    if len(observations) < MIN_OBSERVATIONS_FOR_BASELINE:
        return None

    ordered = sorted(observations, key=lambda o: o.timestamp)
    prior = ordered[:-1]
    prices = sorted(float(o.price) for o in prior)

    mid = len(prices) // 2
    if len(prices) % 2 == 0:
        return (prices[mid - 1] + prices[mid]) / 2
    return prices[mid]


def infer_price_drop_deals(grouped_observations: dict[GroupKey, list[PriceObservationRecord]]) -> list[dict]:
    """One price_drop deal per group whose latest price is >= PRICE_DROP_THRESHOLD_PCT below baseline."""
    deals = []
    for (product_id, store_id), observations in grouped_observations.items():
        baseline = compute_baseline_price(observations)
        if baseline is None or baseline <= 0:
            continue

        latest = max(observations, key=lambda o: o.timestamp)
        latest_price = float(latest.price)
        drop_pct = (baseline - latest_price) / baseline * 100

        if drop_pct >= PRICE_DROP_THRESHOLD_PCT:
            deals.append(
                {
                    "product_id": product_id,
                    "store_id": store_id,
                    "deal_type": "price_drop",
                    "effective_price": round(latest_price, 2),
                    "savings_amount": round(baseline - latest_price, 2),
                    "evidence_ids": [latest.id],
                }
            )
    return deals


def _matching_coupons(product_id: str, store_id: str, coupons: list[Coupon]) -> list[Coupon]:
    """
    Note: a coupon's item_filter of "any" (e.g. a whole-receipt rebate like
    "25 points on any receipt") is deliberately NOT treated as a wildcard
    match here — it isn't a per-item price reduction, so surfacing it as a
    "deal" on every single product observed would be noise, not signal.
    Only store_scope == "any" (any store) is a real wildcard.
    """
    matches = []
    for coupon in coupons:
        if coupon.store_scope and coupon.store_scope.lower() not in ("any", store_id.lower()):
            continue
        if coupon.item_filter.lower() in product_id.lower():
            matches.append(coupon)
    return matches


def _coupon_discount(coupon: Coupon, price: float) -> float:
    if coupon.discount_type == DiscountType.PERCENT_OFF:
        return price * coupon.value
    if coupon.discount_type in (DiscountType.AMOUNT_OFF, DiscountType.BOGO_HALF, DiscountType.BOGO_FREE):
        return coupon.value
    return 0.0


def infer_coupon_deals(
    grouped_observations: dict[GroupKey, list[PriceObservationRecord]], coupons: list[Coupon]
) -> list[dict]:
    """One coupon deal per group with >=1 matching coupon, applied to the group's latest price."""
    deals = []
    for (product_id, store_id), observations in grouped_observations.items():
        matches = _matching_coupons(product_id, store_id, coupons)
        if not matches:
            continue

        latest = max(observations, key=lambda o: o.timestamp)
        latest_price = float(latest.price)

        best_coupon = max(matches, key=lambda c: _coupon_discount(c, latest_price))
        discount = min(_coupon_discount(best_coupon, latest_price), latest_price)
        if discount <= 0:
            continue

        deals.append(
            {
                "product_id": product_id,
                "store_id": store_id,
                "deal_type": "coupon",
                "effective_price": round(latest_price - discount, 2),
                "savings_amount": round(discount, 2),
                "evidence_ids": [latest.id],
            }
        )
    return deals


def infer_deals(observations: list[PriceObservationRecord], coupons: list[Coupon]) -> list[dict]:
    """Combine price-drop and coupon deals, ranked by savings_amount descending."""
    grouped = group_observations(observations)
    deals = infer_price_drop_deals(grouped) + infer_coupon_deals(grouped, coupons)
    return sorted(deals, key=lambda d: d["savings_amount"], reverse=True)


def persist_deals(deals: list[dict], db: Session) -> list[DealEventRecord]:
    """Materialize inferred deal dicts as DealEventRecord rows."""
    records = []
    for deal in deals:
        record = DealEventRecord(
            product_id=deal["product_id"],
            store_id=deal["store_id"],
            deal_type=deal["deal_type"],
            effective_price=deal["effective_price"],
            savings_amount=deal["savings_amount"],
            evidence_ids=deal["evidence_ids"],
        )
        db.add(record)
        records.append(record)

    if records:
        db.commit()
        for record in records:
            db.refresh(record)

    return records
