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

from models import OptimizeRequest, OptimizeResponse, ShoppingItem
from engines import optimize_shopping_list
from providers import get_mock_store_items, get_mock_coupons, SUPPORTED_STORES


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
# Run with: uvicorn app:app --reload
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
