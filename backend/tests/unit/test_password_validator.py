"""Password validator unit tests (F-59)"""
import pytest
from app.utils.password_validator import (
    validate_password_strength,
    get_password_strength,
    get_password_requirements
)


@pytest.mark.unit
class TestPasswordValidator:
    """Test suite for password validator"""

    def test_strong_password(self):
        """Test a strong password passes validation"""
        valid, errors = validate_password_strength("StrongP@ss1")
        assert valid is True
        assert len(errors) == 0

    def test_short_password(self):
        """Test short password fails"""
        valid, errors = validate_password_strength("Ab1")
        assert valid is False

    def test_no_uppercase(self):
        """Test password without uppercase fails"""
        valid, errors = validate_password_strength("abcdefgh1")
        assert valid is False

    def test_no_digit(self):
        """Test password without digit fails"""
        valid, errors = validate_password_strength("Abcdefghijk")
        assert valid is False

    def test_get_strength(self):
        """Test password strength scoring"""
        result = get_password_strength("StrongP@ss1")
        assert "score" in result

    def test_get_requirements(self):
        """Test password requirements retrieval"""
        reqs = get_password_requirements()
        assert "min_length" in reqs
        assert "require_uppercase" in reqs
        assert "require_lowercase" in reqs
        assert "require_digit" in reqs
        assert "require_special" in reqs