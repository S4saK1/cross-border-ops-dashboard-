import pytest
from app.models.user import UserProfile

pytestmark = pytest.mark.integration


@pytest.mark.integration
class TestUsers:

    def test_list_users_admin(self, client, admin_token):
        """Admin can list users."""
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    def test_list_users_viewer_forbidden(self, client, viewer_token):
        """Viewer cannot list users."""
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 403

    def test_get_user_by_id_admin(self, client, admin_token, editor_user):
        """Admin can get any user by ID."""
        response = client.get(
            f"/api/v1/users/{editor_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "editor@test.com"
        assert data["role"] == "editor"

    def test_get_user_by_id_self(self, client, viewer_token, viewer_user):
        """User can view own profile via users endpoint."""
        response = client.get(
            f"/api/v1/users/{viewer_user.id}",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "viewer@test.com"

    def test_get_user_not_found(self, client, admin_token):
        """Non-existent user returns 404."""
        response = client.get(
            "/api/v1/users/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404

    def test_update_user_role_admin(self, client, admin_token, viewer_user):
        """Admin can update user role."""
        response = client.put(
            f"/api/v1/users/{viewer_user.id}/role",
            params={"role": "editor"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    def test_update_user_role_invalid_role(self, client, admin_token, viewer_user):
        """Invalid role returns 400."""
        response = client.put(
            f"/api/v1/users/{viewer_user.id}/role",
            params={"role": "invalid_role"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400

    # ── P1 supplementary tests (M4) ──

    def test_admin_cannot_demote_self(self, client, admin_token, admin_user):
        """Admin cannot change own role to non-admin."""
        response = client.put(
            f"/api/v1/users/{admin_user.id}/role",
            params={"role": "viewer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

    def test_get_self_via_me(self, client, admin_token, admin_user):
        """User can get own profile via /users/me."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    def test_create_user_admin(self, client, admin_token):
        """Admin can create a new user."""
        response = client.post(
            "/api/v1/users",
            json={"email": "newuser@test.com", "password": "Str0ng!Pass1", "display_name": "New User", "role": "viewer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"

    def test_create_user_duplicate_email(self, client, admin_token, viewer_user):
        """Cannot create user with existing email."""
        response = client.post(
            "/api/v1/users",
            json={"email": "viewer@test.com", "password": "Str0ng!Pass1", "display_name": "Dup", "role": "viewer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 409

    def test_create_user_editor_forbidden(self, client, editor_token):
        """Non-admin cannot create users."""
        response = client.post(
            "/api/v1/users",
            json={"email": "bad@test.com", "password": "Str0ng!Pass1", "display_name": "Bad", "role": "viewer"},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 403

    def test_get_user_viewer_cannot_see_others(self, client, viewer_token, admin_user):
        """Viewer cannot see other user's data (returns 404 to prevent enumeration)."""
        response = client.get(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 404

    def test_update_user_admin(self, client, admin_token, viewer_user):
        """Admin can update user profile."""
        response = client.put(
            f"/api/v1/users/{viewer_user.id}",
            json={"display_name": "Updated Viewer", "role": "editor"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    def test_update_user_not_found(self, client, admin_token):
        """Update non-existent user returns 404."""
        response = client.put(
            "/api/v1/users/nonexistent-id",
            json={"display_name": "Ghost"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    def test_delete_user_admin(self, client, admin_token, viewer_user):
        """Admin can soft-delete a user."""
        response = client.delete(
            f"/api/v1/users/{viewer_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    def test_delete_self_forbidden(self, client, admin_token, admin_user):
        """Admin cannot delete themselves."""
        response = client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code in (400, 403, 409)  # blocked by API