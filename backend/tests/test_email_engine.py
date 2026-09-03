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
        monkeypatch.setattr(email_engine, "EMAIL_FROM", "verified@example.com")

        calls = []

        class _FakeResponse:
            def raise_for_status(self):
                pass

        def _fake_post(url, **kwargs):
            calls.append((url, kwargs))
            return _FakeResponse()

        monkeypatch.setattr(email_engine.httpx, "post", _fake_post)

        result = email_engine.send_email("user@example.com", "Subject", "<p>Body</p>")
        assert result == {"status": "sent"}
        assert calls[0][0] == "https://api.sendgrid.com/v3/mail/send"
        assert calls[0][1]["json"]["from"] == {"email": "verified@example.com"}

    def test_sendgrid_without_email_from_raises_503_not_resend_address(self, monkeypatch):
        """A SendGrid account can't authenticate mail from Resend's sandbox
        address — this must fail loudly, never silently send from a bogus
        sender that SendGrid will just reject."""
        monkeypatch.setattr(email_engine, "RESEND_API_KEY", None)
        monkeypatch.setattr(email_engine, "SENDGRID_API_KEY", "sg_test")
        monkeypatch.setattr(email_engine, "EMAIL_FROM", None)

        def _fail_if_called(url, **kwargs):
            raise AssertionError("should not have called out to SendGrid without a valid sender")

        monkeypatch.setattr(email_engine.httpx, "post", _fail_if_called)

        with pytest.raises(HTTPException) as exc_info:
            email_engine.send_email("user@example.com", "Subject", "<p>Body</p>")
        assert exc_info.value.status_code == 503

    def test_resend_uses_sandbox_sender_when_email_from_unset(self, monkeypatch):
        monkeypatch.setattr(email_engine, "RESEND_API_KEY", "re_test")
        monkeypatch.setattr(email_engine, "SENDGRID_API_KEY", None)
        monkeypatch.setattr(email_engine, "EMAIL_FROM", None)

        calls = []

        class _FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"id": "email_123"}

        def _fake_post(url, **kwargs):
            calls.append((url, kwargs))
            return _FakeResponse()

        monkeypatch.setattr(email_engine.httpx, "post", _fake_post)

        email_engine.send_email("user@example.com", "Subject", "<p>Body</p>")
        assert calls[0][1]["json"]["from"] == "onboarding@resend.dev"
