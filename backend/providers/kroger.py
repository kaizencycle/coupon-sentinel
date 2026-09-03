"""
Coupon Sentinel - Kroger API Client (Milestone 2)

OAuth2 client-credentials client for the Kroger Public API
(https://developer.kroger.com/reference/) — product search and price lookup.

Status: implemented per Kroger's documented API shape and covered by unit
tests against a mocked HTTP transport (see backend/tests/test_kroger_client.py).
NOT verified against Kroger's live sandbox — no KROGER_CLIENT_ID/SECRET exist
for this project yet. Treat the response-parsing logic as reviewed-but-unproven
until it's run against a real account.

Same guarded pattern as Stripe (backend/engines/subscription_engine.py):
importing/instantiating this module never requires credentials — only
actually calling the API does, and it fails with a clear error rather than
silently returning nothing.
"""

import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

import httpx

KROGER_CLIENT_ID = os.environ.get("KROGER_CLIENT_ID")
KROGER_CLIENT_SECRET = os.environ.get("KROGER_CLIENT_SECRET")
KROGER_BASE_URL = os.environ.get("KROGER_BASE_URL", "https://api.kroger.com/v1")


class KrogerNotConfiguredError(RuntimeError):
    """Raised when KROGER_CLIENT_ID / KROGER_CLIENT_SECRET are not set."""


class KrogerRateLimitError(RuntimeError):
    """Raised when the client-side sliding-window rate limit is exceeded."""


class KrogerNotFoundError(RuntimeError):
    """Raised when Kroger returns 404 for a specific resource lookup."""


class KrogerRateLimiter:
    """
    Sliding-window rate limiter — Kroger's documented public API limit is
    ~10 requests/sec. This is a client-side guard against bursting past that,
    not a substitute for handling 429s from the server.
    """

    def __init__(self, rate: int = 10, window_seconds: float = 1.0):
        self.rate = rate
        self.window_seconds = window_seconds
        self._timestamps: deque = deque()

    def acquire(self, now: Optional[float] = None) -> None:
        now = time.monotonic() if now is None else now
        while self._timestamps and now - self._timestamps[0] > self.window_seconds:
            self._timestamps.popleft()

        if len(self._timestamps) >= self.rate:
            wait_time = self.window_seconds - (now - self._timestamps[0])
            raise KrogerRateLimitError(f"Kroger rate limit exceeded, retry after {wait_time:.2f}s")

        self._timestamps.append(now)


@dataclass
class KrogerProduct:
    """Normalized subset of a Kroger /products response item."""

    product_id: str
    description: str
    upc: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None
    regular_price: Optional[float] = None
    promo_price: Optional[float] = None
    size: Optional[str] = None
    location_id: Optional[str] = None


def _parse_product(item: dict) -> KrogerProduct:
    fulfillment_items = item.get("items") or [{}]
    first_item = fulfillment_items[0] or {}
    price_block = first_item.get("price") or {}
    aisle_locations = item.get("aisleLocations") or []

    regular_price = price_block.get("regular")
    promo_price = price_block.get("promo")

    return KrogerProduct(
        product_id=item.get("productId", ""),
        description=item.get("description", ""),
        upc=item.get("upc"),
        brand=item.get("brand"),
        price=promo_price or regular_price,
        regular_price=regular_price,
        promo_price=promo_price,
        size=first_item.get("size"),
        location_id=aisle_locations[0].get("locationId") if aisle_locations else None,
    )


class KrogerClient:
    """
    Thin wrapper around the Kroger Product API. Caches the OAuth token until
    it's near expiry (client-credentials tokens are ~30 min). One instance is
    safe to reuse across requests within a process.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.client_id = client_id if client_id is not None else KROGER_CLIENT_ID
        self.client_secret = client_secret if client_secret is not None else KROGER_CLIENT_SECRET
        self.base_url = base_url or KROGER_BASE_URL
        self._http = http_client or httpx.Client(base_url=self.base_url, timeout=10.0)
        self._rate_limiter = KrogerRateLimiter()
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _require_configured(self) -> None:
        if not self.client_id or not self.client_secret:
            raise KrogerNotConfiguredError(
                "Kroger API is not configured (KROGER_CLIENT_ID/KROGER_CLIENT_SECRET missing)"
            )

    def _get_access_token(self) -> str:
        self._require_configured()

        now = time.time()
        if self._token and now < self._token_expires_at - 30:
            return self._token

        self._rate_limiter.acquire()
        response = self._http.post(
            "/connect/oauth2/token",
            data={"grant_type": "client_credentials", "scope": "product.compact"},
            auth=(self.client_id, self.client_secret),
        )
        response.raise_for_status()
        payload = response.json()

        self._token = payload["access_token"]
        self._token_expires_at = now + payload.get("expires_in", 1800)
        return self._token

    def _authed_get(self, path: str, params: dict) -> dict:
        token = self._get_access_token()
        self._rate_limiter.acquire()
        response = self._http.get(path, params=params, headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 404:
            raise KrogerNotFoundError(f"Kroger resource not found: {path}")
        response.raise_for_status()
        return response.json()

    def search_products(
        self, term: str, location_id: Optional[str] = None, limit: int = 10
    ) -> list[KrogerProduct]:
        params = {"filter.term": term, "filter.limit": limit}
        if location_id:
            params["filter.locationId"] = location_id
        data = self._authed_get("/products", params)
        return [_parse_product(item) for item in data.get("data", [])]

    def get_product(self, product_id: str, location_id: Optional[str] = None) -> Optional[KrogerProduct]:
        params = {}
        if location_id:
            params["filter.locationId"] = location_id
        try:
            data = self._authed_get(f"/products/{product_id}", params)
        except KrogerNotFoundError:
            return None

        items = data.get("data")
        if not items:
            return None
        item = items[0] if isinstance(items, list) else items
        return _parse_product(item)

    def close(self) -> None:
        self._http.close()
