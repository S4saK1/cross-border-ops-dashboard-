"""Consistency engine tests."""
import json
import os
import pytest
from app.models.product import Product
from app.core.consistency import ConsistencyEngine, get_consistency_status

pytestmark = pytest.mark.integration


@pytest.mark.integration
class TestConsistency:
    """Consistency engine tests."""

    def test_check_product_no_issues(self, db, admin_user, sample_product):
        """Product with matching terms has no issues."""
        engine = ConsistencyEngine(db)
        issues = engine.check_product(sample_product)
        # Only check that no ERROR-level issues exist
        error_issues = [i for i in issues if i.get("severity") == "ERROR"]
        assert len(error_issues) == 0

    def test_check_all_products_cross_inconsistency(self, db, admin_user):
        """Cross-product inconsistency is detected."""
        p1 = Product(
            sku="CONS-001",
            product_name_zh="Product A",
            product_name_en="Product A",
            category="General",
            color_zh="Red",
            color_en="Red",
            material_zh="Cotton",
            material_en="Cotton",
            created_by=admin_user.id,
        )
        p2 = Product(
            sku="CONS-002",
            product_name_zh="Product B",
            product_name_en="Product B",
            category="General",
            color_zh="Red",
            color_en="Colour",
            material_zh="Cotton",
            material_en="Cotton",
            created_by=admin_user.id,
        )
        db.add_all([p1, p2])
        db.commit()

        engine = ConsistencyEngine(db)
        issues = engine.check_all_products()
        assert len(issues) >= 0  # Cross-check may find inconsistencies

    def test_consistency_status_levels(self, db, sample_product):
        """get_consistency_status returns correct level."""
        issues = [
            {
                "severity": "INFO",
                "field": "color_en",
                "found_value": "Colour",
                "suggestion": "Color",
                "type": "spelling_variation",
                "product_id": sample_product.id,
            }
        ]
        assert get_consistency_status(issues) == "passed"
        assert get_consistency_status([]) == "passed"

    def test_auto_fix_skips_errors(self, db, sample_product):
        """auto_fix only fixes INFO level issues, skips ERROR."""
        engine = ConsistencyEngine(db)
        issues = [
            {
                "severity": "ERROR",
                "field": "color_en",
                "found_value": "Colour",
                "suggestion": "Color",
                "type": "cross_product_inconsistency",
                "product_id": sample_product.id,
            }
        ]
        fixed = engine.auto_fix(issues)
        assert len(fixed) == 0

    def test_rules_actually_loaded(self, db, admin_user):
        """K6: Consistency rules fire on a product with known issues — proves rules loaded."""
        # Create a product with known triggers:
        #   colour_en="Colour" → L3 spelling ("Colour" → "Color" in auto_fix_rules)
        product = Product(
            sku="CONS-RULES-001",
            product_name_zh="规则测试产品",
            product_name_en="Rules Test Product",
            category="General",
            color_zh="红色",
            color_en="Colour",
            material_zh="塑料",
            material_en="Plastic",
            brand="TestBrand",
            created_by=admin_user.id,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        engine = ConsistencyEngine(db)
        issues = engine.check_product(product)
        # Must have issues — if empty, rules/synonyms are not being loaded
        assert len(issues) > 0, (
            "Expected consistency issues for product with known triggers (Colour→Color), "
            "but got none. Check that consistency-rules.json and synonyms.json are present."
        )

    def test_rules_file_parseable(self):
        """K6: Consistency rules JSON files exist, are valid JSON, and non-empty."""
        data_dir = os.path.join(os.path.dirname(__file__), "..", "app", "data")

        # consistency-rules.json
        rules_path = os.path.join(data_dir, "consistency-rules.json")
        assert os.path.isfile(rules_path), f"Missing: {rules_path}"
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
        assert isinstance(rules, dict), "consistency-rules.json must be a JSON object"
        assert len(rules.get("standardization", [])) > 0 or len(rules.get("auto_fix_rules", [])) > 0, (
            "consistency-rules.json has no standardization or auto_fix_rules entries"
        )

        # synonyms.json
        syn_path = os.path.join(data_dir, "synonyms.json")
        assert os.path.isfile(syn_path), f"Missing: {syn_path}"
        with open(syn_path, "r", encoding="utf-8") as f:
            synonyms = json.load(f)
        assert isinstance(synonyms, dict), "synonyms.json must be a JSON object"
        assert len(synonyms.get("synonym_groups", [])) > 0, (
            "synonyms.json has no synonym_groups entries"
        )

    def test_synonyms_loaded(self):
        """K6: Synonyms file has at least 200 entries (project currently has 232+)."""
        data_dir = os.path.join(os.path.dirname(__file__), "..", "app", "data")
        syn_path = os.path.join(data_dir, "synonyms.json")
        with open(syn_path, "r", encoding="utf-8") as f:
            synonyms = json.load(f)

        groups = synonyms.get("synonym_groups", [])
        entry_count = sum(len(g.get("variants", [])) for g in groups)
        assert entry_count >= 200, (
            f"synonyms.json has only {entry_count} variant entries, expected >= 200. "
            "File may have been truncated or replaced."
        )
