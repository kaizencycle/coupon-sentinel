"""Tests for deal intelligence model validation and serialization."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.deal_models import (
    DealEvent,
    DealType,
    EvidenceType,
    PriceObservation,
    derive_confidence_label,
    ConfidenceLabel,
)


class TestPriceObservationValidation:
    def test_rejects_confidence_above_one(self):
        with pytest.raises(ValidationError):
            PriceObservation(
                id="obs-bad",
                product_id="prod-1",
                retailer="Target",
                observed_price=5.0,
                observed_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
                evidence_type=EvidenceType.MANUAL,
                confidence=1.01,
            )

    def test_rejects_confidence_below_zero(self):
        with pytest.raises(ValidationError):
            PriceObservation(
                id="obs-bad",
                product_id="prod-1",
                retailer="Target",
                observed_price=5.0,
                observed_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
                evidence_type=EvidenceType.MANUAL,
                confidence=-0.1,
            )

    def test_rejects_negative_observed_price(self):
        with pytest.raises(ValidationError):
            PriceObservation(
                id="obs-bad",
                product_id="prod-1",
                retailer="Target",
                observed_price=-1.0,
                observed_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
                evidence_type=EvidenceType.MANUAL,
                confidence=0.5,
            )


class TestDealSerialization:
    def test_enum_and_datetime_serialization(self):
        observed = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
        deal = DealEvent(
            id="deal-test",
            product_id="prod-1",
            retailer="Target",
            deal_type=DealType.STACK,
            current_price=11.99,
            regular_price=14.99,
            effective_price=6.99,
            observed_at=observed,
            confidence=0.9,
        )
        data = deal.model_dump(mode="json")
        assert data["deal_type"] == "stack"
        assert data["observed_at"] in (
            "2026-08-07T12:00:00+00:00",
            "2026-08-07T12:00:00Z",
        )
        assert data["confidence"] == 0.9


class TestConfidenceLabel:
    def test_derive_labels(self):
        assert derive_confidence_label(0.98) == ConfidenceLabel.VERIFIED
        assert derive_confidence_label(0.80) == ConfidenceLabel.HIGH
        assert derive_confidence_label(0.60) == ConfidenceLabel.MEDIUM
        assert derive_confidence_label(0.30) == ConfidenceLabel.LOW
