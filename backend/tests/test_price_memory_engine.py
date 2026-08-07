"""Unit tests for local price memory engine (PR-2)."""

from datetime import datetime, timedelta, timezone

import pytest

from backend.deal_models import EvidenceType, PriceObservation
from backend.engines.price_memory_engine import (
    _GOOD_DEAL_THRESHOLD,
    _MIN_SAMPLES_DEFAULT,
    _NORMAL_BAND,
    _STRONG_DEAL_THRESHOLD,
    build_price_anomaly,
    compute_deviation_pct,
    compute_local_baseline,
    derive_recommendation_signal,
    group_observations_by_market,
)
from backend.price_memory_models import RecommendationSignal


def _obs(
    id: str,
    price: float,
    *,
    days_offset: int = 0,
    evidence: EvidenceType = EvidenceType.RETAILER_PUBLIC,
) -> PriceObservation:
    base = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
    when = base - timedelta(days=days_offset)
    return PriceObservation(
        id=id,
        product_id="prod-test",
        retailer="Target",
        zip_code="11566",
        observed_price=price,
        observed_at=when,
        evidence_type=evidence,
        confidence=0.8,
    )


class TestComputeLocalBaseline:
    def test_median_not_mean_outlier_robust(self):
        observations = [
            _obs("a", 10.0),
            _obs("b", 10.0),
            _obs("c", 10.0),
            _obs("d", 10.0),
            _obs("e", 100.0),
        ]
        baseline = compute_local_baseline(observations)
        assert baseline is not None
        assert baseline.median_price == 10.0
        assert baseline.sample_size == 5
        assert baseline.min_observed == 10.0
        assert baseline.max_observed == 100.0

    def test_empty_returns_none(self):
        assert compute_local_baseline([]) is None

    def test_all_time_no_decay_old_observation_counts(self):
        old = _obs("old", 20.0, days_offset=3)
        new = _obs("new", 10.0)
        baseline = compute_local_baseline([old, new])
        assert baseline is not None
        assert baseline.median_price == 15.0


class TestDeriveRecommendationSignal:
    def test_insufficient_data_below_min_samples(self):
        assert (
            derive_recommendation_signal(50.0, sample_size=2, min_samples=3)
            == RecommendationSignal.INSUFFICIENT_DATA
        )

    def test_strong_deal_at_threshold(self):
        assert (
            derive_recommendation_signal(_STRONG_DEAL_THRESHOLD, sample_size=5)
            == RecommendationSignal.STRONG_DEAL
        )

    def test_good_deal_boundaries(self):
        assert (
            derive_recommendation_signal(_GOOD_DEAL_THRESHOLD, sample_size=5)
            == RecommendationSignal.GOOD_DEAL
        )
        assert (
            derive_recommendation_signal(_GOOD_DEAL_THRESHOLD - 0.1, sample_size=5)
            == RecommendationSignal.NORMAL
        )

    def test_normal_band(self):
        assert derive_recommendation_signal(0.0, sample_size=5) == RecommendationSignal.NORMAL
        assert derive_recommendation_signal(10.0, sample_size=5) == RecommendationSignal.NORMAL

    def test_above_baseline(self):
        assert (
            derive_recommendation_signal(-_NORMAL_BAND, sample_size=5)
            == RecommendationSignal.ABOVE_BASELINE
        )


class TestBuildPriceAnomaly:
    def test_empty_observations_returns_insufficient_data_no_exception(self):
        when = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
        anomaly = build_price_anomaly(
            [],
            current_price=9.99,
            observed_at=when,
            observation_ids=[],
        )
        assert anomaly.signal == RecommendationSignal.INSUFFICIENT_DATA
        assert anomaly.baseline is None

    def test_two_samples_insufficient_data(self):
        observations = [_obs("a", 5.0), _obs("b", 6.0)]
        anomaly = build_price_anomaly(
            observations,
            current_price=4.0,
            observed_at=observations[-1].observed_at,
            observation_ids=[o.id for o in observations],
        )
        assert anomaly.signal == RecommendationSignal.INSUFFICIENT_DATA
        assert anomaly.deviation_pct is None

    def test_compute_deviation_pct(self):
        observations = [_obs("a", 10.0), _obs("b", 10.0), _obs("c", 10.0)]
        baseline = compute_local_baseline(observations)
        assert baseline is not None
        assert compute_deviation_pct(7.0, baseline) == 30.0


class TestGroupObservations:
    def test_single_pass_grouping(self):
        observations = [
            _obs("a", 10.0),
            PriceObservation(
                id="b",
                product_id="prod-other",
                retailer="Target",
                zip_code="11566",
                observed_price=5.0,
                observed_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
                evidence_type=EvidenceType.RETAILER_PUBLIC,
                confidence=0.8,
            ),
        ]
        groups = group_observations_by_market(observations)
        assert len(groups) == 2
        assert len(groups[("11566", "target", "prod-test")]) == 1

    def test_mixed_retailer_casing_groups_together(self):
        base = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
        observations = [
            PriceObservation(
                id="lower",
                product_id="prod-test",
                retailer="target",
                zip_code="11566",
                observed_price=10.0,
                observed_at=base,
                evidence_type=EvidenceType.RETAILER_PUBLIC,
                confidence=0.8,
            ),
            PriceObservation(
                id="title",
                product_id="prod-test",
                retailer="Target",
                zip_code="11566",
                observed_price=12.0,
                observed_at=base,
                evidence_type=EvidenceType.COMMUNITY_REPORT,
                confidence=0.6,
            ),
            PriceObservation(
                id="upper",
                product_id="prod-test",
                retailer="TARGET",
                zip_code="11566",
                observed_price=11.0,
                observed_at=base,
                evidence_type=EvidenceType.WEEKLY_AD,
                confidence=0.7,
            ),
        ]
        groups = group_observations_by_market(observations)
        assert len(groups) == 1
        assert len(groups[("11566", "target", "prod-test")]) == 3
        baseline = compute_local_baseline(groups[("11566", "target", "prod-test")])
        assert baseline is not None
        assert baseline.sample_size == 3
        assert baseline.median_price == 11.0
