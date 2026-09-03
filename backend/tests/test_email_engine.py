"""Tests for backend/engines/email_engine.py — no real network calls, httpx.post is mocked."""

import pytest
from fastapi import HTTPException

from backend.engines import email_engine


class TestEmailProviderConfigured:
    def test_false_when_neither_key_set(self, monkeypatch):
        monkeypatch.setattr(email_engine, "RESEND_API_KEY", None)
        monkeypatch.setattr(email_engine, "SENDGRID_API_KEY", None)
        assert email_engine.email_provider_configured() is False

    def test_true_when_resend_key_set(self, monkeypatch):
        monkeypatch.setattr(email_engine, "RESEND_API_KEY", "re_test")
        monkeypatch.setattr(email_engine, "SENDGRID_API_KEY", None)
        assert email_engine.email_provider_configured() is True


class TestSendEmail:
    def test_raises_503_when_not_configured(self, monkeypatch):
        monkeypatch.setattr(email_engine, "RESEND_API_KEY", None)
        monkeypatch.setattr(email_engine, "SENDGRID_API_KEY", None)

        with pytest.raises(HTTPException) as exc_info:
            email_engine.send_email("user@example.com", "Subject", "<p>Body</p>")
        assert exc_info.value.status_code == 503

    def test_prefers_resend_when_both_configured(self, monkeypatch):
        monkeypatch.setattr(email_engine, "RESEND_API_KEY", "re_test")
        monkeypatch.setattr(email_engine, "SENDGRID_API_KEY", "sg_test")

        calls = []

        class _FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"id": "email_123"}

        def _fake_post(url, **kwargs):
            calls.append(url)
            return _FakeResponse()

        monkeypatch.setattr(email_engine.httpx, "post", _fake_post)

        result = email_engine.send_email("user@example.com", "Subject", "<p>Body</p>")
        assert result == {"id": "email_123"}
        assert calls == ["https://api.resend.com/emails"]

    def test_falls_back_to_sendgrid(self, monkeypatch):
        monkeypatch.setattr(email_engine, "RESEND_API_KEY", None)
        monkeypatch.setattr(email_engine, "SENDGRID_API_KEY", "sg_test")

        calls = []

        class _FakeResponse:
            def raise_for_status(self):
                pass

        def _fake_post(url, **kwargs):
            calls.append(url)
            return _FakeResponse()

        monkeypatch.setattr(email_engine.httpx, "post", _fake_post)

        result = email_engine.send_email("user@example.com", "Subject", "<p>Body</p>")
        assert result == {"status": "sent"}
        assert calls == ["https://api.sendgrid.com/v3/mail/send"]
