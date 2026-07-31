import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ForeignKey, Numeric, Index
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku = Column(String(64), unique=True, nullable=False, index=True)
    product_name_zh = Column(String(200), nullable=False)
    product_name_en = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    brand = Column(String(50), nullable=True)
    description_zh = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=False, default="USD")
    stock = Column(Integer, nullable=True)
    color_zh = Column(String(100), nullable=True)
    color_en = Column(String(100), nullable=True)
    material_zh = Column(String(100), nullable=True)
    material_en = Column(String(100), nullable=True)
    size = Column(String(100), nullable=True)
    weight = Column(Numeric(10, 2), nullable=True)
    weight_unit = Column(String(10), nullable=True, default="kg")
    length = Column(Numeric(10, 2), nullable=True)
    width = Column(Numeric(10, 2), nullable=True)
    height = Column(Numeric(10, 2), nullable=True)
    dimension_unit = Column(String(10), nullable=True, default="cm")
    origin = Column(String(50), nullable=True, default="China")
    model_number = Column(String(64), nullable=True)
    extra_fields = Column(JSON, nullable=True, default=dict)
    consistency_status = Column(String(20), nullable=False, default="unchecked")
    consistency_issues = Column(JSON, nullable=True, default=list)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("UserProfile", backref="products")

    __table_args__ = (
        Index("idx_product_name_search", "product_name_zh", "product_name_en"),
        Index("idx_product_created_by", "created_by"),
        Index("idx_product_is_deleted", "is_deleted"),
    )

