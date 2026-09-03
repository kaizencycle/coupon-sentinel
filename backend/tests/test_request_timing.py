"""Test for the request-timing middleware (backend/app.py:log_request_timing)."""

import asyncio
import logging

import pytest

from backend.app import log_request_timing


class TestRequestTimingMiddleware:
    def test_logs_request_method_path_and_status(self, db_client, caplog):
        client, _ = db_client
        with caplog.at_level(logging.INFO, logger="coupon_sentinel.requests"):
            response = client.get("/health")

        assert response.status_code == 200
        matching = [r for r in caplog.records if r.name == "coupon_sentinel.requests"]
        assert len(matching) == 1
        assert "GET" in matching[0].message
        assert "/health" in matching[0].message
        assert "200" in matching[0].message

    def test_logs_before_reraising_when_handler_fails(self, caplog):
        """A handler that raises must still get logged — failed requests,
        slow 500s especially, are exactly what monitoring exists to catch."""

        class _FakeURL:
            path = "/boom"

        class _FakeRequest:
            method = "GET"
            url = _FakeURL()

        async def _raising_call_next(request):
            raise RuntimeError("boom")

        with caplog.at_level(logging.WARNING, logger="coupon_sentinel.requests"):
            with pytest.raises(RuntimeError):
                asyncio.run(log_request_timing(_FakeRequest(), _raising_call_next))

        matching = [r for r in caplog.records if r.name == "coupon_sentinel.requests"]
        assert len(matching) == 1
        assert "FAILED" in matching[0].message
        assert "/boom" in matching[0].message
