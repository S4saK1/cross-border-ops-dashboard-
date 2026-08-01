"""术语一致性检测引擎"""
import json
import os
from sqlalchemy.orm import Session
from app.models.product import Product
from app.models.term import TermDictionary


class ConsistencyEngine:
    """三层一致性检测引擎：L1 精确匹配 + L2 同义词 + L3 拼写"""

    def __init__(self, db: Session):
        self.db = db
        self.rules = self._load_rules()
        self.synonyms = self._load_synonyms()

    def _load_rules(self) -> dict:
        rules_path = os.path.join(os.path.dirname(__file__), "..", "data", "consistency-rules.json")
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"rules": {}, "standardization": [], "auto_fix_rules": []}

    def _load_synonyms(self) -> dict:
        synonyms_path = os.path.join(os.path.dirname(__file__), "..", "data", "synonyms.json")
        try:
            with open(synonyms_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 建立 variant -> canonical 映射
                mapping = {}
                for group in data.get("synonym_groups", []):
                    canonical = group["canonical"]
                    for variant in group["variants"]:
                        mapping[variant.lower()] = canonical
                return mapping
        except FileNotFoundError:
            return {}

    def check_product(self, product: Product) -> list[dict]:
        """检测单个产品的一致性问题"""
        issues = []

        # L1: 精确匹配 - 检查中英文术语是否一致
        l1_issues = self._check_exact_match(product)
        issues.extend(l1_issues)

        # L2: 同义词检测
        l2_issues = self._check_synonyms(product)
        issues.extend(l2_issues)

        # L3: 拼写检测
        l3_issues = self._check_spelling(product)
        issues.extend(l3_issues)

        return issues

    def check_all_products(self) -> list[dict]:
        """检测所有产品的一致性问题，返回跨产品的问题"""
        issues = []
        products = self.db.query(Product).filter(Product.is_deleted.is_(False)).all()

        # 按中文术语分组统计英文翻译
        term_groups = {}
        for p in products:
            field_map = {
                "颜色": (p.color_zh, p.color_en),
                "材质": (p.material_zh, p.material_en),
            }
            for zh_term, (zh_val, en_val) in field_map.items():
                if zh_val and en_val:
                    if zh_term not in term_groups:
                        term_groups[zh_term] = {}
                    if en_val not in term_groups[zh_term]:
                        term_groups[zh_term][en_val] = []
                    term_groups[zh_term][en_val].append(p.sku)

        # 检测不一致
        for zh_term, en_variants in term_groups.items():
            if len(en_variants) > 1:
                sku_list = []
                for en_val, skus in en_variants.items():
                    sku_list.extend(skus)
                issues.append({
                    "severity": "ERROR",
                    "field": zh_term,
                    "zh_term": zh_term,
                    "found_values": list(en_variants.keys()),
                    "suggestion": max(en_variants.keys(), key=lambda x: len(en_variants[x])),
                    "affected_products": sku_list,
                    "type": "cross_product_inconsistency",
                })

        return issues

    def _check_exact_match(self, product: Product) -> list[dict]:
        """L1: 检查中英文字段是否符合术语词典"""
        issues = []
        field_pairs = [
            ("颜色", product.color_zh, product.color_en),
            ("材质", product.material_zh, product.material_en),
        ]

        for zh_term, zh_val, en_val in field_pairs:
            if not en_val:
                continue
            # 查询词典中的标准翻译
            term = self.db.query(TermDictionary).filter(
                TermDictionary.zh == zh_term,
                TermDictionary.is_builtin.is_(True)
            ).first()

            if term and term.en != en_val:
                # 检查是否在同义词列表中
                if en_val not in term.synonyms:
                    issues.append({
                        "severity": "WARNING",
                        "field": zh_term,
                        "zh_term": zh_term,
                        "found_value": en_val,
                        "standard_value": term.en,
                        "type": "non_standard_term",
                        "product_id": product.id,
                        "product_sku": product.sku,
                    })

        return issues

    def _check_synonyms(self, product: Product) -> list[dict]:
        """L2: 检查非标准变体"""
        issues = []
        en_fields = [
            ("color_en", product.color_en),
            ("material_en", product.material_en),
            ("brand", product.brand),
        ]

        for field_name, value in en_fields:
            if not value:
                continue
            value_lower = value.lower()
            if value_lower in self.synonyms:
                canonical = self.synonyms[value_lower]
                if canonical.lower() != value_lower:
                    issues.append({
                        "severity": "INFO",
                        "field": field_name,
                        "found_value": value,
                        "suggestion": canonical,
                        "type": "synonym_variant",
                        "product_id": product.id,
                        "product_sku": product.sku,
                    })

        return issues

    def _check_spelling(self, product: Product) -> list[dict]:
        """L3: 检查美式/英式拼写差异"""
        issues = []
        auto_fix_rules = self.rules.get("auto_fix_rules", [])

        en_fields = [
            ("color_en", product.color_en),
            ("material_en", product.material_en),
            ("product_name_en", product.product_name_en),
        ]

        for field_name, value in en_fields:
            if not value:
                continue
            for rule in auto_fix_rules:
                if rule["pattern"].lower() in value.lower():
                    issues.append({
                        "severity": "INFO",
                        "field": field_name,
                        "found_value": value,
                        "suggestion": value.replace(rule["pattern"], rule["replacement"]),
                        "reason": rule["reason"],
                        "type": "spelling_variation",
                        "product_id": product.id,
                        "product_sku": product.sku,
                    })

        return issues

    def auto_fix(self, issues: list[dict]) -> list[dict]:
        """自动修正 INFO 级别的问题"""
        fixed = []
        for issue in issues:
            if issue["severity"] == "INFO" and "suggestion" in issue:
                fixed.append({
                    "field": issue["field"],
                    "old_value": issue["found_value"],
                    "new_value": issue["suggestion"],
                    "product_id": issue.get("product_id"),
                })
        return fixed

    def check_products_batch(self, products: list[Product]) -> list[dict]:
        """Batch consistency check — avoids N+1 by loading terms once."""
        issues = []
        # Preload all term lookups in a single query
        terms = {
            t.zh: t
            for t in self.db.query(TermDictionary)
            .filter(TermDictionary.is_builtin.is_(True))
            .all()
        }

        for product in products:
            # L1: Exact match using preloaded terms
            field_pairs = [
                ("颜色", product.color_zh, product.color_en),
                ("材质", product.material_zh, product.material_en),
            ]
            for zh_term, zh_val, en_val in field_pairs:
                if not en_val:
                    continue
                term = terms.get(zh_term)
                if term and term.en != en_val:
                    if en_val not in (term.synonyms or []):
                        issues.append({
                            "severity": "WARNING",
                            "field": zh_term,
                            "zh_term": zh_term,
                            "found_value": en_val,
                            "standard_value": term.en,
                            "type": "non_standard_term",
                            "product_id": product.id,
                            "product_sku": product.sku,
                        })

            # L2: Synonym check (already uses preloaded self.synonyms)
            l2 = self._check_synonyms(product)
            issues.extend(l2)

            # L3: Spelling check (already uses preloaded self.rules)
            l3 = self._check_spelling(product)
            issues.extend(l3)

        # Cross-product check
        cross = self.check_all_products()
        issues.extend(cross)

        return issues


def get_consistency_status(issues: list[dict]) -> str:
    """根据问题列表返回产品的一致性状态"""
    if not issues:
        return "passed"
    severities = [i["severity"] for i in issues]
    if "ERROR" in severities:
        return "error"
    if "WARNING" in severities:
        return "warning"
    return "passed"
