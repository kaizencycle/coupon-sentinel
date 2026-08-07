"""
Coupon Sentinel — Local Price Memory Engine (PR-2)

Deterministic aggregation and anomaly detection over PR-1's PriceObservation
evidence. No LLM scoring, no retailer scraping — pure arithmetic over data
PR-1 already collects.

    Individual observations
            ↓
    ZIP / retailer / SKU grouping         (group_observations_by_market)
            ↓
    all-time price history, median     (compute_local_baseline)
            ↓
    deviation off baseline             (compute_deviation_pct)
            ↓
    BUY / WAIT / NORMAL signal         (derive_recommendation_signal)
"""

from collections import defaultdict
from datetime import datetime
from statistics import median
from typing import Dict, List, Optional, Tuple

from backend.deal_models import PriceObservation
from backend.engines.deal_engine import aggregate_observation_confidence, build_evidence_summary
from backend.price_memory_models import (
    MIN_BASELINE_SAMPLES,
    LocalPriceBaseline,
    PriceAnomaly,
    PriceAnomalyDetail,
    RecommendationSignal,
)

# Thresholds (named constants — tune here, not inline in derive logic).
# 40%: meaningful clearance/penny-pull territory, not routine week-to-week noise.
_STRONG_DEAL_THRESHOLD_PCT = 40.0
# 15–40%: real actionable sale, not rare enough for STRONG urgency.
_GOOD_DEAL_THRESHOLD_PCT = 15.0
# ±15%: normal grocery price noise band.
_NORMAL_BAND_PCT = 15.0

GroupKey = Tuple[Optional[str], str, str]
"""(zip_code, retailer_normalized, product_id) — canonical local-market unit."""


def _normalize_retailer(retailer: str) -> str:
    return retailer.lower()


def _market_key(observation: PriceObservation) -> GroupKey:
    return (
        observation.zip_code,
        _normalize_retailer(observation.retailer),
        observation.product_id,
    )


def group_observations_by_market(
    observations: List[PriceObservation],
) -> Dict[GroupKey, List[PriceObservation]]:
    """
    Group observations by (zip_code, retailer, product_id) in a single pass.

    Audit note (C-396): index once — do not re-filter the full observation list
    per product inside nested loops (PR-1 optimize_multi_store anti-pattern).
    Observations with None zip_code group under (None, retailer, product_id).
    """
    groups: Dict[GroupKey, List[PriceObservation]] = defaultdict(list)
    for observation in observations:
        groups[_market_key(observation)].append(observation)
    return dict(groups)


def compute_local_baseline(
    group_key: GroupKey,
    observations: List[PriceObservation],
) -> LocalPriceBaseline:
    """
    All-time median baseline for one market group — no decay, no freshness weighting.

    Freshness belongs only in aggregate_observation_confidence (deal_engine.py).
    """
    if not observations:
        raise ValueError("compute_local_baseline requires at least one observation")

    zip_code, _retailer_key, product_id = group_key
    prices = [o.observed_price for o in observations]
    observed_times = [o.observed_at for o in observations]
    canonical = max(observations, key=lambda o: o.observed_at)

    return LocalPriceBaseline(
        product_id=product_id,
        zip_code=zip_code,
        retailer=canonical.retailer,
        median_price=median(prices),
        sample_size=len(observations),
        min_observed=min(prices),
        max_observed=max(prices),
        first_observed_at=min(observed_times),
        last_observed_at=max(observed_times),
    )


def compute_deviation_pct(current_price: float, baseline: LocalPriceBaseline) -> float:
    """
    Percentage current_price is below (positive) or above (negative) median baseline.

    deviation_pct = (baseline.median_price - current_price) / baseline.median_price * 100
    """
    if baseline.median_price <= 0:
        return 0.0
    return (baseline.median_price - current_price) / baseline.median_price * 100


def derive_recommendation_signal(
    deviation_pct: float,
    sample_size: int,
    min_samples: int = MIN_BASELINE_SAMPLES,
) -> RecommendationSignal:
    """
    Deterministic threshold mapping. sample_size gate is evaluated first —
    a dramatic deviation from thin data remains INSUFFICIENT_DATA.
    """
    if sample_size < min_samples:
        return RecommendationSignal.INSUFFICIENT_DATA

    if deviation_pct >= _STRONG_DEAL_THRESHOLD_PCT:
        return RecommendationSignal.STRONG_DEAL
    if deviation_pct >= _GOOD_DEAL_THRESHOLD_PCT:
        return RecommendationSignal.GOOD_DEAL
    if deviation_pct < -_NORMAL_BAND_PCT:
        return RecommendationSignal.ABOVE_BASELINE
    if -_NORMAL_BAND_PCT <= deviation_pct < _GOOD_DEAL_THRESHOLD_PCT:
        return RecommendationSignal.NORMAL
    return RecommendationSignal.NORMAL


def build_price_anomaly(
    anomaly_id: str,
    group_key: GroupKey,
    current_price: float,
    observations: List[PriceObservation],
    *,
    now: Optional[datetime] = None,
) -> PriceAnomaly:
    """
    Composition function — mirrors PR-1 build_deal_from_observations() structure.

    Reuses aggregate_observation_confidence and build_evidence_summary from
    deal_engine.py — do not duplicate confidence logic here.
    """
    if not observations:
        raise ValueError("build_price_anomaly requires at least one observation")

    baseline = compute_local_baseline(group_key, observations)
    deviation = compute_deviation_pct(current_price, baseline)
    signal = derive_recommendation_signal(deviation, baseline.sample_size)
    confidence = aggregate_observation_confidence(observations, now=now)
    evidence_summary = build_evidence_summary(observations)
    evidence_types = sorted(
        {o.evidence_type for o in observations},
        key=lambda evidence: evidence.value,
    )
    computed_at = now or max(o.observed_at for o in observations)
    zip_code, _retailer_key, product_id = group_key
    display_retailer = max(observations, key=lambda o: o.observed_at).retailer

    return PriceAnomaly(
        id=anomaly_id,
        product_id=product_id,
        zip_code=zip_code,
        retailer=display_retailer,
        current_price=current_price,
        baseline=baseline,
        deviation_pct=round(deviation, 1),
        signal=signal,
        confidence=confidence,
        evidence_types=evidence_types,
        evidence_summary=evidence_summary,
        observation_ids=[o.id for o in observations],
        computed_at=computed_at,
    )


def _anomaly_id_for_key(group_key: GroupKey) -> str:
    zip_part = group_key[0] or "no-zip"
    return f"anomaly-{zip_part}-{group_key[1]}-{group_key[2]}"


def build_market_price_anomaly(
    group_key: GroupKey,
    observations: List[PriceObservation],
    *,
    min_samples: int = MIN_BASELINE_SAMPLES,
    now: Optional[datetime] = None,
) -> PriceAnomaly:
    """Build anomaly for a grouped market using the latest observation as current price."""
    if not observations:
        raise ValueError("build_market_price_anomaly requires at least one observation")

    latest = max(observations, key=lambda o: o.observed_at)
    anomaly = build_price_anomaly(
        _anomaly_id_for_key(group_key),
        group_key,
        latest.observed_price,
        observations,
        now=now,
    )
    if min_samples != MIN_BASELINE_SAMPLES:
        anomaly = anomaly.model_copy(
            update={
                "signal": derive_recommendation_signal(
                    anomaly.deviation_pct,
                    anomaly.baseline.sample_size,
                    min_samples=min_samples,
                )
            }
        )
    return anomaly


def build_all_local_baselines(
    observations: List[PriceObservation],
) -> List[LocalPriceBaseline]:
    groups = group_observations_by_market(observations)
    return [
        compute_local_baseline(key, group_observations)
        for key, group_observations in groups.items()
        if group_observations
    ]


def build_all_price_anomalies(
    observations: List[PriceObservation],
    *,
    min_samples: int = MIN_BASELINE_SAMPLES,
    now: Optional[datetime] = None,
) -> List[PriceAnomaly]:
    groups = group_observations_by_market(observations)
    return [
        build_market_price_anomaly(
            key,
            group_observations,
            min_samples=min_samples,
            now=now,
        )
        for key, group_observations in groups.items()
        if group_observations
    ]


def enrich_price_anomaly(
    anomaly: PriceAnomaly,
    product_name: Optional[str] = None,
    product_brand: Optional[str] = None,
) -> PriceAnomalyDetail:
    return PriceAnomalyDetail(
        **anomaly.model_dump(),
        product_name=product_name,
        product_brand=product_brand,
    )
