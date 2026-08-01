"""Rate limiting tests — verify 429 is returned when threshold exceeded.

The conftest autouse ``clear_rate_limiter`` mocks RateLimiter.check → always True
so that most tests are not affected.  This module overrides that mock with a
real counter-based limiter to prove the auth brute-force protection works.
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.integration
class TestRateLimiting:
    """Auth endpoint rate-limiting: login & register share a 5/min sliding window."""

    def test_login_rate_limit_429_after_threshold(self, client, admin_user, monkeypatch):
        """After 5 valid POSTs to /api/v1/auth/login, the 6th must return exactly 429.

        Previous tests used ``assert status_code in (401, 429)`` with the mock
        always returning True, so the 429 branch was unreachable.  This test
        replaces the mock with a per-IP counter (threshold = 5, window = 60 s)
        and proves the middleware blocks on the 6th request.
        """
        # ── Override the autouse mock with a real counting limiter ──
        state = {"counts": {}}

        def counting_check(client_key: str, max_requests: int = 5, window_seconds: int = 60) -> bool:
            c = state["counts"].get(client_key, 0)
            state["counts"][client_key] = c + 1
            return c < max_requests  # allow 0..4 (first 5), deny from 5th onward

        monkeypatch.setattr("app.core.redis.RateLimiter.check", counting_check)

        payload = {"email": "admin@test.com", "password": "wrongpassword"}

        # First 5 requests: rate limiter allows → auth returns 401 (bad password)
        for i in range(5):
            r = client.post("/api/v1/auth/login", json=payload)
            assert r.status_code == 401, (
                f"Attempt {i + 1}: expected 401 (rate limiter pass, auth fail), got {r.status_code}"
            )

        # 6th request: rate limiter MUST return 429
        r = client.post("/api/v1/auth/login", json=payload)
        assert r.status_code == 429, (
            f"Attempt 6: expected 429 (rate limited), got {r.status_code}"
        )
        data = r.json()
        assert "Too many requests" in data.get("message", ""), (
            f"Expected rate-limit message, got: {data}"
        )

    def test_register_rate_limit_429_after_threshold(self, client, monkeypatch):
        """Register endpoint shares the same limiter; 6th POST must return 429."""
        state = {"counts": {}}

        def counting_check(client_key: str, max_requests: int = 5, window_seconds: int = 60) -> bool:
            c = state["counts"].get(client_key, 0)
            state["counts"][client_key] = c + 1
            return c < max_requests

        monkeypatch.setattr("app.core.redis.RateLimiter.check", counting_check)

        # Each registration must use a unique email to avoid 400 (duplicate)
        for i in range(5):
            payload = {
                "email": f"rl-test-{i}@example.com",
                "password": "X9kLm4PqR7vT2wN5!",
                "display_name": f"RL Test {i}",
            }
            r = client.post("/api/v1/auth/register", json=payload)
            assert r.status_code == 200, (
                f"Attempt {i + 1}: expected 200 (register OK), got {r.status_code}"
            )

        # 6th request: rate limiter MUST return 429
        r = client.post("/api/v1/auth/register", json={
            "email": "rl-test-99@example.com",
            "password": "X9kLm4PqR7vT2wN5!",
            "display_name": "RL Test 99",
        })
        assert r.status_code == 429, (
            f"Attempt 6: expected 429 (rate limited), got {r.status_code}"
        )
