"""
Coupon Sentinel - Stacking Logic

Implements US grocery coupon stacking rules:
- Max 1 manufacturer coupon per item
- Store coupons can stack with manufacturer coupons
- Rebates stack with everything (applied post-purchase)
- BOGO and threshold coupons have special rules
"""

from typing import List, Tuple
from ..models import Coupon, CouponType, DiscountType, StoreItem, AppliedCoupon


def matches_item(coupon: Coupon, item: StoreItem) -> bool:
    """Check if a coupon applies to an item."""
    # Check store scope
    if coupon.store_scope and coupon.store_scope != "any":
        if coupon.store_scope.lower() != item.store_name.lower():
            return False
    
    # Check item filter (name or category match)
    item_filter = coupon.item_filter.lower()
    if item_filter in item.item_name.lower():
        return True
    if item_filter in item.category.lower():
        return True
    if item.brand and item_filter in item.brand.lower():
        return True
    
    # Check brand filter
    if coupon.brand_filter:
        if item.brand and coupon.brand_filter.lower() in item.brand.lower():
            return True
    
    return False


def calculate_discount(coupon: Coupon, item: StoreItem, quantity: int) -> float:
    """Calculate the discount amount for a coupon on an item."""
    if coupon.discount_type == DiscountType.AMOUNT_OFF:
        # Fixed amount off
        return min(coupon.value, item.price * quantity)
    
    elif coupon.discount_type == DiscountType.PERCENT_OFF:
        # Percentage off
        return item.price * quantity * coupon.value
    
    elif coupon.discount_type == DiscountType.BOGO_FREE:
        # Buy one get one free
        if quantity >= 2:
            return item.price  # One item free
        return 0.0
    
    elif coupon.discount_type == DiscountType.BOGO_HALF:
        # Buy one get one 50% off
        if quantity >= 2:
            return item.price * 0.5
        return 0.0
    
    return 0.0


def calculate_best_coupon_stack(
    item: StoreItem,
    quantity: int,
    available_coupons: List[Coupon]
) -> Tuple[List[AppliedCoupon], float]:
    """
    Find the best valid coupon combination for an item.
    
    Rules:
    - Max 1 manufacturer coupon
    - Multiple store coupons allowed (unless store restricts)
    - Rebates tracked separately (post-purchase)
    
    Returns: (applied_coupons, total_discount)
    """
    applied: List[AppliedCoupon] = []
    total_discount = 0.0
    
    # Filter to applicable coupons
    applicable = [c for c in available_coupons if matches_item(c, item)]
    
    # Separate by type
    manufacturer_coupons = [c for c in applicable if c.coupon_type == CouponType.MANUFACTURER]
    store_coupons = [c for c in applicable if c.coupon_type == CouponType.STORE]
    rebates = [c for c in applicable if c.coupon_type == CouponType.REBATE]
    bogo_coupons = [c for c in applicable if c.coupon_type == CouponType.BOGO]
    
    # Apply best manufacturer coupon (max 1)
    if manufacturer_coupons:
        best_mfr = max(manufacturer_coupons, key=lambda c: calculate_discount(c, item, quantity))
        discount = calculate_discount(best_mfr, item, quantity)
        if discount > 0:
            applied.append(AppliedCoupon(
                coupon_id=best_mfr.id,
                description=best_mfr.description,
                coupon_type=best_mfr.coupon_type,
                discount_amount=discount
            ))
            total_discount += discount
    
    # Apply store coupons (can stack multiple, usually)
    for coupon in store_coupons:
        discount = calculate_discount(coupon, item, quantity)
        if discount > 0:
            applied.append(AppliedCoupon(
                coupon_id=coupon.id,
                description=coupon.description,
                coupon_type=coupon.coupon_type,
                discount_amount=discount
            ))
            total_discount += discount
    
    # Apply BOGO if beneficial
    for coupon in bogo_coupons:
        discount = calculate_discount(coupon, item, quantity)
        if discount > 0:
            applied.append(AppliedCoupon(
                coupon_id=coupon.id,
                description=coupon.description,
                coupon_type=coupon.coupon_type,
                discount_amount=discount
            ))
            total_discount += discount
    
    # Note: Rebates are tracked but not applied to in-store total
    # They're returned separately in the optimization result
    
    # Ensure we don't discount below $0
    base_price = item.price * quantity
    total_discount = min(total_discount, base_price)
    
    return applied, total_discount


def find_rebate_opportunities(
    item: StoreItem,
    available_coupons: List[Coupon],
    rebate_apps: List[str]
) -> List[Tuple[str, float]]:
    """Find rebate opportunities for an item after purchase."""
    opportunities = []
    
    rebates = [c for c in available_coupons if c.coupon_type == CouponType.REBATE]
    
    for rebate in rebates:
        if matches_item(rebate, item):
            # Check if user has this rebate app
            app_name = rebate.source
            if app_name.lower() in [a.lower() for a in rebate_apps]:
                opportunities.append((app_name, rebate.value))
    
    return opportunities
