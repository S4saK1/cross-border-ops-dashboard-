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

    def test_export_409_cross_product_consistency_block(self, client, admin_token, admin_user, db):
        """Export must return 409 when cross-product colour inconsistency exists.

        Product A uses "Color", Product B uses "Colour" for the same zh term.
        ConsistencyEngine.check_all_products() detects two different en values
        for the same zh_term → ERROR severity → export blocked (409).
        """
        from app.models.product import Product

        p_a = Product(
            sku="CON-001",
            product_name_zh="产品A", product_name_en="Product A",
            category="General", brand="TestBrand",
            color_zh="红色", color_en="Color",
            material_zh="塑料", material_en="Plastic",
            price=9.99, currency="USD", stock=50,
            weight=0.5, weight_unit="kg", origin="China",
            created_by=admin_user.id,
        )
        p_b = Product(
            sku="CON-002",
            product_name_zh="产品B", product_name_en="Product B",
            category="General", brand="TestBrand",
            color_zh="红色", color_en="Colour",       # ← British spelling → cross-product conflict
            material_zh="塑料", material_en="Plastic",
            price=9.99, currency="USD", stock=50,
            weight=0.5, weight_unit="kg", origin="China",
            created_by=admin_user.id,
        )
        db.add_all([p_a, p_b])
        db.commit()
        db.refresh(p_a)
        db.refresh(p_b)

        response = client.post("/api/v1/export/csv", json={
            "platform": "amazon",
            "product_ids": [p_a.id, p_b.id],
        }, headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 409, (
            f"Expected 409 for cross-product inconsistency, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "Export blocked due to consistency errors" in data["detail"]["message"], (
            f"Unexpected detail: {data['detail']}"
        )
        issues = data["detail"]["issues"]
        assert any(
            i["type"] == "cross_product_inconsistency" for i in issues
        ), f"Expected cross_product_inconsistency in issues, got: {issues}"
