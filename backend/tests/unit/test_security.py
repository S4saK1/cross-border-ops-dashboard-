"""Security unit tests (F-59)"""
import pytest
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test suite for password hashing functions"""

    def test_hash_and_verify(self):
        """Test password hashing and verification round-trip"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        """Test wrong password does not verify"""
        hashed = get_password_hash("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes(self):
        """Test same password produces different hashes each time"""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2


class TestTokenCreation:
    """Test suite for token creation and decoding"""

    def test_create_access_token(self):
        """Test creating and decoding an access token"""
        token = create_access_token({"sub": "test_user"})
        payload = decode_token(token)
        assert payload["sub"] == "test_user"
        assert payload["type"] == "access"

    def test_token_has_expiry(self):
        """Test access token has expiration"""
        token = create_access_token({"sub": "test_user"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_custom_expiry(self):
        """Test custom expiration delta"""
        from datetime import timedelta
        token = create_access_token({"sub": "test_user"}, expires_delta=timedelta(hours=1))
        payload = decode_token(token)
        assert payload["sub"] == "test_user"
