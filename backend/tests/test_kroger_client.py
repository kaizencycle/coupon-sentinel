"""
Tests for the Kroger API client (backend/providers/kroger.py).

All HTTP is mocked via httpx.MockTransport — no real network calls, no real
Kroger credentials needed. These verify the OAuth flow, response parsing,
and rate limiter logic against Kroger's documented API shape; they do not
verify behavior against Kroger's live API.
"""

import httpx
import pytest

from backend.providers.kroger import (
    KrogerClient,
    KrogerNotConfiguredError,
    KrogerProduct,
    KrogerRateLimiter,
    KrogerRateLimitError,
)


def _client_with_handler(handler) -> KrogerClient:
    http_client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.kroger.com/v1")
    return KrogerClient(client_id="test-id", client_secret="test-secret", http_client=http_client)


def _token_response() -> httpx.Response:
    return httpx.Response(200, json={"access_token": "tok_abc", "expires_in": 1800})


class TestKrogerRateLimiter:
    def test_allows_up_to_rate_within_window(self):
        limiter = KrogerRateLimiter(rate=3, window_seconds=1.0)
        limiter.acquire(now=0.0)
        limiter.acquire(now=0.1)
        limiter.acquire(now=0.2)
        with pytest.raises(KrogerRateLimitError):
            limiter.acquire(now=0.3)

    def test_window_slides(self):
        limiter = KrogerRateLimiter(rate=2, window_seconds=1.0)
        limiter.acquire(now=0.0)
        limiter.acquire(now=0.1)
        # 1.2s later the first timestamp (0.0) has aged out of the window
        limiter.acquire(now=1.2)


class TestKrogerClientNotConfigured:
    def test_missing_credentials_raises(self):
        client = KrogerClient(client_id=None, client_secret=None)
        with pytest.raises(KrogerNotConfiguredError):
            client.search_products("milk")


class TestKrogerClientOAuth:
    def test_token_is_cached_across_calls(self):
        request_paths = []

        def handler(request: httpx.Request) -> httpx.Response:
            request_paths.append(request.url.path)
            if request.url.path.endswith("/connect/oauth2/token"):
                return _token_response()
            return httpx.Response(200, json={"data": []})

        client = _client_with_handler(handler)
        client.search_products("milk")
        client.search_products("eggs")

        token_requests = [p for p in request_paths if p.endswith("/connect/oauth2/token")]
        assert len(token_requests) == 1


class TestKrogerClientSearch:
    def test_search_parses_products(self):
        sample_response = {
            "data": [
                {
                    "productId": "0001111041195",
                    "upc": "0001111041195",
                    "description": "Kroger Whole Milk",
                    "brand": "Kroger",
                    "items": [{"size": "1 gal", "price": {"regular": 3.49, "promo": 2.99}}],
                    "aisleLocations": [{"locationId": "01400943"}],
                }
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/connect/oauth2/token"):
                return _token_response()
            if request.url.path.endswith("/products"):
                return httpx.Response(200, json=sample_response)
            return httpx.Response(404)

        client = _client_with_handler(handler)
        products = client.search_products("milk")

        assert len(products) == 1
        product = products[0]
        assert isinstance(product, KrogerProduct)
        assert product.product_id == "0001111041195"
        assert product.description == "Kroger Whole Milk"
        assert product.price == 2.99  # promo preferred over regular
        assert product.regular_price == 3.49
        assert product.size == "1 gal"
        assert product.location_id == "01400943"

    def test_search_falls_back_to_regular_price_when_no_promo(self):
        sample_response = {
            "data": [
                {
                    "productId": "id2",
                    "description": "Bread",
                    "items": [{"size": "1 loaf", "price": {"regular": 2.5}}],
                }
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/connect/oauth2/token"):
                return _token_response()
            return httpx.Response(200, json=sample_response)

        client = _client_with_handler(handler)
        products = client.search_products("bread")

        assert products[0].price == 2.5
        assert products[0].promo_price is None


class TestKrogerClientGetProduct:
    def test_get_product_not_found_returns_none(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/connect/oauth2/token"):
                return _token_response()
            return httpx.Response(200, json={"data": []})

        client = _client_with_handler(handler)
        assert client.get_product("nonexistent") is None

    def test_get_product_real_404_returns_none_not_502(self):
        """Kroger's actual not-found response is an HTTP 404, not a 200 with
        empty data — this must resolve the same way (None), not surface as a
        generic upstream error."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/connect/oauth2/token"):
                return _token_response()
            return httpx.Response(404, json={"errors": {"reason": "product not found"}})

        client = _client_with_handler(handler)
        assert client.get_product("nonexistent") is None

    def test_get_product_raises_on_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/connect/oauth2/token"):
                return _token_response()
            return httpx.Response(500, json={"error": "server_error"})

        client = _client_with_handler(handler)
        with pytest.raises(httpx.HTTPStatusError):
            client.get_product("0001111041195")

    def test_oauth_failure_propagates(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "invalid_client"})

        client = _client_with_handler(handler)
        with pytest.raises(httpx.HTTPStatusError):
            client.search_products("milk")
