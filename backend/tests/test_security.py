import pytest

pytestmark = pytest.mark.integration

"""安全测试 - 注册角色越权漏洞测试"""
import pytest
from app.models.user import UserProfile
from app.core.security import create_access_token


@pytest.mark.security
class TestRegistrationSecurity:
    """注册安全测试"""

    def test_registration_role_escalation(self, client, db):
        """测试注册端点是否强制使用viewer角色，防止角色越权"""

        # 尝试注册一个admin角色用户
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "StrongPassword123!",
                "display_name": "Test User",
                "role": "admin"  # 尝试越权
            }
        )

        # 验证响应 - 应该成功（200）因为密码强度验证通过
        assert response.status_code == 200

        # 验证创建的用户角色是viewer，而不是admin
        user_data = response.json()
        assert user_data["role"] == "viewer"

        # 验证数据库中的用户角色
        user = db.query(UserProfile).filter(UserProfile.email == "test@example.com").first()
        assert user is not None
        assert user.role == "viewer"  # 应该被强制设置为viewer

    def test_registration_editor_role_escalation(self, client):
        """测试注册端点是否阻止editor角色越权"""

        # 尝试注册一个editor角色用户
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test2@example.com",
                "password": "StrongPassword123!",
                "display_name": "Test User 2",
                "role": "editor"  # 尝试越权
            }
        )

        # 验证响应
        assert response.status_code == 200

        # 验证创建的用户角色是viewer，而不是editor
        user_data = response.json()
        assert user_data["role"] == "viewer"

    def test_registration_valid_role(self, client):
        """测试正常注册流程（不指定角色）"""

        # 正常注册，不指定角色
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test3@example.com",
                "password": "StrongPassword123!",
                "display_name": "Test User 3"
            }
        )

        # 验证响应
        assert response.status_code == 200

        # 验证用户角色默认为viewer
        user_data = response.json()
        assert user_data["role"] == "viewer"




@pytest.mark.security
class TestTokenRevocationAndDisabledUser:
    """令牌撤销和禁用用户安全测试"""

    def test_disabled_user_cannot_access_api(self, client, disabled_user_token):
        """测试被禁用的用户不能通过API认证"""
        response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {disabled_user_token}"},
        )
        assert response.status_code == 401

    def test_disabled_user_cannot_login(self, client, disabled_user):
        """测试被禁用的用户不能登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": disabled_user.email, "password": "disabled123"},
        )
        assert response.status_code == 400
        assert "inactive" in response.text.lower()

    def test_password_reset_revokes_tokens(self, client, admin_token, viewer_user):
        """测试密码重置后旧令牌失效"""
        # 先获取旧token
        old_token = create_access_token({"sub": viewer_user.id, "ver": viewer_user.token_version})
        
        # 管理员重置密码
        response = client.post(
            f"/api/v1/users/{viewer_user.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert "temporary_password" in data
        
        # 旧token应该失效（因为token_version已递增）
        response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert response.status_code == 401


@pytest.mark.security
class TestExceptionHandling:
    """异常处理安全测试"""

    def test_invalid_json_returns_422(self, client):
        """测试无效JSON格式返回422"""
        response = client.post(
            "/api/v1/auth/login",
            data="not-json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_malformed_token_returns_401(self, client):
        """测试畸形token返回401"""
        response = client.get(
            "/api/v1/products",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code == 401

    def test_empty_token_returns_401(self, client):
        """测试空token返回401"""
        response = client.get(
            "/api/v1/products",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401

    def test_wrong_token_type_returns_401(self, client, viewer_user):
        """测试使用refresh token访问API返回401"""
        from app.core.security import create_refresh_token
        refresh_token = create_refresh_token({"sub": viewer_user.id})
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == 401


@pytest.mark.security
class TestAuthenticationEdgeCases:
    """认证边界情况测试"""

    def test_xss_injection_in_login(self, client):
        """测试登录端点的XSS注入防护"""
        xss_payload = '<script>alert("xss")</script>'
        response = client.post(
            "/api/v1/auth/login",
            json={"email": xss_payload, "password": "test123"},
        )
        # 应该返回401（无效凭证），而不是执行脚本
        assert response.status_code == 401

    def test_sql_injection_in_login(self, client):
        """测试登录端点的SQL注入防护"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "' OR 1=1 --", "password": "' OR '1'='1"},
        )
        # 应该返回401，而不是成功
        assert response.status_code == 401

    def test_no_auth_token_returns_401(self, client):
        """测试未提供token返回401"""
        response = client.get("/api/v1/products")
        assert response.status_code == 401

    def test_no_auth_token_for_public_returns_200(self, client):
        """测试公开端点无需认证"""
        response = client.get("/health")
        assert response.status_code == 200
