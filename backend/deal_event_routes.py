"""
Coupon Sentinel - Deal Events Routes (Milestone 3)

Real, DB-backed deal events inferred from persisted price_observations
(populated so far by the Kroger client — backend/kroger_routes.py). Separate
namespace from the existing /api/deals (PR-1/2/3's mock-fixture evidence
layer) to avoid conflating the two: this is Milestone 3's literal
deliverable, operating on the Milestone 1 DB schema, not mock data.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.db_models import DealEventRecord, PriceObservationRecord
from backend.engines.deal_inference_engine import infer_deals, persist_deals
from backend.providers.mock_data import get_mock_coupons

router = APIRouter(prefix="/api/deal-events", tags=["deal-events"])


def _serialize(record: DealEventRecord) -> dict:
    return {
        "id": record.id,
        "product_id": record.product_id,
        "store_id": record.store_id,
        "deal_type": record.deal_type,
        "effective_price": float(record.effective_price),
        "savings_amount": float(record.savings_amount),
        "evidence_ids": record.evidence_ids,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.post("/infer")
def infer_deal_events(
    product_id: Optional[str] = Query(None, description="Limit inference to one product"),
    store_id: Optional[str] = Query(None, description="Limit inference to one store"),
    db: Session = Depends(get_db),
):
    """
    Run deal inference over currently persisted price_observations and
    materialize the results as deal_events rows.

    Coupons come from the existing mock coupon catalog (backend/providers/mock_data.py)
    — the same one the optimizer uses. A real coupon provider is Phase 2 scope.
    """
    query = db.query(PriceObservationRecord)
    if product_id:
        query = query.filter(PriceObservationRecord.product_id == product_id)
    if store_id:
        query = query.filter(PriceObservationRecord.store_id == store_id)
    observations = query.all()

    deals = infer_deals(observations, get_mock_coupons())
    records = persist_deals(deals, db)

    return {
        "deals": [_serialize(r) for r in records],
        "count": len(records),
        "observations_considered": len(observations),
    }


@router.get("")
def list_deal_events(
    product_id: Optional[str] = Query(None),
    store_id: Optional[str] = Query(None),
    deal_type: Optional[str] = Query(None, description="'price_drop' or 'coupon'"),
    db: Session = Depends(get_db),
):
    """List persisted deal_events, most recent first."""
    query = db.query(DealEventRecord)
    if product_id:
        query = query.filter(DealEventRecord.product_id == product_id)
    if store_id:
        query = query.filter(DealEventRecord.store_id == store_id)
    if deal_type:
        query = query.filter(DealEventRecord.deal_type == deal_type)

    records = query.order_by(DealEventRecord.created_at.desc()).all()

    return {"deals": [_serialize(r) for r in records], "count": len(records)}
