"""
Coupon Sentinel — Deal context bridge (PR-3)

Attaches PR-2 PriceAnomaly signals to optimizer output via product_id bridge.
No fuzzy matching, no fabricated signals — None when unbridged or no anomaly.
"""

from typing import Dict, List, Optional

from backend.deal_models import PriceObservation
from backend.engines.price_memory_engine import (
    GroupKey,
    build_price_anomaly,
    group_observations_by_market,
)
from backend.models import OptimizedItem
from backend.price_memory_models import OptimizedItemDealContext


def build_market_observation_index(
    observations: List[PriceObservation],
) -> Dict[GroupKey, List[PriceObservation]]:
    """
    Index observations by (zip_code, retailer, product_id) in a single pass.

    Each market group is keyed independently so attach_deal_context can resolve
    the optimizer item's store and request ZIP without cross-market overwrite.
    """
    return group_observations_by_market(observations)


def _market_lookup_key(
    zip_code: str,
    retailer: str,
    product_id: str,
) -> GroupKey:
    return (zip_code, retailer.lower(), product_id)


def attach_deal_context(
    item: OptimizedItem,
    market_observations: Dict[GroupKey, List[PriceObservation]],
    *,
    zip_code: str,
) -> Optional[OptimizedItemDealContext]:
    """
    Lookup deal context for an optimized item via bridged product_id.

    Uses the item's chosen_product.price as current_price — not the max/latest
    observation in the market group. Returns None (not NORMAL) when product_id
    is missing or no observations exist for the item's market.
    """
    product_id = item.chosen_product.product_id
    if not product_id:
        return None

    group_key = _market_lookup_key(
        zip_code,
        item.chosen_product.store_name,
        product_id,
    )
    observations = market_observations.get(group_key)
    if not observations:
        return None

    current_price = item.chosen_product.price
    anomaly = build_price_anomaly(
        anomaly_id=f"anomaly-{group_key[0] or 'no-zip'}-{group_key[1]}-{product_id}",
        group_key=group_key,
        current_price=current_price,
        observations=observations,
    )

    return OptimizedItemDealContext(
        product_id=product_id,
        signal=anomaly.signal,
        deviation_pct=anomaly.deviation_pct,
        baseline_median_price=anomaly.baseline.median_price,
        confidence=anomaly.confidence,
    )
