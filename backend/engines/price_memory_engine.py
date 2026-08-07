"""
Coupon Sentinel — Local Price Memory Engine (PR-2)

Deterministic arithmetic over PR-1 PriceObservations. No LLM inference, no decay
on baselines, no freshness weighting in baseline math (that stays in deal_engine).
"""

from datetime import datetime
from statistics import median
from typing import Dict, List, Optional

from backend.deal_models import PriceObservation
from backend.engines.deal_engine import (
    aggregate_observation_confidence,
    build_evidence_summary,
)
from backend.price_memory_models import (
    GroupKey,
    LocalPriceBaseline,
    PriceAnomaly,
    PriceAnomalyDetail,
    RecommendationSignal,
)

# Minimum observations before a signal is actionable — one price is not a baseline.
_MIN_SAMPLES_DEFAULT = 3

# Deviation thresholds (percent below median = positive deviation_pct).
# 40%: captures genuine clearance/stack opportunities without crying wolf on routine sales.
# 15%: separates meaningful sales from everyday ±noise around a stable SKU price.
# ±15% band: grocery SKUs often fluctuate within loyalty/sale cycles at one store.
_STRONG_DEAL_THRESHOLD = 40.0
_GOOD_DEAL_THRESHOLD = 15.0
_NORMAL_BAND = 15.0


def _market_key(observation: PriceObservation) -> GroupKey:
    zip_code = observation.zip_code or ""
    return (zip_code, observation.retailer, observation.product_id)


def group_observations_by_market(
    observations: List[PriceObservation],
) -> Dict[GroupKey, List[PriceObservation]]:
    """Single-pass grouping by canonical local-market unit."""
    groups: Dict[GroupKey, List[PriceObservation]] = {}
    for observation in observations:
        key = _market_key(observation)
        groups.setdefault(key, []).append(observation)
    return groups


def compute_local_baseline(
    observations: List[PriceObservation],
) -> Optional[LocalPriceBaseline]:
    """
    All-time median of observed_price — no decay, no freshness weighting.

    Returns None when observations is empty (caller degrades to INSUFFICIENT_DATA).
    """
    if not observations:
        return None

    prices = [o.observed_price for o in observations]
    observed_times = [o.observed_at for o in observations]
    first = observations[0]

    return LocalPriceBaseline(
        product_id=first.product_id,
        zip_code=first.zip_code or "",
        retailer=first.retailer,
        store_id=first.store_id,
        median_price=median(prices),
        sample_size=len(observations),
        min_observed=min(prices),
        max_observed=max(prices),
        first_observed_at=min(observed_times),
        last_observed_at=max(observed_times),
    )


def compute_deviation_pct(current_price: float, baseline: LocalPriceBaseline) -> float:
    """
    Percent deviation below baseline (positive = cheaper than median).

    Formula: (median_price - current_price) / median_price * 100
    """
    if baseline.median_price <= 0:
        return 0.0
    return (baseline.median_price - current_price) / baseline.median_price * 100


def derive_recommendation_signal(
    deviation_pct: float,
    sample_size: int,
    min_samples: int = _MIN_SAMPLES_DEFAULT,
) -> RecommendationSignal:
    """Map deviation and sample size to a deterministic signal."""
    if sample_size < min_samples:
        return RecommendationSignal.INSUFFICIENT_DATA

    if deviation_pct >= _STRONG_DEAL_THRESHOLD:
        return RecommendationSignal.STRONG_DEAL
    if deviation_pct >= _GOOD_DEAL_THRESHOLD:
        return RecommendationSignal.GOOD_DEAL
    if deviation_pct <= -_NORMAL_BAND:
        return RecommendationSignal.ABOVE_BASELINE
    return RecommendationSignal.NORMAL


def build_price_anomaly(
    observations: List[PriceObservation],
    current_price: float,
    observed_at: datetime,
    observation_ids: List[str],
    *,
    store_id: Optional[str] = None,
    min_samples: int = _MIN_SAMPLES_DEFAULT,
    now: Optional[datetime] = None,
) -> PriceAnomaly:
    """
    Compose baseline, deviation, signal, and PR-1 provenance/confidence.

    Degrades to INSUFFICIENT_DATA when observations are empty or below min_samples.
    Never raises for thin data — anomaly detection must not 500.
    """
    if not observations:
        zip_code = ""
        retailer = ""
        product_id = ""
    else:
        zip_code = observations[0].zip_code or ""
        retailer = observations[0].retailer
        product_id = observations[0].product_id
        if store_id is None:
            store_id = observations[0].store_id

    baseline = compute_local_baseline(observations)
    evidence_summary = build_evidence_summary(observations) if observations else [
        "No linked observations"
    ]
    confidence = aggregate_observation_confidence(observations, now=now) if observations else 0.0

    if baseline is None or baseline.sample_size < min_samples:
        return PriceAnomaly(
            product_id=product_id,
            zip_code=zip_code,
            retailer=retailer,
            store_id=store_id,
            current_price=current_price,
            observed_at=observed_at,
            observation_ids=observation_ids,
            baseline=baseline,
            deviation_pct=None,
            signal=RecommendationSignal.INSUFFICIENT_DATA,
            evidence_summary=evidence_summary,
            confidence=confidence,
        )

    deviation = compute_deviation_pct(current_price, baseline)
    signal = derive_recommendation_signal(
        deviation,
        baseline.sample_size,
        min_samples=min_samples,
    )

    return PriceAnomaly(
        product_id=product_id,
        zip_code=zip_code,
        retailer=retailer,
        store_id=store_id,
        current_price=current_price,
        observed_at=observed_at,
        observation_ids=observation_ids,
        baseline=baseline,
        deviation_pct=round(deviation, 1),
        signal=signal,
        evidence_summary=evidence_summary,
        confidence=confidence,
    )


def _latest_observation(observations: List[PriceObservation]) -> PriceObservation:
    return max(observations, key=lambda o: o.observed_at)


def build_market_price_anomaly(
    observations: List[PriceObservation],
    *,
    min_samples: int = _MIN_SAMPLES_DEFAULT,
    now: Optional[datetime] = None,
) -> PriceAnomaly:
    """Build anomaly for a market group using the latest observation as current price."""
    if not observations:
        reference = now or datetime.now()
        return build_price_anomaly(
            [],
            current_price=0.0,
            observed_at=reference,
            observation_ids=[],
            min_samples=min_samples,
            now=now,
        )

    latest = _latest_observation(observations)
    return build_price_anomaly(
        observations,
        current_price=latest.observed_price,
        observed_at=latest.observed_at,
        observation_ids=[o.id for o in observations],
        store_id=latest.store_id,
        min_samples=min_samples,
        now=now,
    )


def build_all_local_baselines(
    observations: List[PriceObservation],
) -> List[LocalPriceBaseline]:
    """Compute baselines for every market group in one indexed pass."""
    groups = group_observations_by_market(observations)
    baselines: List[LocalPriceBaseline] = []
    for group_observations in groups.values():
        baseline = compute_local_baseline(group_observations)
        if baseline is not None:
            baselines.append(baseline)
    return baselines


def build_all_price_anomalies(
    observations: List[PriceObservation],
    *,
    min_samples: int = _MIN_SAMPLES_DEFAULT,
    now: Optional[datetime] = None,
) -> List[PriceAnomaly]:
    """Compute anomalies for every market group."""
    groups = group_observations_by_market(observations)
    return [
        build_market_price_anomaly(
            group_observations,
            min_samples=min_samples,
            now=now,
        )
        for group_observations in groups.values()
    ]


def enrich_price_anomaly(
    anomaly: PriceAnomaly,
    product_name: Optional[str] = None,
    product_brand: Optional[str] = None,
) -> PriceAnomalyDetail:
    """Attach product display context for API responses."""
    return PriceAnomalyDetail(
        **anomaly.model_dump(),
        product_name=product_name,
        product_brand=product_brand,
    )
