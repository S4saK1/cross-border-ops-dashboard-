"""刷新令牌黑名单模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, ForeignKey
from app.database import Base


class RefreshTokenBlacklist(Base):
    """刷新令牌黑名单表

    用于存储已撤销的刷新令牌，防止令牌重用
    """
    __tablename__ = "refresh_token_blacklist"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token_id = Column(String(36), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 复合索引：用户ID + 过期时间
    __table_args__ = (
        Index('idx_token_blacklist_user_expires', 'user_id', 'expires_at'),
    )

    def is_expired(self) -> bool:
        """检查令牌是否已过期"""
        return datetime.utcnow() > self.expires_at

    @classmethod
    def create(cls, token_id: str, user_id: str, expires_at: datetime) -> 'RefreshTokenBlacklist':
        """创建黑名单条目"""
        return cls(
            token_id=token_id,
            user_id=user_id,
            expires_at=expires_at
        )
