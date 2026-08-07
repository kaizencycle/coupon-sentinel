"""
Coupon Sentinel — Deal context bridge (PR-3)

Attaches PR-2 PriceAnomaly signals to optimizer output via product_id bridge.
No fuzzy matching, no fabricated signals — None when unbridged or no anomaly.
"""

from typing import Dict, List, Optional

from backend.deal_models import PriceObservation
from backend.engines.price_memory_engine import (
    build_price_anomaly,
    group_observations_by_market,
)
from backend.models import OptimizedItem
from backend.price_memory_models import OptimizedItemDealContext, PriceAnomaly


def build_anomalies_by_product_id(
    observations: List[PriceObservation],
) -> Dict[str, PriceAnomaly]:
    """
    Precompute anomalies once per request — single group_observations_by_market pass.

    Keyed by product_id. When multiple market groups share a product_id, the last
    group processed wins; attach_deal_context also matches retailer + zip_code.
    """
    grouped = group_observations_by_market(observations)
    anomalies: Dict[str, PriceAnomaly] = {}

    for group_key, group_observations in grouped.items():
        gz, gr, gp = group_key
        current_price = max(o.observed_price for o in group_observations)
        anomaly = build_price_anomaly(
            anomaly_id=f"anomaly-{gr}-{gz or 'no-zip'}-{gp}",
            group_key=group_key,
            current_price=current_price,
            observations=group_observations,
        )
        anomalies[gp] = anomaly

    return anomalies


def attach_deal_context(
    item: OptimizedItem,
    anomalies_by_product_id: Dict[str, PriceAnomaly],
    *,
    zip_code: str,
) -> Optional[OptimizedItemDealContext]:
    """
    Lookup deal context for an optimized item via bridged product_id.

    Returns None (not NORMAL) when product_id is missing, no anomaly exists,
    or the anomaly's market does not match the item's store and request ZIP.
    """
    product_id = item.chosen_product.product_id
    if not product_id:
        return None

    anomaly = anomalies_by_product_id.get(product_id)
    if anomaly is None:
        return None

    if (anomaly.zip_code or "") != zip_code:
        return None
    if anomaly.retailer.lower() != item.chosen_product.store_name.lower():
        return None

    return OptimizedItemDealContext(
        product_id=product_id,
        signal=anomaly.signal,
        deviation_pct=anomaly.deviation_pct,
        baseline_median_price=anomaly.baseline.median_price,
        confidence=anomaly.confidence,
    )
