"""Tests for /api/kroger routes — Kroger client is faked out at the FastAPI
dependency level (get_kroger_client), same shape as the real client's public
methods, so no HTTP or credentials are involved."""

import pytest

from backend.app import app
from backend.db_models import PriceObservationRecord
from backend.kroger_routes import get_kroger_client
from backend.providers.kroger import KrogerNotConfiguredError, KrogerProduct


class _FakeKrogerClient:
    def __init__(self, products=None, raise_error=None):
        self._products = products or []
        self._raise_error = raise_error

    def search_products(self, term, location_id=None, limit=10):
        if self._raise_error:
            raise self._raise_error
        return self._products

    def get_product(self, product_id, location_id=None):
        if self._raise_error:
            raise self._raise_error
        for product in self._products:
            if product.product_id == product_id:
                return product
        return None


@pytest.fixture(autouse=True)
def _reset_kroger_override():
    yield
    app.dependency_overrides.pop(get_kroger_client, None)


class TestKrogerSearchEndpoint:
    def test_search_without_credentials_returns_503(self, db_client):
        client, _ = db_client
        app.dependency_overrides[get_kroger_client] = lambda: _FakeKrogerClient(
            raise_error=KrogerNotConfiguredError("Kroger API is not configured")
        )

        response = client.get("/api/kroger/search", params={"query": "milk"})
        assert response.status_code == 503

    def test_search_requires_query_param(self, db_client):
        client, _ = db_client
        response = client.get("/api/kroger/search")
        assert response.status_code == 422

    def test_search_returns_products_and_persists_observations(self, db_client):
        client, session_factory = db_client
        fake_product = KrogerProduct(
            product_id="0001111041195",
            description="Kroger Whole Milk",
            price=2.99,
            regular_price=3.49,
            size="1 gal",
        )
        app.dependency_overrides[get_kroger_client] = lambda: _FakeKrogerClient(products=[fake_product])

        response = client.get("/api/kroger/search", params={"query": "milk"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["source"] == "kroger_api"
        assert data["products"][0]["product_id"] == "0001111041195"
        assert data["products"][0]["price"] == 2.99

        db = session_factory()
        records = db.query(PriceObservationRecord).filter_by(product_id="0001111041195").all()
        assert len(records) == 1
        assert records[0].source == "kroger_api"
        assert float(records[0].price) == 2.99
        assert float(records[0].confidence) == 0.95
        db.close()


class TestKrogerProductEndpoint:
    def test_get_product_not_found_returns_404(self, db_client):
        client, _ = db_client
        app.dependency_overrides[get_kroger_client] = lambda: _FakeKrogerClient(products=[])

        response = client.get("/api/kroger/products/unknown")
        assert response.status_code == 404

    def test_get_product_found(self, db_client):
        client, _ = db_client
        fake_product = KrogerProduct(product_id="abc123", description="Eggs", price=4.29)
        app.dependency_overrides[get_kroger_client] = lambda: _FakeKrogerClient(products=[fake_product])

        response = client.get("/api/kroger/products/abc123")
        assert response.status_code == 200
        assert response.json()["product"]["description"] == "Eggs"
