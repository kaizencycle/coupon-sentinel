"""
Coupon Sentinel — Local Price Memory Models (PR-2)

Additive layer on PR-1 evidence substrate. Groups observations into local market
memory and derives deterministic BUY/WAIT/NORMAL signals from median baselines.

Baseline (median, all-time, no decay) is independent from observation confidence
(freshness weighting lives in PR-1's aggregate_observation_confidence only).
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

# Canonical local-market unit: (zip_code, retailer_lower, product_id).
# Retailer in the key is normalized lowercase for grouping; API models use display casing.
GroupKey = Tuple[str, str, str]


class RecommendationSignal(str, Enum):
    """Deterministic signal from deviation off local median baseline."""

    STRONG_DEAL = "STRONG_DEAL"
    GOOD_DEAL = "GOOD_DEAL"
    NORMAL = "NORMAL"
    ABOVE_BASELINE = "ABOVE_BASELINE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class LocalPriceBaseline(BaseModel):
    """All-time median price memory for one local market group."""

    product_id: str
    zip_code: str
    retailer: str
    store_id: Optional[str] = None
    median_price: float
    sample_size: int
    min_observed: float
    max_observed: float
    first_observed_at: datetime
    last_observed_at: datetime


class PriceAnomaly(BaseModel):
    """
    Current price vs local baseline with deterministic recommendation signal.

    A price anomaly is an observation — not inventory evidence.
    """

    product_id: str
    zip_code: str
    retailer: str
    store_id: Optional[str] = None
    current_price: float
    observed_at: datetime
    observation_ids: List[str] = Field(default_factory=list)
    baseline: Optional[LocalPriceBaseline] = None
    deviation_pct: Optional[float] = None
    signal: RecommendationSignal
    evidence_summary: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    is_mock_data: bool = True


class PriceAnomalyDetail(PriceAnomaly):
    """API-enriched anomaly with product display context."""

    product_name: Optional[str] = None
    product_brand: Optional[str] = None
