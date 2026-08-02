import pytest
from app.models.user import UserProfile

pytestmark = pytest.mark.integration


@pytest.mark.integration
class TestAuth:
    """Auth API tests."""

    def test_register_success(self, client):
        """User registration succeeds with valid data."""
        response = client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "password": "X9kLm4PqR7vT2wN5!",
            "display_name": "New User",
            "role": "viewer",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "new@test.com"
        assert data["display_name"] == "New User"
        assert data["role"] == "viewer"
        assert "password_hash" not in data

    def test_register_role_escalation_prevention(self, client):
        """Registration forces viewer role regardless of input."""
        # Attempt to register as admin
        response = client.post("/api/v1/auth/register", json={
            "email": "admin_attempt@test.com",
            "password": "X9kLm4PqR7vT2wN5!",
            "display_name": "Attempted Admin",
            "role": "admin",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "viewer"

        # Attempt to register as editor
        response = client.post("/api/v1/auth/register", json={
            "email": "editor_attempt@test.com",
            "password": "X9kLm4PqR7vT2wN5!",
            "display_name": "Attempted Editor",
            "role": "editor",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "viewer"

    def test_register_duplicate_email(self, client, admin_user):
        """Duplicate email registration is rejected."""
        response = client.post("/api/v1/auth/register", json={
            "email": "admin@test.com",
            "password": "X9kLm4PqR7vT2wN5!",
            "display_name": "Duplicate",
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_login_success(self, client, admin_user):
        """Login succeeds with valid credentials."""
        response = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        # P0-5: refresh_token is now httpOnly cookie only, not in JSON body
        assert data["user"]["email"] == "admin@test.com"

    def test_login_wrong_password(self, client, admin_user):
        """Wrong password returns 401."""
        response = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Non-existent user returns 401."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "password123",
        })
        assert response.status_code == 401

    def test_get_me_success(self, client, admin_user, admin_token):
        """Get current user info."""
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    def test_get_me_no_token(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        """Invalid token returns 401."""
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid_token_here"
        })
        assert response.status_code == 401

    def test_login_persists_audit_log_and_last_login(self, client, admin_user, db):
        """Login audit log and last_login_at must be persisted (ADR-013)."""
        from app.models.audit import AuditLog

        response = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123",
        })
        assert response.status_code == 200

        logs = db.query(AuditLog).filter(AuditLog.action == "user_login").all()
        assert len(logs) == 1
        assert logs[0].resource_type == "user"

        db.expire_all()
        user = db.query(UserProfile).filter(UserProfile.email == "admin@test.com").first()
        assert user.last_login_at is not None

    def test_refresh_without_body_uses_cookie(self, client, admin_user):
        """Refresh must work with httpOnly cookie alone, without a JSON body."""
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123",
        })
        assert login.status_code == 200

        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_logout_without_body_uses_cookie(self, client, admin_user):
        """Logout must work with httpOnly cookie alone, without a JSON body."""
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123",
        })
        assert login.status_code == 200

        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
