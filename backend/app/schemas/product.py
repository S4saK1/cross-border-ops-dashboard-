import os
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ProductCreate(BaseModel):
    sku: str = Field(..., max_length=64)
    product_name_zh: str = Field(..., max_length=200)
    product_name_en: str = Field(..., max_length=200)
    category: str = Field(..., max_length=50)
    brand: Optional[str] = None
    description_zh: Optional[str] = None
    description_en: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    stock: Optional[int] = None
    color_zh: Optional[str] = None
    color_en: Optional[str] = None
    material_zh: Optional[str] = None
    material_en: Optional[str] = None
    size: Optional[str] = None
    weight: Optional[float] = None
    weight_unit: str = "kg"
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    dimension_unit: str = "cm"
    origin: str = "China"
    model_number: Optional[str] = None
    extra_fields: Optional[dict] = None

    @field_validator("extra_fields")
    @classmethod
    def validate_extra_fields(cls, v):  # noqa: C901
        """F-40: Validate extra_fields against JSON Schema"""
        if v is None or v == {}:
            return v
        import json
        try:
            _schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "extra_fields_schema.json")
            with open(_schema_path, "r", encoding="utf-8") as _f:
                schema = json.load(_f)
            # Simple validation: check keys against allowed properties
            allowed = set(schema.get("properties", {}).keys())
            extra_keys = set(v.keys()) - allowed
            if extra_keys:
                raise ValueError(f"Unknown extra_fields keys: {', '.join(sorted(extra_keys))}")
            # Type validation per property
            for key, val in v.items():
                prop = schema["properties"].get(key, {})
                if prop.get("type") == "string" and not isinstance(val, str):
                    raise ValueError(f"extra_fields.{key} must be a string")
                if prop.get("type") == "integer" and not isinstance(val, int):
                    raise ValueError(f"extra_fields.{key} must be an integer")
                if prop.get("type") == "array" and not isinstance(val, list):
                    raise ValueError(f"extra_fields.{key} must be an array")
                # Max length check
                max_len = prop.get("maxLength")
                if max_len and isinstance(val, str) and len(val) > max_len:
                    raise ValueError(f"extra_fields.{key} exceeds max length {max_len}")
                # Pattern check
                pattern = prop.get("pattern")
                if pattern and isinstance(val, str):
                    import re
                    if not re.match(pattern, val):
                        raise ValueError(f"extra_fields.{key} does not match pattern {pattern}")
        except FileNotFoundError:
            pass  # Schema file not available, skip validation
        return v


class ProductUpdate(BaseModel):
    product_name_zh: Optional[str] = None
    product_name_en: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    description_zh: Optional[str] = None
    description_en: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    stock: Optional[int] = None
    color_zh: Optional[str] = None
    color_en: Optional[str] = None
    material_zh: Optional[str] = None
    material_en: Optional[str] = None
    size: Optional[str] = None
    weight: Optional[float] = None
    weight_unit: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    dimension_unit: Optional[str] = None
    origin: Optional[str] = None
    model_number: Optional[str] = None
    extra_fields: Optional[dict] = None

    @field_validator("extra_fields")
    @classmethod
    def validate_extra_fields(cls, v):  # noqa: C901
        if v is None or v == {}:
            return v
        import json
        import os
        import re
        try:
            _schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "extra_fields_schema.json")
            with open(_schema_path, "r", encoding="utf-8") as _f:
                schema = json.load(_f)
            allowed = set(schema.get("properties", {}).keys())
            extra_keys = set(v.keys()) - allowed
            if extra_keys:
                raise ValueError(f"Unknown extra_fields keys: {', '.join(sorted(extra_keys))}")
            for key, val in v.items():
                prop = schema["properties"].get(key, {})
                if prop.get("type") == "string" and not isinstance(val, str):
                    raise ValueError(f"extra_fields.{key} must be a string")
                if prop.get("type") == "integer" and not isinstance(val, int):
                    raise ValueError(f"extra_fields.{key} must be an integer")
                if prop.get("type") == "array" and not isinstance(val, list):
                    raise ValueError(f"extra_fields.{key} must be an array")
                max_len = prop.get("maxLength")
                if max_len and isinstance(val, str) and len(val) > max_len:
                    raise ValueError(f"extra_fields.{key} exceeds max length {max_len}")
                pattern = prop.get("pattern")
                if pattern and isinstance(val, str):
                    if not re.match(pattern, val):
                        raise ValueError(f"extra_fields.{key} does not match pattern {pattern}")
        except FileNotFoundError:
            pass
        return v


class ProductOut(BaseModel):
    id: str
    sku: str
    product_name_zh: str
    product_name_en: str
    category: str
    brand: Optional[str] = None
    price: Optional[float] = None
    currency: str
    color_en: Optional[str] = None
    material_en: Optional[str] = None
    consistency_status: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int
    total_pages: int
