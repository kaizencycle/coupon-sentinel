"""Tests for backend/engines/analytics_engine.py."""

from backend.db_models import AnalyticsEvent
from backend.engines import analytics_engine


class _SyncThread:
    """Stand-in for threading.Thread that runs the target immediately and
    synchronously on .start(), instead of on a real background thread.

    Mixpanel forwarding is deliberately fire-and-forget on a daemon thread
    in production (see track_event) so it can never block the event loop —
    but that makes a real background thread nondeterministic to assert on
    in a test (a race between the thread and the test's own assertions).
    Swapping in this synchronous stand-in for threading.Thread keeps the
    test deterministic while still exercising the real forwarding logic.
    """

    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


class TestTrackEvent:
    def test_persists_to_db_without_mixpanel_configured(self, db_client, monkeypatch):
        _, session_factory = db_client
        monkeypatch.setattr(analytics_engine, "MIXPANEL_TOKEN", None)
        db = session_factory()

        record = analytics_engine.track_event("signup", db, user_id=42, event_data={"plan": "free"})

        assert record.id is not None
        assert record.event_type == "signup"
        assert record.user_id == 42
        assert record.event_data == {"plan": "free"}

        fetched = db.query(AnalyticsEvent).filter_by(id=record.id).one()
        assert fetched.event_type == "signup"
        db.close()

    def test_anonymous_event_has_null_user_id(self, db_client):
        _, session_factory = db_client
        db = session_factory()
        record = analytics_engine.track_event("optimize", db, user_id=None, event_data={"item_count": 3})
        assert record.user_id is None
        db.close()

    def test_forwards_to_mixpanel_when_configured(self, db_client, monkeypatch):
        _, session_factory = db_client
        monkeypatch.setattr(analytics_engine, "MIXPANEL_TOKEN", "mp_test_token")
        monkeypatch.setattr(analytics_engine.threading, "Thread", _SyncThread)
        db = session_factory()

        calls = []

        class _FakeResponse:
            def raise_for_status(self):
                pass

        def _fake_post(url, **kwargs):
            calls.append((url, kwargs))
            return _FakeResponse()

        monkeypatch.setattr(analytics_engine.httpx, "post", _fake_post)

        analytics_engine.track_event("login", db, user_id=7, event_data={})

        assert len(calls) == 1
        url, kwargs = calls[0]
        assert url == "https://api.mixpanel.com/track"
        payload = kwargs["json"][0]
        assert payload["event"] == "login"
        assert payload["properties"]["token"] == "mp_test_token"
        assert payload["properties"]["distinct_id"] == "7"
        db.close()

    def test_mixpanel_forwarding_failure_does_not_raise(self, db_client, monkeypatch):
        """Observability must never break the request that triggered it."""
        _, session_factory = db_client
        monkeypatch.setattr(analytics_engine, "MIXPANEL_TOKEN", "mp_test_token")
        monkeypatch.setattr(analytics_engine.threading, "Thread", _SyncThread)
        db = session_factory()

        def _raise(*args, **kwargs):
            raise analytics_engine.httpx.ConnectError("boom")

        monkeypatch.setattr(analytics_engine.httpx, "post", _raise)

        # Must not raise, and the local DB write must still have happened.
        record = analytics_engine.track_event("login", db, user_id=7, event_data={})
        assert record.id is not None
        db.close()

    def test_anonymous_distinct_id_when_forwarding(self, db_client, monkeypatch):
        _, session_factory = db_client
        monkeypatch.setattr(analytics_engine, "MIXPANEL_TOKEN", "mp_test_token")
        monkeypatch.setattr(analytics_engine.threading, "Thread", _SyncThread)
        db = session_factory()

        calls = []

        class _FakeResponse:
            def raise_for_status(self):
                pass

        monkeypatch.setattr(analytics_engine.httpx, "post", lambda url, **kw: calls.append(kw) or _FakeResponse())

        analytics_engine.track_event("optimize", db, user_id=None, event_data={})
        assert calls[0]["json"][0]["properties"]["distinct_id"] == "anonymous"
        db.close()

    def test_mixpanel_forwarding_does_not_block_the_caller(self, db_client, monkeypatch):
        """track_event() is called synchronously from inside async route
        handlers — a slow Mixpanel response must not stall it (and, in a
        real server, the single event loop serving every other in-flight
        request). Uses a REAL background thread here (not the _SyncThread
        stand-in) specifically to prove it doesn't block."""
        import threading
        import time

        _, session_factory = db_client
        monkeypatch.setattr(analytics_engine, "MIXPANEL_TOKEN", "mp_test_token")
        db = session_factory()

        release = threading.Event()

        class _FakeResponse:
            def raise_for_status(self):
                pass

        def _slow_post(url, **kwargs):
            release.wait(timeout=2)  # blocks until the test releases it
            return _FakeResponse()

        monkeypatch.setattr(analytics_engine.httpx, "post", _slow_post)

        start = time.monotonic()
        analytics_engine.track_event("login", db, user_id=1, event_data={})
        elapsed = time.monotonic() - start

        assert elapsed < 0.5  # returned long before _slow_post's httpx call ever unblocks
        release.set()  # let the background thread finish so it doesn't leak past the test
        db.close()
