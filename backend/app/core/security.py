from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import jwt
from jwt import PyJWTError
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        # 非法哈希格式（非 bcrypt）视为不匹配
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, token_version: int = 0) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access", "ver": token_version})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, token_version: int = 0) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "token_id": str(uuid.uuid4()), "ver": token_version})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_token_unverified(token: str) -> dict:
    """不解签名读取载荷（用于获取过期时间等元数据）。"""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"verify_signature": False},
    )


def is_token_blacklisted(token_id: str, db: Session, user_id: str | None = None) -> bool:  # noqa: C901
    """检查令牌是否在黑名单中"""
    # 首先检查Redis黑名单
    try:
        from app.core.redis import TokenBlacklist
        if TokenBlacklist.is_blacklisted(token_id):
            return True
        # 同时检查用户级黑名单
        if user_id:
            try:
                if TokenBlacklist.is_user_blacklisted(user_id):
                    return True
            except Exception:
                pass  # Redis 不可用时回退到 DB 检查
    except Exception:
        # Redis不可用时回退到数据库检查
        pass

    # 回退到数据库检查
    from app.models.token_blacklist import RefreshTokenBlacklist

    blacklisted = db.query(RefreshTokenBlacklist).filter(
        RefreshTokenBlacklist.token_id == token_id
    ).first()

    if blacklisted and not blacklisted.is_expired():
        return True

    # DB 路径也检查用户级黑名单
    if user_id:
        user_blacklisted = db.query(RefreshTokenBlacklist).filter(
            RefreshTokenBlacklist.user_id == user_id,
            RefreshTokenBlacklist.expires_at > datetime.utcnow()
        ).first()
        if user_blacklisted:
            return True

    return False


def blacklist_refresh_token(token_id: str, user_id: str, expires_at: datetime, db: Session) -> None:
    """将刷新令牌加入黑名单"""
    # 首先尝试添加到Redis黑名单
    try:
        from app.core.redis import TokenBlacklist
        # 计算过期时间（秒）
        expires_in = int((expires_at - datetime.utcnow()).total_seconds())
        if expires_in > 0:
            TokenBlacklist.add_to_blacklist(token_id, user_id, expires_in)
    except Exception:
        # Redis不可用时回退到数据库
        pass

    # 同时添加到数据库黑名单（确保兼容性）
    from app.models.token_blacklist import RefreshTokenBlacklist

    try:
        blacklist_entry = RefreshTokenBlacklist.create(
            token_id=token_id,
            user_id=user_id,
            expires_at=expires_at
        )
        db.add(blacklist_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to blacklist refresh token in DB: {e}")


def revoke_all_user_tokens(user_id: str, db: Session) -> None:
    """撤销用户的所有刷新令牌"""
    import logging
    logger = logging.getLogger(__name__)

    # 1. Redis 侧 - 设置用户级黑名单
    try:
        from app.core.redis import TokenBlacklist
        TokenBlacklist.blacklist_all_user_tokens(user_id, 86400)  # 24h TTL
    except Exception:
        pass

    # 2. DB 侧 - 同时更新数据库黑名单（确保兼容性）
    from app.models.token_blacklist import RefreshTokenBlacklist

    try:
        db.query(RefreshTokenBlacklist).filter(
            RefreshTokenBlacklist.user_id == user_id,
            RefreshTokenBlacklist.expires_at > datetime.utcnow()
        ).update({"expires_at": datetime.utcnow()})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update blacklist entries in DB: {e}")

    # 3. DB 侧 - 递增 token_version（fail-closed）
    try:
        from app.models.user import UserProfile
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if user:
            user.token_version += 1
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to revoke tokens for user {user_id} via token_version: {e}")


def cleanup_expired_blacklist_entries(db: Session) -> None:
    """清理过期的黑名单条目"""
    from app.models.token_blacklist import RefreshTokenBlacklist

    db.query(RefreshTokenBlacklist).filter(
        RefreshTokenBlacklist.expires_at < datetime.utcnow()
    ).delete()

    db.commit()


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    secure = settings.COOKIE_SECURE
    samesite = settings.COOKIE_SAMESITE
    domain = settings.COOKIE_DOMAIN or None

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        domain=domain,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        domain=domain,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )


def clear_auth_cookies(response: Response):
    secure = settings.COOKIE_SECURE
    samesite = settings.COOKIE_SAMESITE
    domain = settings.COOKIE_DOMAIN or None

    response.delete_cookie("access_token", path="/", domain=domain, secure=secure, samesite=samesite)
    response.delete_cookie("refresh_token", path="/api/v1/auth", domain=domain, secure=secure, samesite=samesite)


def get_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get("access_token")


def get_refresh_token_from_cookie(request: Request) -> str | None:
    """P0-5: 从 cookie 中读取 refresh_token，优先于 JSON body"""
    return request.cookies.get("refresh_token")


async def _authenticate(
    token: str = Depends(oauth2_scheme),
    request: Request = None,
    db: Session = Depends(get_db),
    enforce_force_password: bool = True,
):
    from app.models.user import UserProfile

    # Fallback: try cookie if no Bearer token
    if not token and request:
        token = get_token_from_cookie(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Verify token version (compatible with legacy tokens without "ver" claim)
    token_ver = payload.get("ver")
    if token_ver is not None and token_ver != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    # P0-7: 强制改密服务端拦截（改密端点自身通过 allow_forced 变体放行）
    if enforce_force_password and payload.get("force_password_change"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required",
        )

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """标准认证依赖：强制改密用户会被拦截。"""
    return await _authenticate(token=token, request=request, db=db, enforce_force_password=True)


async def get_current_user_allow_forced(
    token: str = Depends(oauth2_scheme),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """认证依赖变体：放行强制改密用户（仅用于 change-password 端点）。"""
    return await _authenticate(token=token, request=request, db=db, enforce_force_password=False)
