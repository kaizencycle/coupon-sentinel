"""Tests for JWT authentication (register / login / refresh / current user)."""


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
