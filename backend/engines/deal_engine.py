"""
Coupon Sentinel — Deal Engine (PR-1)

Deterministic effective-price calculations and conservative evidence aggregation.
No LLM scoring, no travel cost, no BUY/WAIT logic — those belong in later PRs.
"""

from datetime import datetime
from typing import List, Optional, Set

from backend.deal_models import (
    ConfidenceLabel,
    DealEvent,
    DealEventDetail,
    DealType,
    EvidenceType,
    PriceObservation,
    PriceObservationDetail,
    ProductIdentity,
    derive_confidence_label,
)

# Evidence weights for conservative confidence aggregation (not independence modeling).
_EVIDENCE_WEIGHTS: dict[EvidenceType, float] = {
    EvidenceType.RECEIPT: 0.95,
    EvidenceType.RETAILER_PUBLIC: 0.85,
    EvidenceType.WEEKLY_AD: 0.80,
    EvidenceType.COUPON_FEED: 0.70,
    EvidenceType.REBATE_FEED: 0.70,
    EvidenceType.COMMUNITY_REPORT: 0.45,
    EvidenceType.MANUAL: 0.60,
}

# Future requirement: distinguish N copies of one source from N independent observations.
# PR-1 uses source-type diversity as a weak heuristic only — not true evidentiary independence.
INDEPENDENCE_MODELING_FUTURE_REQUIREMENT = (
    "Future systems must track source identity and independence chains so that "
    "10 copies of one source cannot inflate confidence like 10 independent observations."
)


def calculate_effective_price(
    current_price: float,
    coupon_value: float = 0.0,
    loyalty_savings: float = 0.0,
    rebate_value: float = 0.0,
) -> float:
    """
    effective price = current transaction price - coupon - loyalty - rebate
    Clamped to zero — excess discounts must not produce invalid consumer totals.
    """
    total_discounts = coupon_value + loyalty_savings + rebate_value
    return max(0.0, current_price - total_discounts)


def calculate_savings_amount(
    regular_price: float,
    effective_price: float,
) -> float:
    """Absolute savings vs regular/list price. Never negative."""
    return max(0.0, regular_price - effective_price)


def calculate_savings_percentage(
    regular_price: float,
    effective_price: float,
) -> float:
    """Percentage savings vs regular price, rounded to one decimal."""
    if regular_price <= 0:
        return 0.0
    pct = (regular_price - effective_price) / regular_price * 100
    return round(max(0.0, pct), 1)


def aggregate_observation_confidence(
    observations: List[PriceObservation],
    *,
    now: Optional[datetime] = None,
) -> float:
    """
    Conservative confidence from independent observations.

    Behavior (PR-1):
    - Single weak community report → low confidence
    - Multiple recent observations with diverse evidence types → higher confidence
    - Receipt-backed observation → strong evidence floor
    - Stale evidence → reduced confidence

    Does NOT claim true evidentiary independence — see INDEPENDENCE_MODELING_FUTURE_REQUIREMENT.
    """
    if not observations:
        return 0.0

    reference = now or datetime.now(observations[0].observed_at.tzinfo)
    weighted_sum = 0.0
    weight_total = 0.0
    evidence_types: Set[EvidenceType] = set()
    has_receipt = False

    for obs in observations:
        age_days = max(0.0, (reference - obs.observed_at).total_seconds() / 86400.0)
        staleness = 1.0 if age_days <= 7 else 0.85 if age_days <= 30 else 0.65 if age_days <= 90 else 0.4

        type_weight = _EVIDENCE_WEIGHTS.get(obs.evidence_type, 0.5)
        combined = obs.confidence * type_weight * staleness

        weighted_sum += combined
        weight_total += type_weight
        evidence_types.add(obs.evidence_type)
        if obs.evidence_type == EvidenceType.RECEIPT:
            has_receipt = True

    base = weighted_sum / weight_total if weight_total > 0 else 0.0

    # Small boost for evidence-type diversity (not independence)
    diversity_boost = min(0.08, max(0.0, (len(evidence_types) - 1) * 0.04))
    receipt_floor = 0.90 if has_receipt else 0.0

    return min(1.0, max(base + diversity_boost, receipt_floor))


def build_evidence_summary(observations: List[PriceObservation]) -> List[str]:
    """Human-readable provenance lines for consumer display."""
    if not observations:
        return ["No linked observations"]

    summaries: List[str] = []
    count = len(observations)
    summaries.append(f"{count} observation{'s' if count != 1 else ''}")

    evidence_types = {obs.evidence_type for obs in observations}
    if EvidenceType.RECEIPT in evidence_types:
        summaries.append("Receipt verified")
    if EvidenceType.RETAILER_PUBLIC in evidence_types:
        summaries.append("Retailer listing")
    if EvidenceType.WEEKLY_AD in evidence_types:
        summaries.append("Weekly ad")
    if EvidenceType.COUPON_FEED in evidence_types:
        summaries.append("Coupon feed")
    if EvidenceType.REBATE_FEED in evidence_types:
        summaries.append("Rebate feed")
    if EvidenceType.COMMUNITY_REPORT in evidence_types:
        summaries.append("Community report")

    return summaries


def enrich_deal_event(
    deal: DealEvent,
    product: ProductIdentity,
    observations: List[PriceObservation],
) -> DealEventDetail:
    """Attach provenance and display metadata without altering canonical deal fields."""
    linked = [o for o in observations if o.id in deal.observation_ids]
    evidence_types = sorted(
        {o.evidence_type for o in linked},
        key=lambda e: e.value,
    )
    receipt_verified = any(o.evidence_type == EvidenceType.RECEIPT for o in linked)

    return DealEventDetail(
        **deal.model_dump(),
        product_name=product.name,
        product_brand=product.brand,
        confidence_label=derive_confidence_label(deal.confidence),
        evidence_types=evidence_types,
        evidence_summary=build_evidence_summary(linked),
        observation_count=len(linked),
        receipt_verified=receipt_verified,
        is_mock_data=True,
    )


def enrich_price_observation(
    observation: PriceObservation,
    product: Optional[ProductIdentity] = None,
) -> PriceObservationDetail:
    return PriceObservationDetail(
        **observation.model_dump(),
        product_name=product.name if product else None,
        confidence_label=derive_confidence_label(observation.confidence),
        is_mock_data=True,
    )


def build_deal_from_observations(
    deal_id: str,
    product_id: str,
    retailer: str,
    deal_type: DealType,
    observations: List[PriceObservation],
    *,
    current_price: float,
    regular_price: Optional[float] = None,
    coupon_value: float = 0.0,
    rebate_value: float = 0.0,
    loyalty_savings: float = 0.0,
    store_id: Optional[str] = None,
    zip_code: Optional[str] = None,
    starts_at: Optional[datetime] = None,
    expires_at: Optional[datetime] = None,
    inventory_confirmed: bool = False,
) -> DealEvent:
    """Build a DealEvent from observations with deterministic pricing."""
    effective = calculate_effective_price(
        current_price,
        coupon_value=coupon_value,
        loyalty_savings=loyalty_savings,
        rebate_value=rebate_value,
    )
    reg = regular_price if regular_price is not None else current_price
    savings_amt = calculate_savings_amount(reg, effective)
    savings_pct = calculate_savings_percentage(reg, effective)
    confidence = aggregate_observation_confidence(observations)
    latest_observed = max(obs.observed_at for obs in observations)

    return DealEvent(
        id=deal_id,
        product_id=product_id,
        retailer=retailer,
        store_id=store_id,
        zip_code=zip_code,
        deal_type=deal_type,
        regular_price=regular_price,
        current_price=current_price,
        coupon_value=coupon_value,
        rebate_value=rebate_value,
        loyalty_savings=loyalty_savings,
        effective_price=effective,
        savings_amount=savings_amt,
        savings_percentage=savings_pct,
        starts_at=starts_at,
        expires_at=expires_at,
        observed_at=latest_observed,
        observation_ids=[o.id for o in observations],
        confidence=confidence,
        inventory_confirmed=inventory_confirmed,
    )
