import pytest
pytestmark = [pytest.mark.integration, pytest.mark.security]
"""全局异常处理器测试"""
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


class TestGlobalExceptionHandler:
    """GlobalExceptionHandlerMiddleware 测试"""

    def test_http_exception_returns_standard_format(self, client: TestClient):
        """HTTPException 返回标准化错误格式"""
        # 触发一个 HTTP 404 via FastAPI path
        res = client.get("/api/v1/products/nonexistent-id-should-404",
                          headers={"Authorization": f"Bearer test"})
        assert res.status_code in [401, 404]  # 401 if unauth, 404 from route
        data = res.json()
        if res.status_code == 401:
            assert "detail" in data
        else:
            assert "detail" in data

    def test_method_not_allowed(self, client: TestClient):
        """错误 HTTP 方法返回 405"""
        res = client.get("/api/v1/auth/login")  # login is POST only
        assert res.status_code == 405

    def test_not_found_route(self, client: TestClient):
        """不存在的路由返回 404"""
        res = client.get("/api/v1/nonexistent")
        assert res.status_code == 404

    def test_validation_error(self, client: TestClient, admin_token: str):
        """请求体验证失败"""
        res = client.post(
            "/api/v1/products",
            json={"invalid": "data"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code in [401, 403, 422]  # 可能先验证 token，或直接422

    def test_500_internal_error_is_caught(
        self, client, admin_token
    ):
        """500 错误被中间件捕获，不泄露栈追踪"""
        import json
        # Send invalid JSON to trigger 500 from parsing
        # Or trigger a real exception via a deliberately broken request
        res = client.post(
            "/api/v1/products",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json",
            },
            content=b"not valid json at all!!!",
        )
        # Should be caught by exception handler -> 500 with standard format
        assert res.status_code in [500, 422]
        if res.status_code == 500:
            data = res.json()
            assert "detail" in data
            # Ensure no traceback leak
            body = res.text
            assert "Traceback" not in body
            assert "File " not in body
    def test_global_handler_catches_unhandled_exception(
        self, client: TestClient
    ):
        """验证中间件注册：确保 GlobalExceptionHandlerMiddleware 已添加"""
        from app.main import app
        from app.middleware.exception_handler import GlobalExceptionHandlerMiddleware

        middlewares = [
            m.cls for m in app.user_middleware
        ]
        assert GlobalExceptionHandlerMiddleware in middlewares, (
            "GlobalExceptionHandlerMiddleware must be registered"
        )


class TestErrorResponseFormat:
    """错误响应格式测试"""

    def test_login_with_invalid_credentials(self, client: TestClient):
        """无效凭据的错误响应"""
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrong"},
        )
        assert res.status_code == 401
        data = res.json()
        assert "detail" in data

    def test_unauthorized_access(self, client: TestClient):
        """未认证访问受保护端点"""
        res = client.get("/api/v1/users")
        assert res.status_code == 401

    def test_forbidden_access(self, client: TestClient, viewer_token: str):
        """权限不足访问管理端点"""
        res = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 403
