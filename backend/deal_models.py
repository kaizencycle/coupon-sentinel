"""
Coupon Sentinel — Consumer Deal Intelligence Models (PR-1)

Canonical data model for evidence-backed price intelligence.

Architecture principle (never collapse these layers):
  Evidence → PriceObservation → DealEvent → Consumer recommendation

Consumer protection guardrails:
  1. Public or user-contributed information only.
  2. No unauthorized access to retailer systems.
  3. No bypassing login/access controls.
  4. No claims of inventory without evidence.
  5. No claiming personalized pricing from one observation.
  6. Price anomalies are observations, not accusations.
  7. No ranking by affiliate commission.
  8. Consumer privacy takes priority over behavioral monetization.
  9. Receipt data should be minimized after extracting relevant market facts.
  10. Every displayed deal should be traceable to its provenance.

A receipt is evidence of a transaction, not permission to create a behavioral profile.
Persist only information necessary for consumer-price intelligence.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class EvidenceType(str, Enum):
    """Source type for a price observation. Extensible via string enum values."""

    RETAILER_PUBLIC = "retailer_public"
    RECEIPT = "receipt"
    WEEKLY_AD = "weekly_ad"
    COUPON_FEED = "coupon_feed"
    REBATE_FEED = "rebate_feed"
    COMMUNITY_REPORT = "community_report"
    MANUAL = "manual"


class ConfidenceLabel(str, Enum):
    """Derived display classification for numeric confidence. Never replaces evidence."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERIFIED = "VERIFIED"


class DealType(str, Enum):
    """Interpretation of one or more observations into a consumer-relevant opportunity."""

    SALE = "sale"
    CLEARANCE = "clearance"
    COUPON = "coupon"
    REBATE = "rebate"
    STACK = "stack"
    DISCONTINUED = "discontinued"
    SEASONAL = "seasonal"
    MARKDOWN = "markdown"
    PENNY_OR_PULL = "penny_or_pull"
    PRICE_ANOMALY = "price_anomaly"
    UNKNOWN = "unknown"


class ProductIdentity(BaseModel):
    """Product independent of any single retailer."""

    id: str
    name: str
    brand: Optional[str] = None
    upc: Optional[str] = None
    category: Optional[str] = None
    package_size: Optional[float] = None
    package_unit: Optional[str] = None


class RetailLocation(BaseModel):
    """Merchant/location context. Coarse location only — no street addresses required."""

    retailer: str
    store_id: Optional[str] = None
    zip_code: Optional[str] = None
    region: Optional[str] = None


class PriceObservation(BaseModel):
    """
    At this place and time, this evidence indicated this product had this price.

    A price observation does NOT automatically mean confirmed inventory, nationwide
    price, permanent price, or recommended purchase — those are interpretations.
    """

    id: str
    product_id: str
    upc: Optional[str] = None
    retailer: str
    store_id: Optional[str] = None
    zip_code: Optional[str] = None
    observed_price: float
    regular_price: Optional[float] = None
    loyalty_price: Optional[float] = None
    observed_at: datetime
    evidence_type: EvidenceType
    source: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    in_stock: Optional[bool] = None
    documented_coupon_value: Optional[float] = Field(
        None,
        ge=0.0,
        description="Coupon discount amount evidenced by this observation (e.g. coupon feed)",
    )
    documented_rebate_value: Optional[float] = Field(
        None,
        ge=0.0,
        description="Rebate value evidenced by this observation (e.g. rebate feed)",
    )
    documented_loyalty_savings: Optional[float] = Field(
        None,
        ge=0.0,
        description="Loyalty savings amount evidenced by this observation",
    )

    @field_validator("observed_price")
    @classmethod
    def observed_price_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("observed_price must be non-negative")
        return value


class DealEvent(BaseModel):
    """
    Interprets one or more observations into a consumer-relevant opportunity.

    Deal confidence is separate from inventory confidence — inventory_confirmed
    must only be True when evidenced, never inferred from deal type alone.
    """

    id: str
    product_id: str
    retailer: str
    store_id: Optional[str] = None
    zip_code: Optional[str] = None
    deal_type: DealType
    regular_price: Optional[float] = None
    current_price: float
    coupon_value: float = 0
    rebate_value: float = 0
    loyalty_savings: float = 0
    effective_price: float
    savings_amount: Optional[float] = None
    savings_percentage: Optional[float] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    observed_at: datetime
    observation_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    inventory_confirmed: bool = False


class DealEventDetail(DealEvent):
    """API-enriched deal with provenance summary for consumer display."""

    product_name: str
    product_brand: Optional[str] = None
    confidence_label: ConfidenceLabel
    evidence_types: List[EvidenceType] = Field(default_factory=list)
    evidence_summary: List[str] = Field(default_factory=list)
    observation_count: int = 0
    receipt_verified: bool = False
    is_mock_data: bool = True


class PriceObservationDetail(PriceObservation):
    """API-enriched observation with product context."""

    product_name: Optional[str] = None
    confidence_label: ConfidenceLabel
    is_mock_data: bool = True


def derive_confidence_label(confidence: float) -> ConfidenceLabel:
    """Map numeric confidence to a display label without replacing underlying evidence."""
    if confidence >= 0.95:
        return ConfidenceLabel.VERIFIED
    if confidence >= 0.75:
        return ConfidenceLabel.HIGH
    if confidence >= 0.5:
        return ConfidenceLabel.MEDIUM
    return ConfidenceLabel.LOW
