"""
Coupon Sentinel — Local Price Memory Models (PR-2)

Canonical data model for local market memory, built on top of PR-1's
PriceObservation evidence layer. Additive only — does not modify any
model in deal_models.py.

Architecture principle (extends PR-1's layering, never collapse):
  Evidence → PriceObservation → DealEvent → Consumer recommendation
                    ↓
            LocalPriceBaseline → PriceAnomaly → RecommendationSignal

Ratified design decisions (ATLAS Handoff, C-396 — do not relitigate mid-PR):
  - Baseline window is ALL-TIME, no decay.
  - Baseline statistic is MEDIAN, not mean.
  - Baseline and confidence are separate concerns.
  - Below MIN_BASELINE_SAMPLES → INSUFFICIENT_DATA.

Consumer protection guardrails (inherited from PR-1):
  - A price anomaly is an observation, not an accusation.
  - No behavioral profiling. No identity persisted with price memory.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.deal_models import EvidenceType


MIN_BASELINE_SAMPLES = 3
"""Minimum PriceObservations before a signal is trustworthy."""


class RecommendationSignal(str, Enum):
    """Deterministic classification of current price vs. local baseline."""

    STRONG_DEAL = "strong_deal"
    GOOD_DEAL = "good_deal"
    NORMAL = "normal"
    ABOVE_BASELINE = "above_baseline"
    INSUFFICIENT_DATA = "insufficient_data"


class LocalPriceBaseline(BaseModel):
    """
    All-time median local price for (zip_code, retailer, product_id).

    Grouping key excludes store_id — store_id stays on observations for
    drill-down, not as the primary market unit.
    """

    product_id: str
    zip_code: Optional[str] = None
    retailer: str
    median_price: float = Field(..., ge=0.0)
    sample_size: int = Field(..., ge=0)
    min_observed: float = Field(..., ge=0.0)
    max_observed: float = Field(..., ge=0.0)
    first_observed_at: datetime
    last_observed_at: datetime


class PriceAnomaly(BaseModel):
    """
    Interprets a current price against a LocalPriceBaseline.

    confidence comes from PR-1 aggregate_observation_confidence() — not
    recomputed in the price-memory engine.
    """

    id: str
    product_id: str
    zip_code: Optional[str] = None
    retailer: str
    current_price: float = Field(..., ge=0.0)
    baseline: LocalPriceBaseline
    deviation_pct: float
    signal: RecommendationSignal
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_types: List[EvidenceType] = Field(default_factory=list)
    evidence_summary: List[str] = Field(default_factory=list)
    observation_ids: List[str] = Field(default_factory=list)
    computed_at: datetime
    is_mock_data: bool = True


class PriceAnomalyDetail(PriceAnomaly):
    """API-enriched anomaly with product display context."""

    product_name: Optional[str] = None
    product_brand: Optional[str] = None


class OptimizedItemDealContext(BaseModel):
    """
    Local price-memory context attached to an optimized catalog item.

    Separate from OptimizedItem — attachable only when product_id bridge exists.
    """

    product_id: str
    signal: RecommendationSignal
    deviation_pct: float
    baseline_median_price: float
    confidence: float = Field(..., ge=0.0, le=1.0)
