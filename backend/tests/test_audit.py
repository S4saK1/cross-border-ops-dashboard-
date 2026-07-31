import pytest
pytestmark = pytest.mark.integration
"""审计日志 API 测试"""
import pytest
from fastapi.testclient import TestClient


class TestAuditLogs:
    """审计日志端点测试"""

    def test_list_audit_logs_requires_auth(self, client: TestClient):
        """未认证用户无法访问审计日志"""
        res = client.get("/api/v1/audit-logs")
        assert res.status_code == 401

    def test_list_audit_logs_viewer_denied(self, client: TestClient, viewer_token: str):
        """查看者无法访问审计日志"""
        res = client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 403

    def test_list_audit_logs_admin_allowed(self, client: TestClient, admin_token: str):
        """管理员可以访问审计日志"""
        res = client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    def test_create_product_generates_audit_log(
        self, client: TestClient, editor_token: str, db
    ):
        """创建产品应生成审计日志"""
        # 创建产品
        res = client.post(
            "/api/v1/products",
            json={
                "sku": "AUDIT-TEST-001",
                "product_name_zh": "审计测试产品",
                "product_name_en": "Audit Test Product",
                "category": "通用属性",
            },
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert res.status_code == 201

        # 检查审计日志：使用 conftest 注入的 db fixture（测试数据库）
        from app.models.audit import AuditLog

        logs = db.query(AuditLog).filter(AuditLog.action == "create").all()
        assert len(logs) >= 1
        assert logs[-1].resource_type == "product"


class TestAuditLogFiltering:
    """审计日志筛选测试"""

    def test_filter_by_action(self, client: TestClient, admin_token: str):
        """按操作类型筛选"""
        res = client.get(
            "/api/v1/audit-logs?action=create",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200

    def test_pagination(self, client: TestClient, admin_token: str):
        """分页查询"""
        res = client.get(
            "/api/v1/audit-logs?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
