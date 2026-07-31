"""P0-8: Terms API tests — fixed structure (tests were nested inside _seed_terms, collecting 0)."""
import pytest
from app.models.term import TermDictionary

pytestmark = pytest.mark.integration


def _seed_terms(db):
    """Helper: seed test term dictionary entries."""
    terms = [
        TermDictionary(zh="手机壳", en="Phone Case", category="3C", is_builtin=True),
        TermDictionary(zh="充电器", en="Charger", category="3C", is_builtin=True),
        TermDictionary(zh="数据线", en="USB Cable", category="3C", is_builtin=True),
        TermDictionary(zh="连衣裙", en="Dress", category="Apparel", is_builtin=True),
    ]
    for t in terms:
        db.add(t)
    db.commit()


def test_list_terms(client, admin_token):
    response = client.get("/api/v1/terms", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_list_terms_by_category(client, admin_token, db):
    _seed_terms(db)
    response = client.get("/api/v1/terms?category=3C", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["category"] == "3C"


def test_list_terms_pagination(client, admin_token):
    response = client.get("/api/v1/terms?page=1&page_size=5", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5


def test_create_custom_term(client, editor_token, db):
    payload = {"zh": "测试术语", "en": "Test Term", "category": "General"}
    response = client.post("/api/v1/terms", json=payload, headers={
        "Authorization": f"Bearer {editor_token}"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["zh"] == "测试术语"
    assert data["en"] == "Test Term"
    assert data["is_builtin"] is False


def test_terms_require_auth(client):
    response = client.get("/api/v1/terms")
    assert response.status_code == 401
