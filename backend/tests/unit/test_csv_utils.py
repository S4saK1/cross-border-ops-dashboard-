"""CSV cell sanitization tests (F-59)"""
import pytest
from app.utils.csv_utils import sanitize_csv_cell


@pytest.mark.unit
class TestSanitizeCsvCell:
    """Test suite for sanitize_csv_cell function"""

    def test_normal_text(self):
        """Test normal text without special characters"""
        result = sanitize_csv_cell("Hello World")
        assert result == "Hello World"

    def test_equals_sign(self):
        """Test = prefix removal"""
        result = sanitize_csv_cell("=SUM(A1:A10)")
        assert result == "'=SUM(A1:A10)"
    def test_plus_sign(self):
        """Test + prefix"""
        assert sanitize_csv_cell("+12345") == "'+12345"

    def test_minus_sign(self):
        """Test - prefix"""
        assert sanitize_csv_cell("-12345") == "'-12345"

    def test_at_sign(self):
        """Test @ prefix"""
        assert sanitize_csv_cell("@cmd") == "'@cmd"

    def test_tab_character(self):
        """Test tab insertion"""
        result = sanitize_csv_cell("hello\tworld")
        assert result == "hello\tworld"

    def test_newline_character(self):
        """Test newline handling"""
        result = sanitize_csv_cell("hello\nworld")
        assert result == "hello\nworld"

    def test_empty_string(self):
        """Test empty string"""
        assert sanitize_csv_cell("") == ""

    def test_none_value(self):
        """Test None value"""
        assert sanitize_csv_cell(None) is None

    def test_already_apostrophe(self):
        """Test already sanitized value"""
        assert sanitize_csv_cell("'safe") == "'safe"

    def test_mixed_special_chars(self):
        """Test mixed special characters"""
        result = sanitize_csv_cell("=-+@test")
        assert result == "'=-+@test"
