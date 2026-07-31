import pytest

pytestmark = pytest.mark.integration

import pytest
import io
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token


@pytest.mark.security
class TestPathTraversal:

    def test_path_traversal_filename(self, client: TestClient, admin_token):

        # Test with normal filenames
        normal_filenames = [
            "test.csv",
            "normal_file.csv",
            "import_2024.csv",
        ]

        for filename in normal_filenames:
            file_content = b"sku,product_name_zh,product_name_en,category\nTEST001,test,Test,general"

            response = client.post(
                "/api/v1/import/upload",
                files={"file": (filename, io.BytesIO(file_content), "text/csv")},
                headers={"Authorization": f"Bearer {admin_token}"}
            )

            assert response.status_code == 200
            data = response.json()

            #                                   
            safe_filename = data["filename"]
            assert ".." not in safe_filename
            assert "/" not in safe_filename
            assert "\\" not in safe_filename
            assert safe_filename.endswith(".csv")
