import pytest

pytestmark = pytest.mark.integration

import pytest


@pytest.mark.integration
class TestExport:

    def test_export_amazon_csv(self, client, admin_token, sample_product):
        response = client.post("/api/v1/export/csv", json={
            "platform": "amazon",
            "product_ids": [sample_product.id],
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        #      ?CSV       
        content = response.text
        assert "item_type" in content
        assert "item_name" in content
        assert "Test Product" in content
        assert "TEST-001" in content

    def test_export_alibaba_csv(self, client, admin_token, sample_product):
        response = client.post("/api/v1/export/csv", json={
            "platform": "alibaba",
            "product_ids": [sample_product.id],
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        content = response.text
        assert "Subject" in content
        assert "Model Number" in content
        assert "Test Product" in content

    def test_export_invalid_platform(self, client, admin_token, sample_product):
        response = client.post("/api/v1/export/csv", json={
            "platform": "shopee",
            "product_ids": [sample_product.id],
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 400
        assert "Platform must be" in response.json()["detail"]

    def test_export_no_products(self, client, admin_token):
        """Export with empty product_ids returns 404."""
        response = client.post("/api/v1/export/csv", json={
            "platform": "amazon",
            "product_ids": [],
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 404
