import pytest
from app.models.product import Product

pytestmark = pytest.mark.integration

import pytest
from app.models.product import Product


@pytest.mark.integration
class TestProducts:

    def test_create_product_success(self, client, editor_token):
        """Editor can create a product."""
        response = client.post("/api/v1/products", json={
            "sku": "NEW-001",
            "product_name_zh": "Test Product ZH",
            "product_name_en": "Test Product EN",
            "category": "General",
            "brand": "TestBrand",
            "color_zh": "Red",
            "color_en": "Blue",
            "material_zh": "Steel",
            "material_en": "Metal",
            "price": 29.99,
            "currency": "USD",
            "stock": 100,
            "weight": 1.0,
            "weight_unit": "kg",
            "origin": "China",
        }, headers={"Authorization": f"Bearer {editor_token}"})
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "NEW-001"
        assert data["product_name_zh"] == "Test Product ZH"
        assert data["consistency_status"] == "unchecked"

    def test_create_product_duplicate_sku(self, client, editor_token, sample_product):
        response = client.post("/api/v1/products", json={
            "sku": "TEST-001",
            "product_name_zh": "            ",
            "product_name_en": "Duplicate Product",
            "category": "General",
        }, headers={"Authorization": f"Bearer {editor_token}"})
        assert response.status_code == 400
        assert "SKU already exists" in response.json()["detail"]

    def test_create_product_viewer_forbidden(self, client, viewer_token):
        response = client.post("/api/v1/products", json={
            "sku": "FORBIDDEN-001",
            "product_name_zh": "            ",
            "product_name_en": "Forbidden",
            "category": "General",
        }, headers={"Authorization": f"Bearer {viewer_token}"})
        assert response.status_code == 403

    def test_list_products(self, client, admin_token, sample_product):
        response = client.get("/api/v1/products", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["sku"] == "TEST-001"

    def test_list_products_search(self, client, admin_token, sample_product):
        """Search products by name returns matching results."""
        response = client.get("/api/v1/products?search=Test", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_list_products_search_no_result(self, client, admin_token, sample_product):
        """Search with a term that matches no products returns empty list."""
        response = client.get("/api/v1/products?search=ZZZZNOTFOUND", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_get_product_not_found(self, client, admin_token):
        """Requesting a non-existent product returns 404."""
        response = client.get("/api/v1/products/nonexistent-id", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 404

    def test_delete_product_success(self, client, admin_token, sample_product):
        """Admin can delete an existing product (soft delete)."""
        response = client.delete(f"/api/v1/products/{sample_product.id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200

    def test_pagination(self, client, admin_token, db, admin_user):
        #                   
        for i in range(25):
            product = db.query(
                __import__('app.models.product', fromlist=['Product']).Product
            ).first() or None
            #         ?client       
            client.post("/api/v1/products", json={
                "sku": f"PAG-{i:03d}",
                "product_name_zh": f"            {i}",
                "product_name_en": f"Pagination Product {i}",
                "category": "General",
            }, headers={"Authorization": f"Bearer {admin_token}"})

        # Test pagination
        response = client.get("/api/v1/products?page=1&page_size=10", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total"] >= 25
