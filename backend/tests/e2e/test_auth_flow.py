"""认证流程端到端测试"""
import pytest


@pytest.mark.e2e
class TestAuthFlow:
    """认证流程E2E测试"""
    
    def test_complete_auth_flow(self, client):
        """测试完整的认证流程"""
        # 1. 注册用户
        register_response = client.post("/api/v1/auth/register", json={
            "email": "e2e@test.com",
            "password": "E2ETestPass123!",
            "display_name": "E2E测试用户"
        })
        assert register_response.status_code == 200
        user_data = register_response.json()
        assert user_data["email"] == "e2e@test.com"
        assert user_data["role"] == "viewer"
        
        # 2. 登录
        login_response = client.post("/api/v1/auth/login", json={
            "email": "e2e@test.com",
            "password": "E2ETestPass123!"
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data
        
        # 3. 获取用户信息
        me_response = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {login_data['access_token']}"
        })
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == "e2e@test.com"
        
        # 4. 刷新令牌
        refresh_response = client.post("/api/v1/auth/refresh", json={
            "token": login_data["refresh_token"]
        })
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        
        # 5. 登出
        logout_response = client.post("/api/v1/auth/logout", json={
            "token": login_data["refresh_token"]
        }, headers={
            "Authorization": f"Bearer {login_data['access_token']}"
        })
        assert logout_response.status_code == 200
    
    def test_role_escalation_prevention(self, client):
        """测试角色越权防护"""
        # 尝试注册为admin
        response = client.post("/api/v1/auth/register", json={
            "email": "admin_attempt@test.com",
            "password": "E2ETestPass123!",
            "display_name": "试图提权的用户",
            "role": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        
        # 验证角色被强制设为viewer
        assert data["role"] == "viewer"
        
        # 验证无法访问管理员功能
        login_response = client.post("/api/v1/auth/login", json={
            "email": "admin_attempt@test.com",
            "password": "E2ETestPass123!"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 尝试访问管理员功能
        admin_response = client.get("/api/v1/users", headers={
            "Authorization": f"Bearer {token}"
        })
        assert admin_response.status_code == 403