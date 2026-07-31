"""
Permission matrix tests (RBAC regression).

Validates that each role has exactly the access it should:
- viewer: read-only on products/terms, can view own profile
- editor: can create/update products & terms, cannot manage users
- reviewer: can export, view audit logs
- admin: full access including user management
"""
import pytest
from app.models.role import Role


@pytest.mark.integration
class TestPermissionMatrix:
    """RBAC permission matrix across all roles"""

    # ── Product endpoints ──

    def test_viewer_can_list_products(self, client, viewer_token):
        r = client.get("/api/v1/products", headers={"Authorization": f"Bearer {viewer_token}"})
        assert r.status_code == 200

    def test_viewer_cannot_create_product(self, client, viewer_token):
        r = client.post("/api/v1/products", json={
            "sku": "SKU-001", "product_name_zh": "test", "product_name_en": "test",
            "category": "test", "brand": "test"
        }, headers={"Authorization": f"Bearer {viewer_token}"})
        assert r.status_code == 403

    def test_editor_can_create_product(self, client, editor_token):
        r = client.post("/api/v1/products", json={
            "sku": "SKU-002", "product_name_zh": "test", "product_name_en": "test",
            "category": "test", "brand": "test"
        }, headers={"Authorization": f"Bearer {editor_token}"})
        assert r.status_code == 201

    def test_editor_cannot_delete_product(self, client, editor_token, sample_product):
        r = client.delete(f"/api/v1/products/{sample_product.id}",
                          headers={"Authorization": f"Bearer {editor_token}"})
        assert r.status_code == 403

    def test_admin_can_delete_product(self, client, admin_token, sample_product):
        r = client.delete(f"/api/v1/products/{sample_product.id}",
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200

    # ── User management endpoints ──

    def test_editor_cannot_list_users(self, client, editor_token):
        r = client.get("/api/v1/users", headers={"Authorization": f"Bearer {editor_token}"})
        assert r.status_code == 403

    def test_admin_can_list_users(self, client, admin_token):
        r = client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200

    def test_admin_can_reset_password(self, client, admin_token, viewer_user):
        r = client.post(f"/api/v1/users/{viewer_user.id}/reset-password",
                        json={}, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert "temporary_password" in r.json()

    def test_editor_cannot_reset_password(self, client, editor_token, viewer_user):
        r = client.post(f"/api/v1/users/{viewer_user.id}/reset-password",
                        json={}, headers={"Authorization": f"Bearer {editor_token}"})
        assert r.status_code == 403

    # ── Export endpoints ──

    def test_viewer_cannot_export(self, client, viewer_token, sample_product):
        r = client.post("/api/v1/export/csv", json={
            "platform": "amazon", "product_ids": [sample_product.id]
        }, headers={"Authorization": f"Bearer {viewer_token}"})
        assert r.status_code == 403

    def test_reviewer_can_export(self, client, reviewer_token, sample_product):
        """Reviewer can access export endpoint."""
        r = client.post("/api/v1/export/csv", json={
            "platform": "amazon", "product_ids": [sample_product.id]
        }, headers={"Authorization": f"Bearer {reviewer_token}"})
        assert r.status_code == 200, f"Expected 200 for clean product export, got {r.status_code}: {r.text}"

    # ── Import endpoints ──

    def test_viewer_cannot_import(self, client, viewer_token):
        r = client.post("/api/v1/import/preview",
                        json={"file_id": "nonexistent"},
                        headers={"Authorization": f"Bearer {viewer_token}"})
        assert r.status_code in (403, 404)

    def test_editor_can_access_import(self, client, editor_token):
        """Editor can access import preview."""
        r = client.post("/api/v1/import/preview?file_id=nonexistent",
                        headers={"Authorization": f"Bearer {editor_token}"})
        assert r.status_code == 404

    # ── Audit endpoints ──

    def test_viewer_cannot_access_audit(self, client, viewer_token):
        r = client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {viewer_token}"})
        assert r.status_code == 403

    def test_admin_can_access_audit(self, client, admin_token):
        r = client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200

    # ── Self-profile access ──

    def test_viewer_can_get_own_profile(self, client, viewer_token):
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {viewer_token}"})
        assert r.status_code == 200

    def test_viewer_cannot_get_other_user(self, client, viewer_token, admin_user):
        r = client.get(f"/api/v1/users/{admin_user.id}",
                       headers={"Authorization": f"Bearer {viewer_token}"})
        assert r.status_code == 404  # not found (prevents enumeration)


@pytest.mark.integration
class TestCSRFProtection:
    """CSRF middleware tests"""

    def test_get_requests_pass_csrf(self, client):
        """GET requests should bypass CSRF check"""
        r = client.get("/health")
        assert r.status_code == 200

    def test_post_without_origin_passes(self, client, admin_token):
        """Server-to-server calls (no Origin) should pass"""
        r = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        })
        assert r.status_code == 200

    def test_post_with_wrong_origin_blocked(self, client, admin_token):
        """Cross-origin POST with wrong Origin should be blocked"""
        r = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }, headers={"Origin": "https://evil.com"})
        assert r.status_code == 403

    def test_post_with_allowed_origin_passes(self, client, admin_token):
        """POST with allowed Origin should pass"""
        r = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }, headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 200

    def test_delete_with_wrong_origin_blocked(self, client, admin_token, sample_product):
        """DELETE with wrong Origin should be blocked"""
        r = client.delete(f"/api/v1/products/{sample_product.id}",
                          headers={
                              "Authorization": f"Bearer {admin_token}",
                              "Origin": "https://evil.com"
                          })
        assert r.status_code == 403


@pytest.mark.integration
class TestTokenLifecycle:
    """Token refresh, logout, and revocation lifecycle tests"""

    def test_login_returns_both_tokens(self, client, admin_user):
        r = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_works(self, client, admin_user):
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        })
        refresh = login.json()["refresh_token"]
        r = client.post("/api/v1/auth/refresh", json={"token": refresh})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_refresh_with_access_token_fails(self, client, admin_user):
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        })
        access = login.json()["access_token"]
        r = client.post("/api/v1/auth/refresh", json={"token": access})
        assert r.status_code == 401

    def test_logout_invalidates_refresh(self, client, admin_user):
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        })
        refresh = login.json()["refresh_token"]
        r = client.post("/api/v1/auth/logout", json={"token": refresh})
        assert r.status_code == 200
        # Using same refresh should now fail
        r2 = client.post("/api/v1/auth/refresh", json={"token": refresh})
        assert r2.status_code == 401

    def test_password_reset_revokes_all_tokens(self, client, admin_token, viewer_user):
        # Login as viewer
        login = client.post("/api/v1/auth/login", json={
            "email": "viewer@test.com", "password": "viewer123"
        })
        old_access = login.json()["access_token"]
        # Admin resets viewer's password
        r = client.post(f"/api/v1/users/{viewer_user.id}/reset-password",
                        json={}, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        # Old access token should be invalid
        r2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_access}"})
        assert r2.status_code == 401
