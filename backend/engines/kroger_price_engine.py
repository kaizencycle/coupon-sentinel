"""
Coupon Sentinel - Kroger Price Observation Recording (Milestone 2)

Persists KrogerProduct lookups as PriceObservationRecord rows — the evidence
layer's durable storage (see backend/db_models.py). Kept as its own module
rather than folded into providers/kroger.py so the HTTP client stays free of
DB/session concerns.
"""

from typing import Optional

from sqlalchemy.orm import Session

from backend.db_models import PriceObservationRecord
from backend.providers.kroger import KrogerProduct

# Kroger's own live API is treated as a high-confidence source — it's the
# retailer's own listed price, not a scrape or community report.
KROGER_API_CONFIDENCE = 0.95


def record_price_observations(
    products: list[KrogerProduct], store_id: str, db: Session
) -> list[PriceObservationRecord]:
    """Persist one PriceObservationRecord per product that has a known price."""
    records: list[PriceObservationRecord] = []

    for product in products:
        if product.price is None:
            continue

        record = PriceObservationRecord(
            product_id=product.product_id,
            store_id=store_id,
            price=product.price,
            unit_price=None,
            package_size=product.size,
            source="kroger_api",
            confidence=KROGER_API_CONFIDENCE,
        )
        db.add(record)
        records.append(record)

    if records:
        db.commit()
        for record in records:
            db.refresh(record)

    return records


def record_price_observation(product: KrogerProduct, store_id: str, db: Session) -> Optional[PriceObservationRecord]:
    """Persist a single product lookup; convenience wrapper around record_price_observations."""
    records = record_price_observations([product], store_id, db)
    return records[0] if records else None
