import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, Index
from sqlalchemy import JSON
from app.database import Base


class TermDictionary(Base):
    __tablename__ = "term_dictionary"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zh = Column(String(100), nullable=False)
    en = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    note = Column(Text, nullable=True)
    synonyms = Column(JSON, nullable=False, default=list)
    platform_amazon = Column(String(100), nullable=True)
    platform_alibaba = Column(String(100), nullable=True)
    is_builtin = Column(Boolean, nullable=False, default=True, index=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_term_zh_en", "zh", "en", unique=True),
    )

