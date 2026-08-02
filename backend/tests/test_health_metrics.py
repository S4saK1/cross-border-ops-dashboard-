"""Health and metrics endpoint tests."""
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.integration
class TestHealthMetrics:
    """Health and Prometheus metrics tests."""

    def test_health_endpoint(self, client):
        """Health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_db_endpoint(self, client):
        """DB health endpoint exists and reports a status."""
        response = client.get("/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "unhealthy")

    def test_app_version_matches_release(self, client):
        """App version string must match the released version (v2.0.0)."""
        from app.main import app
        assert app.version == "2.0.0"

    def test_prometheus_metrics_public(self, client):
        """Prometheus metrics endpoint is publicly accessible."""
        response = client.get("/metrics/prometheus")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_admin_metrics_endpoint(self, client, admin_token):
        """Admin metrics endpoint requires auth."""
        response = client.get("/metrics", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
