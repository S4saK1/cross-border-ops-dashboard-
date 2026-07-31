import pytest
pytestmark = [pytest.mark.integration, pytest.mark.security]
"""认证模块缺失功能测试"""
import pytest


class TestAuthMissingEndpoints:
    """认证模块 API 端点测试"""

    def test_logout_all_endpoint(self, client, admin_user, admin_token):
        """测试登出所有设备端点"""
        response = client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_password_requirements_endpoint(self, client):
        """测试密码要求端点"""
        response = client.get("/api/v1/auth/password-requirements")
        assert response.status_code == 200
        data = response.json()
        # Should contain password requirements info
        assert isinstance(data, dict)

    def test_check_password_strength_endpoint(self, client):
        """测试密码强度检查端点"""
        # 测试强密码
        response = client.post(
            "/api/v1/auth/check-password-strength",
            json={"password": "StrongPass123!"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

        # 测试弱密码
        response = client.post(
            "/api/v1/auth/check-password-strength",
            json={"password": "123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
