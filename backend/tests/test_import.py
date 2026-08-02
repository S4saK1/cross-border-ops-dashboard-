import pytest

pytestmark = pytest.mark.integration

import csv
import io
import os
import tempfile
import pytest


@pytest.mark.integration
class TestImport:

    def test_upload_csv(self, client, editor_token):
        #              CSV
        csv_content = "SKU,            ,            ,      ,      \nIMPORT-001,            ,Test Product,           ?      \nIMPORT-002,            2,Test Product 2,           ?      "

        #       BytesIO                        
        csv_bytes = csv_content.encode("utf-8")
        response = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert data["total_rows"] == 2
        assert len(data["headers"]) == 5

    def test_upload_invalid_format(self, client, editor_token):
        content = b"test content"
        response = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 400

    def test_upload_legacy_xls_rejected(self, client, editor_token):
        """Legacy .xls is not supported by openpyxl; reject at extension check."""
        content = b"dummy xls content"
        response = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.xls", io.BytesIO(content), "application/vnd.ms-excel")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    def test_preview_import(self, client, editor_token):
        # Verify
        csv_content = "SKU,product_name_zh,product_name_en,category\nPREVIEW-001,Preview ZH,Preview EN,General"
        csv_bytes = csv_content.encode("utf-8")

        upload_response = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        file_id = upload_response.json()["file_id"]

        #       
        response = client.post(
            f"/api/v1/import/preview?file_id={file_id}",
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_rows" in data
        assert "can_proceed" in data

    def test_execute_import_create(self, client, editor_token):
        csv_content = "SKU,product_name_zh,product_name_en,category,price\nEXEC-001,Exec ZH,Import Product,General,9.99"
        csv_bytes = csv_content.encode("utf-8")

        upload_response = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        file_id = upload_response.json()["file_id"]

        #             
        response = client.post(
            f"/api/v1/import/execute?file_id={file_id}&mode=create",
            json={
                "SKU": "sku",
                "product_name_zh": "product_name_zh",
                "product_name_en": "product_name_en",
                "category": "category",
                "price": "price",
            },
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["error_count"] == 0

        # Verify product was created
        list_response = client.get(
            "/api/v1/products?search=EXEC-001",
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

    def test_execute_import_duplicate_sku(self, client, editor_token):
        csv_content = "SKU,product_name_zh,product_name_en,category\nDUP-001,Dup ZH,Dup EN,General"
        csv_bytes = csv_content.encode("utf-8")

        upload_response = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        file_id = upload_response.json()["file_id"]

        # Execute import
        client.post(
            f"/api/v1/import/execute?file_id={file_id}&mode=create",
            json={"SKU": "sku", "product_name_zh": "product_name_zh", "product_name_en": "product_name_en", "category": "category"},
            headers={"Authorization": f"Bearer {editor_token}"},
        )

        # Verify
        upload2 = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )

        # Verify
        response = client.post(
            f"/api/v1/import/execute?file_id={upload2.json()['file_id']}&mode=create",
            json={"SKU": "sku", "product_name_zh": "product_name_zh", "product_name_en": "product_name_en", "category": "category"},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skip_count"] == 1

    def test_import_viewer_forbidden(self, client, viewer_token):
        response = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.csv", io.BytesIO(b"test"), "text/csv")},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_upload_empty_csv(self, client, editor_token):
        """Upload empty CSV returns appropriate response."""
        csv_bytes = "SKU,product_name_zh\n".encode("utf-8")
        response = client.post(
            "/api/v1/import/upload",
            files={"file": ("empty.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code in (200, 400)

    def test_execute_import_unauthorized(self, client):
        """Execute import without auth returns 401."""
        response = client.post("/api/v1/import/execute?file_id=nonexistent&mode=create", json={})
        assert response.status_code == 401

    def test_execute_import_viewer_forbidden(self, client, viewer_token):
        """Viewer cannot execute import."""
        response = client.post(
            "/api/v1/import/execute?file_id=nonexistent&mode=create",
            json={},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_execute_import_invalid_file_id(self, client, editor_token):
        """Execute with invalid file_id returns 404."""
        response = client.post(
            "/api/v1/import/execute?file_id=nonexistent-id&mode=create",
            json={"SKU": "sku"},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 404

    def test_execute_import_update_mode(self, client, editor_token):
        """Execute import in update mode on non-existing SKU creates it."""
        csv_content = "SKU,product_name_zh,product_name_en,category\nUPD-001,Update ZH,Update EN,General"
        csv_bytes = csv_content.encode("utf-8")
        upload_response = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        file_id = upload_response.json()["file_id"]
        response = client.post(
            f"/api/v1/import/execute?file_id={file_id}&mode=update",
            json={"SKU": "sku", "product_name_zh": "product_name_zh", "product_name_en": "product_name_en", "category": "category"},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success_count"] == 1

    def test_execute_import_xlsx_over_100_rows(self, client, editor_token):
        """Excel files larger than the 100-row preview cache must import fully."""
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["SKU", "product_name_zh", "product_name_en", "category"])
        for i in range(1, 151):
            ws.append([f"XLSX-{i:03d}", f"产品{i}", f"Product {i}", "General"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        upload_response = client.post(
            "/api/v1/import/upload",
            files={"file": ("products.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["total_rows"] == 150

        response = client.post(
            f"/api/v1/import/execute?file_id={upload_data['file_id']}&mode=create",
            json={
                "SKU": "sku",
                "product_name_zh": "product_name_zh",
                "product_name_en": "product_name_en",
                "category": "category",
            },
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 150
        assert data["error_count"] == 0

        list_response = client.get(
            "/api/v1/products?page_size=100",
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 150

    def test_execute_import_writes_audit_log(self, client, editor_token, db):
        """Execute import must write an import_execute audit entry (ADR-013)."""
        from app.models.audit import AuditLog

        csv_content = "SKU,product_name_zh,product_name_en,category\nAUD-IMPORT-001,Audit ZH,Audit EN,General"
        csv_bytes = csv_content.encode("utf-8")
        upload_response = client.post(
            "/api/v1/import/upload",
            files={"file": ("audit.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        file_id = upload_response.json()["file_id"]

        response = client.post(
            f"/api/v1/import/execute?file_id={file_id}&mode=create",
            json={
                "SKU": "sku",
                "product_name_zh": "product_name_zh",
                "product_name_en": "product_name_en",
                "category": "category",
            },
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success_count"] == 1

        logs = db.query(AuditLog).filter(AuditLog.action == "import_execute").all()
        assert len(logs) == 1
        assert logs[0].resource_type == "product"
        details = logs[0].details or {}
        after = details.get("after") or {}
        assert after["mode"] == "create"
        assert after["succeeded"] == 1
        assert after["attempted"] == 1
        assert after["failed"] == 0

    def test_execute_import_duplicate_sku_in_file(self, client, editor_token):
        """Duplicate SKUs inside one file must skip, not crash with a 500."""
        csv_content = (
            "SKU,product_name_zh,product_name_en,category\n"
            "INFILE-001,One ZH,One EN,General\n"
            "INFILE-001,Two ZH,Two EN,General"
        )
        csv_bytes = csv_content.encode("utf-8")
        upload_response = client.post(
            "/api/v1/import/upload",
            files={"file": ("dup.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        file_id = upload_response.json()["file_id"]

        response = client.post(
            f"/api/v1/import/execute?file_id={file_id}&mode=create",
            json={
                "SKU": "sku",
                "product_name_zh": "product_name_zh",
                "product_name_en": "product_name_en",
                "category": "category",
            },
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["skip_count"] == 1
        assert data["error_count"] == 0
