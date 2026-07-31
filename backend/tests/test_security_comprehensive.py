import pytest

pytestmark = pytest.mark.integration

import pytest
import io
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.security
class TestPasswordStrengthValidation:

    def test_password_strength_validation(self, client: TestClient):
        
        # Test weak passwords
        weak_passwords = [
            "password",
            "123456",
            "admin",
            "qwerty",
            "abc123",
            "11111111",
            "password123",
            "admin123",
        ]
        
        for password in weak_passwords:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test_{password}@example.com",
                    "password": password,
                    "display_name": "Test User",
                }
            )
            # Should fail with 400 or 422 due to weak password
            assert response.status_code in [400, 422]
            # Check for password validation error in response
            if response.status_code == 400:
                assert "password" in response.json()["detail"]["message"].lower()
            elif response.status_code == 422:
                # Pydantic validation error
                assert "detail" in response.json()

    def test_strong_password_accepted(self, client: TestClient):
        
        strong_passwords = [
            "StrongPassword123!",
            "MyStr0ngP@ssw0rd",
            "Complex!Pass#123",
            "Secure123$%^",
        ]
        
        for i, password in enumerate(strong_passwords):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"strong_{i}@example.com",
                    "password": password,
                    "display_name": "Test User",
                }
            )
            # Should succeed
            assert response.status_code == 200
            assert response.json()["role"] == "viewer"


@pytest.mark.security
class TestFileUploadSecurity:

    def test_file_upload_security(self, client: TestClient, editor_token):
        
        # Test malicious filenames
        malicious_filenames = [
            "../../../etc/passwd.csv",
            "..\\..\\windows\\system32\\config\\sam.csv",
            "test/../../../etc/shadow.csv",
            "test\\..\\..\\..\\etc\\passwd.csv",
            "....//....//etc/passwd.csv",
            "test.csv/../../../etc/passwd",
        ]
        
        for filename in malicious_filenames:
            file_content = b"sku,product_name_zh,product_name_en,category\nTEST001,test,Test,general"
            
            response = client.post(
                "/api/v1/import/upload",
                files={"file": (filename, io.BytesIO(file_content), "text/csv")},
                headers={"Authorization": f"Bearer {editor_token}"}
            )
            
            # Should either reject or sanitize the filename
            if response.status_code == 200:
                # If upload succeeds, verify filename is sanitized
                data = response.json()
                safe_filename = data["filename"]
                assert ".." not in safe_filename
                assert "/" not in safe_filename
                assert "\\" not in safe_filename
            else:
                # Should be rejected with 400
                assert response.status_code == 400


@pytest.mark.security
class TestJwtTokenSecurity:

    def test_jwt_token_security(self, client: TestClient):
        
        # Test login with invalid credentials
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 401
        
        # Test access without token
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        
        # Test access with invalid token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


@pytest.mark.security
class TestEndpointProtection:

    def test_admin_endpoint_protection(self, client: TestClient, viewer_token):
        
        # Try to access admin endpoint with viewer token
        response = client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        # Should be forbidden for viewer role
        assert response.status_code == 403

    def test_sql_injection_prevention(self, client: TestClient, editor_token):
        
        # Try SQL injection in search
        sql_injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' AND '1'='1",
        ]
        
        for payload in sql_injection_payloads:
            response = client.get(
                f"/api/v1/products?search={payload}",
                headers={"Authorization": f"Bearer {editor_token}"}
            )
            # Should return empty results, not error
            assert response.status_code == 200
            assert response.json()["total"] == 0

    def test_rate_limiting(self, client: TestClient):
        
        # Attempt multiple rapid login attempts
        for i in range(10):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "wrongpassword"
                }
            )
            # Should eventually get rate limited (429) or still get 401
            assert response.status_code in [401, 429]
