"""Tests for backend/monitoring.py — no real Sentry project, sentry_sdk.init is mocked."""

import logging

import sentry_sdk

from backend import monitoring


class TestConfigureLogging:
    def test_respects_log_level_env_var(self, monkeypatch):
        """LOG_LEVEL is declared in render.yaml/docker-compose.yml but was
        never actually wired to Python logging until this milestone — this
        is the regression guard for that."""
        monkeypatch.setattr(monitoring, "LOG_LEVEL", "WARNING")
        monkeypatch.setattr(logging.root, "handlers", [])

        monitoring.configure_logging()

        assert logging.root.level == logging.WARNING

    def test_defaults_to_info(self, monkeypatch):
        monkeypatch.setattr(monitoring, "LOG_LEVEL", "INFO")
        monkeypatch.setattr(logging.root, "handlers", [])

        monitoring.configure_logging()

        assert logging.root.level == logging.INFO


class TestInitMonitoring:
    def test_noop_without_dsn(self, monkeypatch):
        monkeypatch.setattr(monitoring, "SENTRY_DSN", None)

        calls = []
        monkeypatch.setattr(sentry_sdk, "init", lambda **kw: calls.append(kw))

        monitoring.init_monitoring()

        assert calls == []

    def test_initializes_sentry_when_dsn_set(self, monkeypatch):
        monkeypatch.setattr(monitoring, "SENTRY_DSN", "https://example@o0.ingest.sentry.io/0")
        monkeypatch.setattr(monitoring, "ENVIRONMENT", "production")

        calls = []
        monkeypatch.setattr(sentry_sdk, "init", lambda **kw: calls.append(kw))

        monitoring.init_monitoring()

        assert len(calls) == 1
        assert calls[0]["dsn"] == "https://example@o0.ingest.sentry.io/0"
        assert calls[0]["environment"] == "production"
