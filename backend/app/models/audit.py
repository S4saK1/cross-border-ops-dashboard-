import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, ForeignKey
from sqlalchemy import JSON
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(64), nullable=True)
    details = Column(JSON, nullable=True, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )
