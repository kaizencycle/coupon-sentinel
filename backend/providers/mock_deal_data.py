"""
Coupon Sentinel — Mock Deal Intelligence Data (PR-1)

FIXTURE / MOCK DATA ONLY — not live retailer prices.
Demonstrates canonical observation → deal event flow including receipt-backed evidence.
"""

from datetime import datetime, timezone
from typing import Dict, List, Tuple

from backend.deal_models import (
    DealEvent,
    DealType,
    EvidenceType,
    PriceObservation,
    ProductIdentity,
)
from backend.engines.deal_engine import build_deal_from_observations

MOCK_DATA_NOTICE = (
    "All prices in this module are synthetic fixtures for development and testing. "
    "They do not represent live retailer pricing."
)

_OBSERVED_AT = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
_OBSERVED_EARLIER = datetime(2026, 8, 6, 9, 30, 0, tzinfo=timezone.utc)


def get_mock_products() -> List[ProductIdentity]:
    return [
        ProductIdentity(
            id="prod-tide-pods",
            name="Tide Pods Laundry Detergent",
            brand="Tide",
            upc="012345678901",
            category="household",
            package_size=42.0,
            package_unit="count",
        ),
        ProductIdentity(
            id="prod-gv-milk",
            name="Whole Milk",
            brand="Great Value",
            upc="078742000123",
            category="dairy",
            package_size=1.0,
            package_unit="gallon",
        ),
        ProductIdentity(
            id="prod-barilla-pasta",
            name="Spaghetti Pasta",
            brand="Barilla",
            upc="076808000001",
            category="pasta",
            package_size=1.0,
            package_unit="lb",
        ),
        ProductIdentity(
            id="prod-cereal-clearance",
            name="Honey Nut Cereal",
            brand="Cheerios",
            upc="016000000100",
            category="breakfast",
            package_size=18.0,
            package_unit="oz",
        ),
        ProductIdentity(
            id="prod-penny-pull",
            name="Seasonal Decor Item",
            brand="Store Brand",
            upc="099999999901",
            category="seasonal",
            package_size=1.0,
            package_unit="count",
        ),
        ProductIdentity(
            id="prod-price-anomaly",
            name="Premium Olive Oil",
            brand="Bertolli",
            upc="041618000050",
            category="pantry",
            package_size=17.0,
            package_unit="oz",
        ),
        ProductIdentity(
            id="prod-coffee-stack",
            name="Ground Coffee",
            brand="Folgers",
            upc="025500002000",
            category="beverages",
            package_size=30.5,
            package_unit="oz",
        ),
        ProductIdentity(
            id="prod-chips-rebate",
            name="Tortilla Chips",
            brand="Tostitos",
            upc="028400000100",
            category="snacks",
            package_size=13.0,
            package_unit="oz",
        ),
    ]


def get_mock_price_observations() -> List[PriceObservation]:
    """Normalized price observations — evidence layer only."""
    return [
        # Receipt-backed Tide Pods (canonical receipt fixture)
        PriceObservation(
            id="obs-tide-receipt",
            product_id="prod-tide-pods",
            upc="012345678901",
            retailer="Target",
            store_id="target-11429",
            zip_code="11429",
            observed_price=11.99,
            regular_price=14.99,
            observed_at=_OBSERVED_AT,
            evidence_type=EvidenceType.RECEIPT,
            source="receipt_fixture_normalized",
            confidence=0.98,
            in_stock=None,
        ),
        # Second observation same SKU/location — coupon feed
        PriceObservation(
            id="obs-tide-coupon-feed",
            product_id="prod-tide-pods",
            upc="012345678901",
            retailer="Target",
            store_id="target-11429",
            zip_code="11429",
            observed_price=11.99,
            regular_price=14.99,
            observed_at=_OBSERVED_EARLIER,
            evidence_type=EvidenceType.COUPON_FEED,
            source="mock_coupon_feed",
            confidence=0.75,
            in_stock=None,
        ),
        # Normal shelf price
        PriceObservation(
            id="obs-milk-shelf",
            product_id="prod-gv-milk",
            upc="078742000123",
            retailer="Walmart",
            store_id="walmart-11566",
            zip_code="11566",
            observed_price=3.48,
            regular_price=3.48,
            observed_at=_OBSERVED_AT,
            evidence_type=EvidenceType.RETAILER_PUBLIC,
            source="mock_retailer_listing",
            confidence=0.85,
            in_stock=True,
        ),
        # Two observations same SKU/location (milk)
        PriceObservation(
            id="obs-milk-community-1",
            product_id="prod-gv-milk",
            upc="078742000123",
            retailer="Walmart",
            store_id="walmart-11566",
            zip_code="11566",
            observed_price=3.48,
            observed_at=_OBSERVED_EARLIER,
            evidence_type=EvidenceType.COMMUNITY_REPORT,
            source="mock_community_user_a",
            confidence=0.55,
            in_stock=None,
        ),
        PriceObservation(
            id="obs-milk-community-2",
            product_id="prod-gv-milk",
            upc="078742000123",
            retailer="Walmart",
            store_id="walmart-11566",
            zip_code="11566",
            observed_price=3.48,
            observed_at=_OBSERVED_AT,
            evidence_type=EvidenceType.COMMUNITY_REPORT,
            source="mock_community_user_b",
            confidence=0.50,
            in_stock=None,
        ),
        # Sale
        PriceObservation(
            id="obs-pasta-sale",
            product_id="prod-barilla-pasta",
            upc="076808000001",
            retailer="Target",
            store_id="target-11566",
            zip_code="11566",
            observed_price=1.29,
            regular_price=1.89,
            observed_at=_OBSERVED_AT,
            evidence_type=EvidenceType.WEEKLY_AD,
            source="mock_weekly_ad",
            confidence=0.80,
            in_stock=True,
        ),
        # Clearance markdown
        PriceObservation(
            id="obs-cereal-clearance",
            product_id="prod-cereal-clearance",
            upc="016000000100",
            retailer="Target",
            store_id="target-11566",
            zip_code="11566",
            observed_price=2.49,
            regular_price=5.99,
            observed_at=_OBSERVED_AT,
            evidence_type=EvidenceType.RETAILER_PUBLIC,
            source="mock_clearance_tag",
            confidence=0.82,
            in_stock=True,
        ),
        # Penny/pull — internal shelf-remove condition, not a promotion
        PriceObservation(
            id="obs-penny-pull",
            product_id="prod-penny-pull",
            upc="099999999901",
            retailer="Walmart",
            store_id="walmart-11566",
            zip_code="11566",
            observed_price=0.01,
            regular_price=12.99,
            observed_at=_OBSERVED_AT,
            evidence_type=EvidenceType.COMMUNITY_REPORT,
            source="mock_penny_pull_report",
            confidence=0.70,
            in_stock=None,
        ),
        # Price anomaly — observation only, not an accusation
        PriceObservation(
            id="obs-price-anomaly",
            product_id="prod-price-anomaly",
            upc="041618000050",
            retailer="Target",
            store_id="target-11566",
            zip_code="11566",
            observed_price=1.99,
            regular_price=9.99,
            observed_at=_OBSERVED_AT,
            evidence_type=EvidenceType.COMMUNITY_REPORT,
            source="mock_anomaly_report",
            confidence=0.40,
            in_stock=None,
        ),
        # Coupon stack support observation
        PriceObservation(
            id="obs-coffee-sale",
            product_id="prod-coffee-stack",
            upc="025500002000",
            retailer="Walmart",
            store_id="walmart-11566",
            zip_code="11566",
            observed_price=9.98,
            regular_price=11.98,
            observed_at=_OBSERVED_AT,
            evidence_type=EvidenceType.RETAILER_PUBLIC,
            source="mock_retailer_listing",
            confidence=0.85,
            in_stock=True,
        ),
        # Rebate stack support
        PriceObservation(
            id="obs-chips-shelf",
            product_id="prod-chips-rebate",
            upc="028400000100",
            retailer="Target",
            store_id="target-11566",
            zip_code="11566",
            observed_price=4.99,
            regular_price=4.99,
            observed_at=_OBSERVED_AT,
            evidence_type=EvidenceType.RETAILER_PUBLIC,
            source="mock_retailer_listing",
            confidence=0.85,
            in_stock=True,
        ),
    ]


def get_mock_deal_events() -> List[DealEvent]:
    """Deal events derived from mock observations — interpretation layer."""
    observations = {o.id: o for o in get_mock_price_observations()}

    def obs(ids: List[str]) -> List[PriceObservation]:
        return [observations[i] for i in ids]

    deals = [
        # STACK — Tide Pods (UI showcase card)
        build_deal_from_observations(
            deal_id="deal-tide-stack",
            product_id="prod-tide-pods",
            retailer="Target",
            deal_type=DealType.STACK,
            observations=obs(["obs-tide-receipt", "obs-tide-coupon-feed"]),
            current_price=11.99,
            regular_price=14.99,
            coupon_value=3.00,
            rebate_value=2.00,
            store_id="target-11429",
            zip_code="11429",
            inventory_confirmed=False,
        ),
        # Normal shelf price
        build_deal_from_observations(
            deal_id="deal-milk-shelf",
            product_id="prod-gv-milk",
            retailer="Walmart",
            deal_type=DealType.UNKNOWN,
            observations=obs(["obs-milk-shelf"]),
            current_price=3.48,
            regular_price=3.48,
            store_id="walmart-11566",
            zip_code="11566",
            inventory_confirmed=True,
        ),
        # Two community observations same SKU/location
        build_deal_from_observations(
            deal_id="deal-milk-community",
            product_id="prod-gv-milk",
            retailer="Walmart",
            deal_type=DealType.SALE,
            observations=obs(["obs-milk-community-1", "obs-milk-community-2"]),
            current_price=3.48,
            regular_price=3.48,
            store_id="walmart-11566",
            zip_code="11566",
            inventory_confirmed=False,
        ),
        # Sale
        build_deal_from_observations(
            deal_id="deal-pasta-sale",
            product_id="prod-barilla-pasta",
            retailer="Target",
            deal_type=DealType.SALE,
            observations=obs(["obs-pasta-sale"]),
            current_price=1.29,
            regular_price=1.89,
            store_id="target-11566",
            zip_code="11566",
            inventory_confirmed=True,
        ),
        # Coupon stack
        build_deal_from_observations(
            deal_id="deal-coffee-coupon-stack",
            product_id="prod-coffee-stack",
            retailer="Walmart",
            deal_type=DealType.COUPON,
            observations=obs(["obs-coffee-sale"]),
            current_price=9.98,
            regular_price=11.98,
            coupon_value=1.50,
            store_id="walmart-11566",
            zip_code="11566",
            inventory_confirmed=True,
        ),
        # Rebate stack
        build_deal_from_observations(
            deal_id="deal-chips-rebate-stack",
            product_id="prod-chips-rebate",
            retailer="Target",
            deal_type=DealType.REBATE,
            observations=obs(["obs-chips-shelf"]),
            current_price=4.99,
            regular_price=4.99,
            coupon_value=1.00,
            rebate_value=1.00,
            store_id="target-11566",
            zip_code="11566",
            inventory_confirmed=True,
        ),
        # Clearance markdown
        build_deal_from_observations(
            deal_id="deal-cereal-clearance",
            product_id="prod-cereal-clearance",
            retailer="Target",
            deal_type=DealType.CLEARANCE,
            observations=obs(["obs-cereal-clearance"]),
            current_price=2.49,
            regular_price=5.99,
            store_id="target-11566",
            zip_code="11566",
            inventory_confirmed=True,
        ),
        # Penny/pull — inventory NOT confirmed
        build_deal_from_observations(
            deal_id="deal-penny-pull",
            product_id="prod-penny-pull",
            retailer="Walmart",
            deal_type=DealType.PENNY_OR_PULL,
            observations=obs(["obs-penny-pull"]),
            current_price=0.01,
            regular_price=12.99,
            store_id="walmart-11566",
            zip_code="11566",
            inventory_confirmed=False,
        ),
        # Price anomaly
        build_deal_from_observations(
            deal_id="deal-price-anomaly",
            product_id="prod-price-anomaly",
            retailer="Target",
            deal_type=DealType.PRICE_ANOMALY,
            observations=obs(["obs-price-anomaly"]),
            current_price=1.99,
            regular_price=9.99,
            store_id="target-11566",
            zip_code="11566",
            inventory_confirmed=False,
        ),
    ]

    return deals


def get_mock_deal_catalog() -> Tuple[List[ProductIdentity], List[PriceObservation], List[DealEvent]]:
    return get_mock_products(), get_mock_price_observations(), get_mock_deal_events()


def get_product_index() -> Dict[str, ProductIdentity]:
    return {p.id: p for p in get_mock_products()}
