"""
Coupon Sentinel - FastAPI Backend

Main API application with endpoints for:
- Shopping list optimization
- Store/coupon/item listings
- Health checks
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from .models import (
    OptimizeRequest,
    OptimizeResponse,
    OptimizeWithDealContextResponse,
    OptimizedItemWithDealContext,
    ShoppingItem,
    StorePlanWithDealContext,
)
from .engines import optimize_shopping_list
from .engines.deal_context_engine import attach_deal_context, build_market_observation_index
from .engines.deal_engine import enrich_deal_event, enrich_price_observation
from .engines.price_memory_engine import (
    build_price_anomaly,
    compute_local_baseline,
    enrich_price_anomaly,
    group_observations_by_market,
)
from .providers import (
    get_mock_store_items,
    get_mock_coupons,
    SUPPORTED_STORES,
    get_mock_deal_events,
    get_mock_price_observations,
    get_product_index,
    MOCK_DATA_NOTICE,
)


# ============================================================================
# App Setup
# ============================================================================

app = FastAPI(
    title="Coupon Sentinel API",
    description="Extreme couponing, automated. Find the cheapest way to fulfill your shopping list.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "mock_data",
        "features": {
            "multi_store": True,
            "coupon_stacking": True,
            "rebate_tracking": True
        }
    }


# ============================================================================
# Main Optimization Endpoint
# ============================================================================

@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize(request: OptimizeRequest):
    """
    Optimize a shopping list for maximum savings.
    
    Takes a list of items and returns the cheapest way to buy them,
    including coupon stacking and store recommendations.
    """
    if not request.shopping_list:
        raise HTTPException(status_code=400, detail="Shopping list cannot be empty")
    
    # Load data (in production, this would come from real sources)
    store_items = get_mock_store_items()
    coupons = get_mock_coupons()
    
    # Run optimization
    result = optimize_shopping_list(request, store_items, coupons)
    
    return result


@app.post("/api/optimize/with-deal-context", response_model=OptimizeWithDealContextResponse)
async def optimize_with_deal_context(request: OptimizeRequest):
    """
    Optimize a shopping list and attach optional local deal context per item.

    Separate from POST /api/optimize — existing optimize response shape is unchanged.
    deal_context is null when no product_id bridge or no matching market anomaly.
    """
    if not request.shopping_list:
        raise HTTPException(status_code=400, detail="Shopping list cannot be empty")

    store_items = get_mock_store_items()
    coupons = get_mock_coupons()
    result = optimize_shopping_list(request, store_items, coupons)

    # Single pass: index observations by market once per request (not per item).
    market_observations = build_market_observation_index(get_mock_price_observations())

    plans_with_context: List[StorePlanWithDealContext] = []
    for plan in result.plans:
        items_with_context: List[OptimizedItemWithDealContext] = []
        for item in plan.items:
            deal_context = attach_deal_context(
                item,
                market_observations,
                zip_code=request.zip_code,
            )
            items_with_context.append(
                OptimizedItemWithDealContext(
                    **item.model_dump(),
                    deal_context=deal_context,
                )
            )
        plans_with_context.append(
            StorePlanWithDealContext(
                store_name=plan.store_name,
                items=items_with_context,
                subtotal=plan.subtotal,
                store_level_discounts=plan.store_level_discounts,
                final_total=plan.final_total,
                estimated_savings=plan.estimated_savings,
            )
        )

    return OptimizeWithDealContextResponse(
        plans=plans_with_context,
        grand_total=result.grand_total,
        total_base_cost=result.total_base_cost,
        total_savings=result.total_savings,
        savings_percentage=result.savings_percentage,
        unfulfilled_items=result.unfulfilled_items,
        action_steps=result.action_steps,
        rebate_opportunities=result.rebate_opportunities,
        is_mock_data=True,
        notice=MOCK_DATA_NOTICE,
    )


# ============================================================================
# Data Listing Endpoints
# ============================================================================

@app.get("/api/stores")
async def list_stores():
    """List all supported stores."""
    return {
        "stores": SUPPORTED_STORES,
        "count": len(SUPPORTED_STORES)
    }


@app.get("/api/items")
async def list_items(
    store: Optional[str] = Query(None, description="Filter by store name"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """List available items, optionally filtered by store or category."""
    items = get_mock_store_items()
    
    if store:
        items = [i for i in items if i.store_name.lower() == store.lower()]
    
    if category:
        items = [i for i in items if i.category.lower() == category.lower()]
    
    return {
        "items": [
            {
                "store": i.store_name,
                "name": i.item_name,
                "brand": i.brand,
                "price": i.price,
                "size": f"{i.package_size} {i.package_unit}",
                "unit_price": round(i.unit_price, 2),
                "category": i.category
            }
            for i in items
        ],
        "count": len(items)
    }


@app.get("/api/coupons")
async def list_coupons(
    store: Optional[str] = Query(None, description="Filter by store"),
    coupon_type: Optional[str] = Query(None, description="Filter by type: manufacturer, store, rebate")
):
    """List available coupons, optionally filtered."""
    coupons = get_mock_coupons()
    
    if store:
        coupons = [c for c in coupons if c.store_scope is None or 
                   c.store_scope.lower() in ["any", store.lower()]]
    
    if coupon_type:
        coupons = [c for c in coupons if c.coupon_type.value == coupon_type.lower()]
    
    return {
        "coupons": [
            {
                "id": c.id,
                "type": c.coupon_type.value,
                "store": c.store_scope or "any",
                "description": c.description,
                "value": c.value,
                "item_filter": c.item_filter,
                "source": c.source
            }
            for c in coupons
        ],
        "count": len(coupons)
    }


@app.get("/api/categories")
async def list_categories():
    """List all product categories."""
    items = get_mock_store_items()
    categories = sorted(set(i.category for i in items))
    
    return {
        "categories": categories,
        "count": len(categories)
    }


# ============================================================================
# Deal Intelligence Endpoints (PR-1 — read-only, mock fixtures)
# ============================================================================

@app.get("/api/deals")
async def list_deals(
    zip_code: Optional[str] = Query(None, description="Filter by zip code"),
    retailer: Optional[str] = Query(None, description="Filter by retailer"),
    deal_type: Optional[str] = Query(None, description="Filter by deal type"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
):
    """
    List canonical deal events derived from mock observations.

    All data is synthetic fixture data — not live retailer pricing.
  """
    products = get_product_index()
    observations = {o.id: o for o in get_mock_price_observations()}
    deals = get_mock_deal_events()

    if zip_code:
        deals = [d for d in deals if d.zip_code == zip_code]
    if retailer:
        deals = [d for d in deals if d.retailer.lower() == retailer.lower()]
    if deal_type:
        deals = [d for d in deals if d.deal_type.value == deal_type.lower()]
    if product_id:
        deals = [d for d in deals if d.product_id == product_id]

    enriched = []
    for deal in deals:
        product = products.get(deal.product_id)
        if not product:
            continue
        linked_obs = [observations[i] for i in deal.observation_ids if i in observations]
        enriched.append(
            enrich_deal_event(deal, product, linked_obs).model_dump(mode="json")
        )

    return {
        "deals": enriched,
        "count": len(enriched),
        "is_mock_data": True,
        "notice": MOCK_DATA_NOTICE,
    }


@app.get("/api/deals/{deal_id}")
async def get_deal(deal_id: str):
    """Get a single deal event with provenance summary."""
    products = get_product_index()
    observations = {o.id: o for o in get_mock_price_observations()}

    for deal in get_mock_deal_events():
        if deal.id == deal_id:
            product = products.get(deal.product_id)
            if not product:
                raise HTTPException(status_code=404, detail="Product not found for deal")
            linked_obs = [observations[i] for i in deal.observation_ids if i in observations]
            detail = enrich_deal_event(deal, product, linked_obs)
            return {
                "deal": detail.model_dump(mode="json"),
                "is_mock_data": True,
                "notice": MOCK_DATA_NOTICE,
            }

    raise HTTPException(status_code=404, detail=f"Deal not found: {deal_id}")


@app.get("/api/price-observations")
async def list_price_observations(
    zip_code: Optional[str] = Query(None, description="Filter by zip code"),
    retailer: Optional[str] = Query(None, description="Filter by retailer"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    evidence_type: Optional[str] = Query(None, description="Filter by evidence type"),
):
    """
    List normalized price observations (evidence layer).

    Observations are not deals or recommendations — they are raw evidenced prices.
    """
    products = get_product_index()
    observations = get_mock_price_observations()

    if zip_code:
        observations = [o for o in observations if o.zip_code == zip_code]
    if retailer:
        observations = [o for o in observations if o.retailer.lower() == retailer.lower()]
    if product_id:
        observations = [o for o in observations if o.product_id == product_id]
    if evidence_type:
        observations = [
            o for o in observations if o.evidence_type.value == evidence_type.lower()
        ]

    enriched = [
        enrich_price_observation(o, products.get(o.product_id)).model_dump(mode="json")
        for o in observations
    ]

    return {
        "observations": enriched,
        "count": len(enriched),
        "is_mock_data": True,
        "notice": MOCK_DATA_NOTICE,
    }


# ============================================================================
# Local Price Memory Endpoints (PR-2 — read-only, mock fixtures)
#
# Additive read-only routes using engines/price_memory_engine.py.
# Same is_mock_data / MOCK_DATA_NOTICE contract as PR-1 deal endpoints.
# Filter observations only for single-product lookup; list_anomalies computes
# every market group first then filters (same pattern as list_deals).
# ============================================================================


def _price_memory_group_key(zip_code: str, retailer: str, product_id: str) -> tuple:
    """GroupKey aligned with engine retailer normalization."""
    return (zip_code, retailer.lower(), product_id)


@app.get("/api/price-memory/{product_id}")
async def get_price_memory(
    product_id: str,
    zip_code: str = Query(..., description="ZIP code for the local market"),
    retailer: str = Query(..., description="Retailer name"),
):
    """
    Return the local price baseline for one product at one retailer/ZIP.

    Groups matching observations via group_observations_by_market, then computes
    the all-time median baseline for that single group. 404 if no observations
    exist — an empty baseline is not a valid response.
    """
    observations = get_mock_price_observations()
    grouped = group_observations_by_market(observations)
    group_key = _price_memory_group_key(zip_code, retailer, product_id)

    group_observations = grouped.get(group_key, [])
    if not group_observations:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No price observations for product={product_id} "
                f"retailer={retailer} zip_code={zip_code}"
            ),
        )

    baseline = compute_local_baseline(group_key, group_observations)

    return {
        "baseline": baseline.model_dump(mode="json"),
        "is_mock_data": True,
        "notice": MOCK_DATA_NOTICE,
    }


@app.get("/api/anomalies")
async def list_anomalies(
    zip_code: Optional[str] = Query(None, description="Filter by zip code"),
    retailer: Optional[str] = Query(None, description="Filter by retailer"),
    signal: Optional[str] = Query(
        None,
        description=(
            "Filter by signal: strong_deal, good_deal, normal, "
            "above_baseline, insufficient_data"
        ),
    ),
):
    """
    List price anomalies across all local markets in the mock fixture set.

    Computes one PriceAnomaly per (zip_code, retailer, product_id) group first,
    then filters — do not pre-filter observations before grouping (that would
    shrink sample sizes and skew MIN_BASELINE_SAMPLES gating).
    """
    products = get_product_index()
    observations = get_mock_price_observations()
    grouped = group_observations_by_market(observations)

    anomalies = []
    for group_key, group_observations in grouped.items():
        gz, gr, gp = group_key
        current_price = max(o.observed_price for o in group_observations)
        anomalies.append(
            build_price_anomaly(
                anomaly_id=f"anomaly-{gr}-{gz or 'no-zip'}-{gp}",
                group_key=group_key,
                current_price=current_price,
                observations=group_observations,
            )
        )

    if zip_code:
        anomalies = [a for a in anomalies if (a.zip_code or "") == zip_code]
    if retailer:
        anomalies = [a for a in anomalies if a.retailer.lower() == retailer.lower()]
    if signal:
        anomalies = [a for a in anomalies if a.signal.value == signal.lower()]

    enriched = []
    for anomaly in anomalies:
        product = products.get(anomaly.product_id)
        enriched.append(
            enrich_price_anomaly(
                anomaly,
                product_name=product.name if product else None,
                product_brand=product.brand if product else None,
            ).model_dump(mode="json")
        )

    return {
        "anomalies": enriched,
        "count": len(enriched),
        "is_mock_data": True,
        "notice": MOCK_DATA_NOTICE,
    }


# ============================================================================
# Quick Optimize (Simplified Endpoint)
# ============================================================================

@app.post("/api/quick-optimize")
async def quick_optimize(
    items: List[str] = Query(..., description="List of item names"),
    stores: List[str] = Query(default=[], description="Preferred stores"),
    multi_store: bool = Query(False, description="Allow shopping at multiple stores")
):
    """
    Quick optimization endpoint that takes simple item names.
    
    Example: /api/quick-optimize?items=milk&items=eggs&stores=Target&stores=Walmart
    """
    shopping_list = [
        ShoppingItem(name=item, quantity=1, unit="count", flexible=True)
        for item in items
    ]
    
    request = OptimizeRequest(
        shopping_list=shopping_list,
        zip_code="00000",
        preferred_stores=stores if stores else SUPPORTED_STORES,
        allow_multi_store=multi_store,
        rebate_apps=[]
    )
    
    store_items = get_mock_store_items()
    coupons = get_mock_coupons()
    
    result = optimize_shopping_list(request, store_items, coupons)
    
    # Return simplified response
    return {
        "grand_total": result.grand_total,
        "total_savings": result.total_savings,
        "savings_percentage": result.savings_percentage,
        "stores_to_visit": [p.store_name for p in result.plans],
        "action_steps": result.action_steps
    }


# ============================================================================
# Run from repo root with: uvicorn backend.app:app --reload
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
