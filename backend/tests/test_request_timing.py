"""Test for the request-timing middleware (backend/app.py:log_request_timing)."""

import logging


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
