"""
Coupon Sentinel - Mock Data Provider

Realistic sample data for testing the optimization engine.
Replace this with real API integrations in production.
"""

from typing import List
from backend.models import StoreItem, Coupon, CouponType, DiscountType


SUPPORTED_STORES = ["Target", "Walmart", "Costco"]


def get_mock_store_items() -> List[StoreItem]:
    """Return mock store inventory data."""
    
    items = [
        # ============================================================
        # TARGET
        # ============================================================
        # Dairy
        StoreItem(
            store_name="Target",
            item_name="Organic Whole Milk",
            brand="Good & Gather",
            package_size=1.0,
            package_unit="gallon",
            price=4.99,
            regular_price=5.49,
            category="dairy",
            loyalty_price=4.49,
            in_stock=True
        ),
        StoreItem(
            store_name="Target",
            item_name="2% Reduced Fat Milk",
            brand="Good & Gather",
            package_size=1.0,
            package_unit="gallon",
            price=3.99,
            category="dairy",
            in_stock=True
        ),
        StoreItem(
            store_name="Target",
            item_name="Large Grade A Eggs",
            brand="Good & Gather",
            package_size=12.0,
            package_unit="count",
            price=3.49,
            category="dairy",
            in_stock=True
        ),
        StoreItem(
            store_name="Target",
            item_name="Large Grade A Eggs",
            brand="Good & Gather",
            package_size=18.0,
            package_unit="count",
            price=4.99,
            category="dairy",
            in_stock=True
        ),
        # Bread & Bakery
        StoreItem(
            store_name="Target",
            item_name="Whole Wheat Bread",
            brand="Good & Gather",
            package_size=1.0,
            package_unit="count",
            price=2.99,
            category="bakery",
            in_stock=True
        ),
        StoreItem(
            store_name="Target",
            item_name="White Sandwich Bread",
            brand="Wonder",
            package_size=1.0,
            package_unit="count",
            price=3.49,
            category="bakery",
            in_stock=True
        ),
        # Meat
        StoreItem(
            store_name="Target",
            item_name="Boneless Skinless Chicken Breast",
            brand="Good & Gather",
            package_size=1.5,
            package_unit="lb",
            price=7.99,
            category="meat",
            in_stock=True
        ),
        StoreItem(
            store_name="Target",
            item_name="Ground Beef 80/20",
            brand="Good & Gather",
            package_size=1.0,
            package_unit="lb",
            price=5.99,
            category="meat",
            in_stock=True
        ),
        # Pasta & Sauce
        StoreItem(
            store_name="Target",
            item_name="Spaghetti Pasta",
            brand="Barilla",
            package_size=1.0,
            package_unit="lb",
            price=1.89,
            category="pasta",
            in_stock=True
        ),
        StoreItem(
            store_name="Target",
            item_name="Marinara Sauce",
            brand="Rao's",
            package_size=24.0,
            package_unit="oz",
            price=8.99,
            category="pasta",
            in_stock=True
        ),
        StoreItem(
            store_name="Target",
            item_name="Marinara Sauce",
            brand="Prego",
            package_size=24.0,
            package_unit="oz",
            price=3.29,
            category="pasta",
            in_stock=True
        ),
        # Snacks
        StoreItem(
            store_name="Target",
            item_name="Tortilla Chips",
            brand="Tostitos",
            package_size=13.0,
            package_unit="oz",
            price=4.99,
            category="snacks",
            in_stock=True
        ),
        # Beverages
        StoreItem(
            store_name="Target",
            item_name="Orange Juice",
            brand="Simply",
            package_size=52.0,
            package_unit="oz",
            price=4.49,
            category="beverages",
            in_stock=True
        ),
        StoreItem(
            store_name="Target",
            item_name="Coffee",
            brand="Starbucks",
            package_size=12.0,
            package_unit="oz",
            price=9.99,
            category="beverages",
            in_stock=True
        ),
        
        # ============================================================
        # WALMART
        # ============================================================
        # Dairy
        StoreItem(
            store_name="Walmart",
            item_name="Whole Milk",
            brand="Great Value",
            package_size=1.0,
            package_unit="gallon",
            price=3.48,
            category="dairy",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="2% Reduced Fat Milk",
            brand="Great Value",
            package_size=1.0,
            package_unit="gallon",
            price=3.28,
            category="dairy",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="Large Grade A Eggs",
            brand="Great Value",
            package_size=12.0,
            package_unit="count",
            price=2.98,
            category="dairy",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="Large Grade A Eggs",
            brand="Great Value",
            package_size=18.0,
            package_unit="count",
            price=4.24,
            category="dairy",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="Large Grade A Eggs",
            brand="Great Value",
            package_size=60.0,
            package_unit="count",
            price=11.98,
            category="dairy",
            in_stock=True
        ),
        # Bread
        StoreItem(
            store_name="Walmart",
            item_name="Whole Wheat Bread",
            brand="Great Value",
            package_size=1.0,
            package_unit="count",
            price=1.48,
            category="bakery",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="White Sandwich Bread",
            brand="Great Value",
            package_size=1.0,
            package_unit="count",
            price=1.28,
            category="bakery",
            in_stock=True
        ),
        # Meat
        StoreItem(
            store_name="Walmart",
            item_name="Boneless Skinless Chicken Breast",
            brand="Great Value",
            package_size=2.5,
            package_unit="lb",
            price=9.97,
            category="meat",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="Ground Beef 80/20",
            brand="Great Value",
            package_size=1.0,
            package_unit="lb",
            price=4.98,
            category="meat",
            in_stock=True
        ),
        # Pasta
        StoreItem(
            store_name="Walmart",
            item_name="Spaghetti Pasta",
            brand="Barilla",
            package_size=1.0,
            package_unit="lb",
            price=1.48,
            category="pasta",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="Spaghetti Pasta",
            brand="Great Value",
            package_size=1.0,
            package_unit="lb",
            price=0.98,
            category="pasta",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="Marinara Sauce",
            brand="Prego",
            package_size=24.0,
            package_unit="oz",
            price=2.98,
            category="pasta",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="Marinara Sauce",
            brand="Great Value",
            package_size=24.0,
            package_unit="oz",
            price=1.98,
            category="pasta",
            in_stock=True
        ),
        # Snacks
        StoreItem(
            store_name="Walmart",
            item_name="Tortilla Chips",
            brand="Tostitos",
            package_size=13.0,
            package_unit="oz",
            price=4.48,
            category="snacks",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="Tortilla Chips",
            brand="Great Value",
            package_size=13.0,
            package_unit="oz",
            price=2.48,
            category="snacks",
            in_stock=True
        ),
        # Beverages
        StoreItem(
            store_name="Walmart",
            item_name="Orange Juice",
            brand="Simply",
            package_size=52.0,
            package_unit="oz",
            price=3.98,
            category="beverages",
            in_stock=True
        ),
        StoreItem(
            store_name="Walmart",
            item_name="Coffee",
            brand="Folgers",
            package_size=30.5,
            package_unit="oz",
            price=9.98,
            category="beverages",
            in_stock=True
        ),
        
        # ============================================================
        # COSTCO (Bulk Sizes)
        # ============================================================
        StoreItem(
            store_name="Costco",
            item_name="Organic Whole Milk",
            brand="Kirkland",
            package_size=2.0,
            package_unit="gallon",
            price=6.99,
            category="dairy",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Cage Free Eggs",
            brand="Kirkland",
            package_size=24.0,
            package_unit="count",
            price=6.99,
            category="dairy",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Cage Free Eggs",
            brand="Kirkland",
            package_size=60.0,
            package_unit="count",
            price=14.99,
            category="dairy",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Artisan Bread",
            brand="Kirkland",
            package_size=2.0,
            package_unit="count",
            price=4.99,
            category="bakery",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Boneless Skinless Chicken Breast",
            brand="Kirkland",
            package_size=6.0,
            package_unit="lb",
            price=22.99,
            category="meat",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Ground Beef 88/12",
            brand="Kirkland",
            package_size=4.0,
            package_unit="lb",
            price=19.99,
            category="meat",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Spaghetti Pasta",
            brand="Barilla",
            package_size=6.0,
            package_unit="lb",
            price=7.99,
            category="pasta",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Marinara Sauce",
            brand="Rao's",
            package_size=54.0,
            package_unit="oz",
            price=11.99,
            category="pasta",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Tortilla Chips",
            brand="Kirkland",
            package_size=40.0,
            package_unit="oz",
            price=6.99,
            category="snacks",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Orange Juice",
            brand="Kirkland",
            package_size=2.0,
            package_unit="gallon",
            price=8.99,
            category="beverages",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Coffee",
            brand="Kirkland",
            package_size=48.0,
            package_unit="oz",
            price=16.99,
            category="beverages",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Toilet Paper",
            brand="Kirkland",
            package_size=30.0,
            package_unit="count",
            price=24.99,
            category="household",
            in_stock=True
        ),
        StoreItem(
            store_name="Costco",
            item_name="Paper Towels",
            brand="Kirkland",
            package_size=12.0,
            package_unit="count",
            price=19.99,
            category="household",
            in_stock=True
        ),
    ]
    
    return items


def get_mock_coupons() -> List[Coupon]:
    """Return mock coupon/discount data."""
    
    coupons = [
        # ============================================================
        # MANUFACTURER COUPONS (work at any store)
        # ============================================================
        Coupon(
            id="mfr-barilla-1",
            coupon_type=CouponType.MANUFACTURER,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="$0.75 off 2 Barilla pasta",
            item_filter="pasta",
            brand_filter="Barilla",
            value=0.75,
            min_quantity=2,
            source="coupons.com"
        ),
        Coupon(
            id="mfr-tostitos-1",
            coupon_type=CouponType.MANUFACTURER,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="$1.00 off Tostitos chips",
            item_filter="chips",
            brand_filter="Tostitos",
            value=1.00,
            source="newspaper"
        ),
        Coupon(
            id="mfr-prego-1",
            coupon_type=CouponType.MANUFACTURER,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="$0.50 off Prego sauce",
            item_filter="sauce",
            brand_filter="Prego",
            value=0.50,
            source="prego.com"
        ),
        Coupon(
            id="mfr-simply-1",
            coupon_type=CouponType.MANUFACTURER,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="$0.75 off Simply Orange Juice",
            item_filter="orange juice",
            brand_filter="Simply",
            value=0.75,
            source="ibotta"
        ),
        Coupon(
            id="mfr-folgers-1",
            coupon_type=CouponType.MANUFACTURER,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="$1.50 off Folgers coffee",
            item_filter="coffee",
            brand_filter="Folgers",
            value=1.50,
            source="smartsource"
        ),
        
        # ============================================================
        # TARGET STORE COUPONS
        # ============================================================
        Coupon(
            id="target-dairy-1",
            coupon_type=CouponType.STORE,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="Target",
            description="$1 off Good & Gather dairy",
            item_filter="dairy",
            brand_filter="Good & Gather",
            value=1.00,
            source="Target Circle"
        ),
        Coupon(
            id="target-meat-1",
            coupon_type=CouponType.STORE,
            discount_type=DiscountType.PERCENT_OFF,
            store_scope="Target",
            description="15% off meat purchase",
            item_filter="meat",
            value=0.15,
            source="Target Circle"
        ),
        Coupon(
            id="target-bread-1",
            coupon_type=CouponType.STORE,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="Target",
            description="$0.50 off Wonder bread",
            item_filter="bread",
            brand_filter="Wonder",
            value=0.50,
            source="Target Circle"
        ),
        Coupon(
            id="target-starbucks-1",
            coupon_type=CouponType.STORE,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="Target",
            description="$2 off Starbucks coffee",
            item_filter="coffee",
            brand_filter="Starbucks",
            value=2.00,
            source="Target Circle"
        ),
        
        # ============================================================
        # WALMART STORE COUPONS
        # ============================================================
        Coupon(
            id="walmart-rollback-eggs",
            coupon_type=CouponType.STORE,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="Walmart",
            description="Rollback: $0.30 off eggs",
            item_filter="eggs",
            value=0.30,
            source="Walmart"
        ),
        Coupon(
            id="walmart-great-value-1",
            coupon_type=CouponType.STORE,
            discount_type=DiscountType.PERCENT_OFF,
            store_scope="Walmart",
            description="10% off Great Value brand",
            item_filter="great value",
            brand_filter="Great Value",
            value=0.10,
            source="Walmart+"
        ),
        
        # ============================================================
        # REBATE OFFERS (post-purchase)
        # ============================================================
        Coupon(
            id="ibotta-milk-1",
            coupon_type=CouponType.REBATE,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="$0.50 back on milk",
            item_filter="milk",
            value=0.50,
            source="Ibotta"
        ),
        Coupon(
            id="ibotta-eggs-1",
            coupon_type=CouponType.REBATE,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="$0.75 back on eggs",
            item_filter="eggs",
            value=0.75,
            source="Ibotta"
        ),
        Coupon(
            id="ibotta-bread-1",
            coupon_type=CouponType.REBATE,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="$0.25 back on bread",
            item_filter="bread",
            value=0.25,
            source="Ibotta"
        ),
        Coupon(
            id="fetch-any-1",
            coupon_type=CouponType.REBATE,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="25 points ($0.25) on any receipt",
            item_filter="any",
            value=0.25,
            source="Fetch"
        ),
        Coupon(
            id="ibotta-chips-1",
            coupon_type=CouponType.REBATE,
            discount_type=DiscountType.AMOUNT_OFF,
            store_scope="any",
            description="$1.00 back on Tostitos",
            item_filter="chips",
            brand_filter="Tostitos",
            value=1.00,
            source="Ibotta"
        ),
        
        # ============================================================
        # BOGO OFFERS
        # ============================================================
        Coupon(
            id="target-bogo-sauce",
            coupon_type=CouponType.BOGO,
            discount_type=DiscountType.BOGO_HALF,
            store_scope="Target",
            description="BOGO 50% off pasta sauce",
            item_filter="sauce",
            value=0.0,  # Calculated dynamically
            min_quantity=2,
            source="Target Weekly Ad"
        ),
    ]
    
    return coupons
