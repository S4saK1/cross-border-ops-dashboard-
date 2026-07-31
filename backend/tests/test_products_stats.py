import pytest

pytestmark = pytest.mark.integration

"""产品统计端点测试 — 端点未实现，测试暂跳过"""
import pytest

pytestmark = pytest.mark.skip(reason="/api/v1/products/stats endpoint not yet implemented")


@pytest.mark.integration
class TestProductsStats:
    """产品统计端点测试——端点在规划中，待实现后启用本文件"""

    def test_products_stats_endpoint(self, client, admin_token, db, admin_user):
        """占位：待 /products/stats 端点实现后补全"""
        pass

    def test_products_stats_no_auth(self, client):
        """占位：待 /products/stats 端点实现后补全"""
        pass
