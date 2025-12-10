"""
Coupon Sentinel - Data Models
Pydantic models for items, coupons, stores, and optimization results.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class CouponType(str, Enum):
    MANUFACTURER = "manufacturer"
    STORE = "store"
    REBATE = "rebate"
    BOGO = "bogo"
    THRESHOLD = "threshold"  # e.g., "$5 off $25"


class DiscountType(str, Enum):
    AMOUNT_OFF = "amount_off"
    PERCENT_OFF = "percent_off"
    BOGO_FREE = "bogo_free"
    BOGO_HALF = "bogo_half"


# ============================================================================
# Input Models
# ============================================================================

class ShoppingItem(BaseModel):
    """An item the user wants to buy."""
    name: str = Field(..., description="Item name (e.g., 'milk', 'eggs')")
    quantity: float = Field(1, description="How many to buy")
    unit: str = Field("count", description="Unit type: 'count', 'lb', 'oz', 'gallon'")
    brand_preference: Optional[str] = Field(None, description="Preferred brand (optional)")
    flexible: bool = Field(True, description="Allow store brand substitutions")


class OptimizeRequest(BaseModel):
    """Request to optimize a shopping list."""
    shopping_list: List[ShoppingItem]
    zip_code: str = Field(..., description="User's zip code for store selection")
    preferred_stores: List[str] = Field(default_factory=list, description="Preferred stores")
    allow_multi_store: bool = Field(False, description="Allow splitting across stores")
    rebate_apps: List[str] = Field(default_factory=list, description="Rebate apps user has")


# ============================================================================
# Store & Product Models
# ============================================================================

class StoreItem(BaseModel):
    """A product available at a specific store."""
    store_name: str
    item_name: str
    brand: Optional[str] = None
    package_size: float = Field(..., description="Package size (e.g., 12 for 12-count)")
    package_unit: str = Field(..., description="Unit: 'count', 'oz', 'lb', 'gallon'")
    price: float = Field(..., description="Current price")
    regular_price: Optional[float] = Field(None, description="Regular price if on sale")
    category: str = Field(..., description="Category: 'dairy', 'meat', 'produce', etc.")
    upc: Optional[str] = None
    loyalty_price: Optional[float] = Field(None, description="Price with loyalty card")
    in_stock: bool = True

    @property
    def unit_price(self) -> float:
        """Price per unit (e.g., per oz, per count)."""
        return self.price / self.package_size if self.package_size > 0 else self.price


# ============================================================================
# Coupon Models
# ============================================================================

class Coupon(BaseModel):
    """A coupon or discount offer."""
    id: str
    coupon_type: CouponType
    discount_type: DiscountType
    store_scope: Optional[str] = Field(None, description="Store name or 'any'")
    description: str
    item_filter: str = Field(..., description="Item name, category, or UPC to match")
    brand_filter: Optional[str] = None
    value: float = Field(..., description="Discount amount or percentage (0.20 = 20%)")
    min_quantity: int = Field(1, description="Minimum items to trigger")
    min_spend: Optional[float] = Field(None, description="Minimum spend to trigger")
    max_uses: int = Field(1, description="Max times this coupon can be used")
    expires_at: Optional[str] = None
    source: str = Field("manual", description="Where coupon came from")
    stackable: bool = Field(True, description="Can stack with other coupons")


# ============================================================================
# Output Models
# ============================================================================

class AppliedCoupon(BaseModel):
    """A coupon that was applied to an item."""
    coupon_id: str
    description: str
    coupon_type: CouponType
    discount_amount: float


class OptimizedItem(BaseModel):
    """An item in the optimized plan."""
    requested_item: ShoppingItem
    chosen_product: StoreItem
    quantity_to_buy: int = Field(..., description="How many packages to buy")
    base_cost: float
    applied_coupons: List[AppliedCoupon] = Field(default_factory=list)
    final_cost: float
    savings: float
    notes: List[str] = Field(default_factory=list)


class StorePlan(BaseModel):
    """Shopping plan for a single store."""
    store_name: str
    items: List[OptimizedItem]
    subtotal: float
    store_level_discounts: List[AppliedCoupon] = Field(default_factory=list)
    final_total: float
    estimated_savings: float


class RebateOpportunity(BaseModel):
    """A rebate that can be claimed after purchase."""
    app: str = Field(..., description="Rebate app name")
    item: str
    rebate_amount: float
    instructions: str


class OptimizeResponse(BaseModel):
    """Complete optimization result."""
    plans: List[StorePlan]
    grand_total: float
    total_base_cost: float
    total_savings: float
    savings_percentage: float
    unfulfilled_items: List[ShoppingItem] = Field(default_factory=list)
    action_steps: List[str] = Field(default_factory=list)
    rebate_opportunities: List[RebateOpportunity] = Field(default_factory=list)
