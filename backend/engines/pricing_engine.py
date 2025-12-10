"""
Coupon Sentinel - Pricing Engine

Core optimization logic:
1. Match requested items to store products
2. Apply coupon stacking rules
3. Choose optimal store(s)
4. Generate shopping plan
"""

from typing import List, Dict, Tuple, Optional
import math
from models import (
    ShoppingItem, StoreItem, Coupon, OptimizeRequest, OptimizeResponse,
    OptimizedItem, StorePlan, AppliedCoupon, RebateOpportunity
)
from engines.stacking_logic import calculate_best_coupon_stack, find_rebate_opportunities


def match_items(
    requested: ShoppingItem,
    available: List[StoreItem]
) -> List[StoreItem]:
    """Find store items that match a requested item."""
    matches = []
    search_term = requested.name.lower()
    
    for item in available:
        # Match by name
        if search_term in item.item_name.lower():
            matches.append(item)
            continue
        
        # Match by category
        if search_term in item.category.lower():
            matches.append(item)
            continue
        
        # Match by brand if specified
        if requested.brand_preference and item.brand:
            if requested.brand_preference.lower() in item.brand.lower():
                matches.append(item)
    
    return matches


def calculate_packages_needed(requested: ShoppingItem, product: StoreItem) -> int:
    """Calculate how many packages to buy to fulfill request."""
    if requested.unit == product.package_unit:
        return math.ceil(requested.quantity / product.package_size)
    
    # Simple unit conversions
    conversion = {
        ("count", "count"): 1,
        ("gallon", "gallon"): 1,
        ("lb", "lb"): 1,
        ("oz", "oz"): 1,
        ("oz", "lb"): 16,  # 16 oz = 1 lb
        ("lb", "oz"): 1/16,
    }
    
    key = (requested.unit, product.package_unit)
    if key in conversion:
        needed = requested.quantity * conversion[key]
        return math.ceil(needed / product.package_size)
    
    # Default: assume 1 package
    return max(1, int(requested.quantity))


def optimize_single_store(
    request: OptimizeRequest,
    store_items: List[StoreItem],
    coupons: List[Coupon],
    store_name: str
) -> Optional[StorePlan]:
    """Optimize shopping for a single store."""
    
    # Filter items for this store
    items_at_store = [i for i in store_items if i.store_name == store_name]
    if not items_at_store:
        return None
    
    optimized_items: List[OptimizedItem] = []
    total_base = 0.0
    total_final = 0.0
    total_savings = 0.0
    
    for requested in request.shopping_list:
        # Find matching products at this store
        matches = match_items(requested, items_at_store)
        
        if not matches:
            continue
        
        # Evaluate each match
        best_choice = None
        best_final_cost = float('inf')
        best_coupons = []
        
        for product in matches:
            qty_needed = calculate_packages_needed(requested, product)
            base_cost = product.price * qty_needed
            
            # Calculate coupon savings
            applied_coupons, discount = calculate_best_coupon_stack(
                product, qty_needed, coupons
            )
            
            final_cost = base_cost - discount
            
            if final_cost < best_final_cost:
                best_choice = product
                best_final_cost = final_cost
                best_coupons = applied_coupons
                best_qty = qty_needed
                best_base = base_cost
        
        if best_choice:
            savings = best_base - best_final_cost
            optimized_items.append(OptimizedItem(
                requested_item=requested,
                chosen_product=best_choice,
                quantity_to_buy=best_qty,
                base_cost=round(best_base, 2),
                applied_coupons=best_coupons,
                final_cost=round(best_final_cost, 2),
                savings=round(savings, 2),
                notes=[]
            ))
            total_base += best_base
            total_final += best_final_cost
            total_savings += savings
    
    if not optimized_items:
        return None
    
    return StorePlan(
        store_name=store_name,
        items=optimized_items,
        subtotal=round(total_base, 2),
        store_level_discounts=[],
        final_total=round(total_final, 2),
        estimated_savings=round(total_savings, 2)
    )


def optimize_multi_store(
    request: OptimizeRequest,
    store_items: List[StoreItem],
    coupons: List[Coupon],
    stores: List[str]
) -> List[StorePlan]:
    """Optimize by picking the best store for each item."""
    
    # For each item, find the best store
    item_assignments: Dict[str, Tuple[StoreItem, int, List[AppliedCoupon], float]] = {}
    
    for requested in request.shopping_list:
        best_store = None
        best_product = None
        best_cost = float('inf')
        best_coupons = []
        best_qty = 1
        
        for store in stores:
            items_at_store = [i for i in store_items if i.store_name == store]
            matches = match_items(requested, items_at_store)
            
            for product in matches:
                qty_needed = calculate_packages_needed(requested, product)
                base_cost = product.price * qty_needed
                
                applied_coupons, discount = calculate_best_coupon_stack(
                    product, qty_needed, coupons
                )
                
                final_cost = base_cost - discount
                
                if final_cost < best_cost:
                    best_store = store
                    best_product = product
                    best_cost = final_cost
                    best_coupons = applied_coupons
                    best_qty = qty_needed
        
        if best_product:
            item_assignments[requested.name] = (
                best_product, best_qty, best_coupons, best_cost
            )
    
    # Group by store
    store_groups: Dict[str, List[OptimizedItem]] = {}
    
    for requested in request.shopping_list:
        if requested.name in item_assignments:
            product, qty, coupons_applied, cost = item_assignments[requested.name]
            store = product.store_name
            
            if store not in store_groups:
                store_groups[store] = []
            
            base_cost = product.price * qty
            store_groups[store].append(OptimizedItem(
                requested_item=requested,
                chosen_product=product,
                quantity_to_buy=qty,
                base_cost=round(base_cost, 2),
                applied_coupons=coupons_applied,
                final_cost=round(cost, 2),
                savings=round(base_cost - cost, 2),
                notes=[]
            ))
    
    # Create store plans
    plans = []
    for store, items in store_groups.items():
        subtotal = sum(i.base_cost for i in items)
        final = sum(i.final_cost for i in items)
        savings = sum(i.savings for i in items)
        
        plans.append(StorePlan(
            store_name=store,
            items=items,
            subtotal=round(subtotal, 2),
            store_level_discounts=[],
            final_total=round(final, 2),
            estimated_savings=round(savings, 2)
        ))
    
    return plans


def generate_action_steps(plans: List[StorePlan]) -> List[str]:
    """Generate human-readable shopping instructions."""
    steps = []
    
    for i, plan in enumerate(plans):
        if len(plans) > 1:
            steps.append(f"**Stop {i+1}: {plan.store_name}**")
        else:
            steps.append(f"**Shop at {plan.store_name}**")
        
        # Gather coupons to clip
        coupons_to_clip = set()
        for item in plan.items:
            for coupon in item.applied_coupons:
                coupons_to_clip.add(coupon.description)
        
        if coupons_to_clip:
            steps.append("Before shopping:")
            for coupon in coupons_to_clip:
                steps.append(f"  • Clip: {coupon}")
        
        steps.append("Buy:")
        for item in plan.items:
            brand = item.chosen_product.brand or ""
            name = item.chosen_product.item_name
            size = f"{item.chosen_product.package_size} {item.chosen_product.package_unit}"
            steps.append(
                f"  • {item.quantity_to_buy}x {brand} {name} ({size}) = ${item.final_cost:.2f}"
            )
        
        steps.append(f"Total at {plan.store_name}: ${plan.final_total:.2f}")
        steps.append("")
    
    return steps


def optimize_shopping_list(
    request: OptimizeRequest,
    store_items: List[StoreItem],
    coupons: List[Coupon]
) -> OptimizeResponse:
    """
    Main optimization function.
    
    Takes a shopping list and finds the cheapest way to fulfill it
    using available store items and coupons.
    """
    
    # Determine which stores to consider
    if request.preferred_stores:
        stores = request.preferred_stores
    else:
        stores = list(set(i.store_name for i in store_items))
    
    # Filter items to preferred stores
    filtered_items = [i for i in store_items if i.store_name in stores]
    
    if request.allow_multi_store:
        # Optimize across multiple stores
        plans = optimize_multi_store(request, filtered_items, coupons, stores)
    else:
        # Find the single best store
        best_plan = None
        best_total = float('inf')
        
        for store in stores:
            plan = optimize_single_store(request, filtered_items, coupons, store)
            if plan and plan.final_total < best_total:
                best_plan = plan
                best_total = plan.final_total
        
        plans = [best_plan] if best_plan else []
    
    # Calculate totals
    grand_total = sum(p.final_total for p in plans)
    total_base = sum(p.subtotal for p in plans)
    total_savings = sum(p.estimated_savings for p in plans)
    savings_pct = (total_savings / total_base * 100) if total_base > 0 else 0
    
    # Find unfulfilled items
    fulfilled_names = set()
    for plan in plans:
        for item in plan.items:
            fulfilled_names.add(item.requested_item.name.lower())
    
    unfulfilled = [
        item for item in request.shopping_list 
        if item.name.lower() not in fulfilled_names
    ]
    
    # Generate action steps
    action_steps = generate_action_steps(plans)
    
    # Find rebate opportunities
    rebates = []
    for plan in plans:
        for item in plan.items:
            opps = find_rebate_opportunities(
                item.chosen_product, coupons, request.rebate_apps
            )
            for app, amount in opps:
                rebates.append(RebateOpportunity(
                    app=app,
                    item=item.chosen_product.item_name,
                    rebate_amount=amount,
                    instructions=f"Submit receipt to {app} for ${amount:.2f} back"
                ))
    
    return OptimizeResponse(
        plans=plans,
        grand_total=round(grand_total, 2),
        total_base_cost=round(total_base, 2),
        total_savings=round(total_savings, 2),
        savings_percentage=round(savings_pct, 1),
        unfulfilled_items=unfulfilled,
        action_steps=action_steps,
        rebate_opportunities=rebates
    )
