"""
Coupon Sentinel - Kroger API Routes (Milestone 2)

Read endpoints backed by the real Kroger Product API (backend/providers/kroger.py).
Separate from the mock-data optimizer's /api/items and /api/stores — these
hit a live third-party API and persist what they find as evidence-layer
price observations.

Returns 503 (not a fake empty result) when KROGER_CLIENT_ID/SECRET are unset,
same pattern as the Stripe billing routes.
"""

from dataclasses import asdict
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.engines.kroger_price_engine import record_price_observations
from backend.providers.kroger import KrogerClient, KrogerNotConfiguredError, KrogerRateLimitError

router = APIRouter(prefix="/api/kroger", tags=["kroger"])

_kroger_client: Optional[KrogerClient] = None


def get_kroger_client() -> KrogerClient:
    """Process-wide singleton so the OAuth token is cached across requests."""
    global _kroger_client
    if _kroger_client is None:
        _kroger_client = KrogerClient()
    return _kroger_client


def _call_kroger(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KrogerNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except KrogerRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Kroger API error: {exc.response.status_code}",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Kroger API unreachable: {exc}")


@router.get("/search")
async def search_kroger_products(
    query: str = Query(..., min_length=1, description="Search term, e.g. 'milk'"),
    location_id: Optional[str] = Query(None, description="Kroger store location id"),
    limit: int = Query(10, ge=1, le=50),
    client: KrogerClient = Depends(get_kroger_client),
    db: Session = Depends(get_db),
):
    products = _call_kroger(client.search_products, query, location_id=location_id, limit=limit)
    record_price_observations(products, store_id="kroger", db=db)

    return {
        "products": [asdict(p) for p in products],
        "count": len(products),
        "source": "kroger_api",
    }


@router.get("/products/{product_id}")
async def get_kroger_product(
    product_id: str,
    location_id: Optional[str] = Query(None, description="Kroger store location id"),
    client: KrogerClient = Depends(get_kroger_client),
    db: Session = Depends(get_db),
):
    product = _call_kroger(client.get_product, product_id, location_id=location_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product not found: {product_id}")

    record_price_observations([product], store_id="kroger", db=db)

    return {"product": asdict(product), "source": "kroger_api"}
