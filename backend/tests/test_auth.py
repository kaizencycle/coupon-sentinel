"""Tests for JWT authentication (register / login / refresh / current user)."""

from backend import auth as auth_module


def _register(client, email="user@example.com", password="password123"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


class TestRegister:
    def test_register_returns_tokens(self, db_client):
        client, _ = db_client
        response = _register(client)
        assert response.status_code == 201
        data = response.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email_rejected(self, db_client):
        client, _ = db_client
        _register(client)
        response = _register(client)
        assert response.status_code == 409

    def test_register_rejects_short_password(self, db_client):
        client, _ = db_client
        response = _register(client, password="short")
        assert response.status_code == 422


class TestLogin:
    def test_login_with_correct_credentials(self, db_client):
        client, _ = db_client
        _register(client, email="login@example.com", password="password123")
        response = client.post(
            "/api/auth/login", json={"email": "login@example.com", "password": "password123"}
        )
        assert response.status_code == 200
        assert response.json()["access_token"]

    def test_login_with_wrong_password_rejected(self, db_client):
        client, _ = db_client
        _register(client, email="wrongpw@example.com", password="password123")
        response = client.post(
            "/api/auth/login", json={"email": "wrongpw@example.com", "password": "nope12345"}
        )
        assert response.status_code == 401

    def test_login_unknown_email_rejected(self, db_client):
        client, _ = db_client
        response = client.post(
            "/api/auth/login", json={"email": "ghost@example.com", "password": "password123"}
        )
        assert response.status_code == 401


class TestRefresh:
    def test_refresh_issues_new_tokens(self, db_client):
        client, _ = db_client
        tokens = _register(client, email="refresh@example.com").json()
        response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert response.status_code == 200
        assert response.json()["access_token"]

    def test_refresh_rejects_access_token(self, db_client):
        client, _ = db_client
        tokens = _register(client, email="refresh2@example.com").json()
        response = client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
        assert response.status_code == 401

    def test_refresh_rejects_garbage_token(self, db_client):
        client, _ = db_client
        response = client.post("/api/auth/refresh", json={"refresh_token": "not-a-jwt"})
        assert response.status_code == 401


class TestCurrentUser:
    def test_profile_requires_auth(self, db_client):
        client, _ = db_client
        response = client.get("/api/user/profile")
        assert response.status_code == 401

    def test_profile_rejects_bad_token(self, db_client):
        client, _ = db_client
        response = client.get("/api/user/profile", headers={"Authorization": "Bearer garbage"})
        assert response.status_code == 401

    def test_profile_returns_current_user(self, db_client):
        client, _ = db_client
        tokens = _register(client, email="profile@example.com").json()
        response = client.get(
            "/api/user/profile", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile@example.com"
        assert data["tier"] == "free"


class TestEmailVerification:
    def test_resend_verification_requires_auth(self, db_client):
        client, _ = db_client
        response = client.post("/api/auth/resend-verification")
        assert response.status_code == 401

    def test_resend_verification_without_provider_returns_503(self, db_client):
        # No RESEND_API_KEY/SENDGRID_API_KEY set in the test environment —
        # send_email() itself raises 503, same as Stripe/Kroger when unconfigured.
        client, _ = db_client
        tokens = _register(client, email="noemail@example.com").json()

        response = client.post(
            "/api/auth/resend-verification",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 503

    def test_resend_verification_sends_when_configured(self, db_client, monkeypatch):
        client, _ = db_client
        tokens = _register(client, email="sendme@example.com").json()

        captured = {}

        def _fake_send_email(to, subject, html):
            captured["to"] = to
            captured["subject"] = subject
            captured["html"] = html
            return {"id": "email_123"}

        monkeypatch.setattr(auth_module, "send_email", _fake_send_email)

        response = client.post(
            "/api/auth/resend-verification",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "sent"}
        assert captured["to"] == "sendme@example.com"
        assert "verify-email?token=" in captured["html"]

    def test_resend_verification_short_circuits_if_already_verified(self, db_client):
        client, session_factory = db_client
        tokens = _register(client, email="already@example.com").json()

        db = session_factory()
        from backend.db_models import User

        user = db.query(User).filter_by(email="already@example.com").first()
        user.is_email_verified = True
        db.commit()
        db.close()

        response = client.post(
            "/api/auth/resend-verification",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "already_verified"}

    def test_verify_email_with_valid_token(self, db_client):
        client, session_factory = db_client
        tokens = _register(client, email="verifyme@example.com").json()

        db = session_factory()
        from backend.db_models import User

        user = db.query(User).filter_by(email="verifyme@example.com").first()
        assert user.is_email_verified is False
        token = auth_module.create_email_verification_token(user.id)
        db.close()

        response = client.post("/api/auth/verify-email", json={"token": token})
        assert response.status_code == 200
        assert response.json() == {"status": "verified", "email": "verifyme@example.com"}

        db2 = session_factory()
        refreshed = db2.query(User).filter_by(email="verifyme@example.com").first()
        assert refreshed.is_email_verified is True
        db2.close()

    def test_verify_email_rejects_access_token(self, db_client):
        client, _ = db_client
        tokens = _register(client, email="wrongtype@example.com").json()
        response = client.post("/api/auth/verify-email", json={"token": tokens["access_token"]})
        assert response.status_code == 401

    def test_verify_email_rejects_garbage_token(self, db_client):
        client, _ = db_client
        response = client.post("/api/auth/verify-email", json={"token": "not-a-jwt"})
        assert response.status_code == 401
