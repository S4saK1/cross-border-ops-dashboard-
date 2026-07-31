from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserProfile
from app.schemas.auth import UserCreate, UserLogin, RefreshTokenRequest, TokenResponse, UserOut, ChangePasswordRequest, PasswordStrengthRequest
from app.core.security import (
    set_auth_cookies,
    clear_auth_cookies,
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    is_token_blacklisted,
    blacklist_refresh_token,
    revoke_all_user_tokens,
    cleanup_expired_blacklist_entries,
)
from app.core.deps import require_admin
from app.models.role import Role
from app.core.audit import write_audit_log
from app.config import settings
from app.utils.password_validator import validate_password_strength, get_password_requirements

router = APIRouter()


@router.post("/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with role escalation prevention and password strength validation.
    
    Security note: This endpoint ignores the role field from user input
    and forces all new users to have "viewer" role to prevent privilege escalation.
    Also validates password strength to prevent weak passwords.
    """
    # 验证邮箱是否已存在
    existing = db.query(UserProfile).filter(UserProfile.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 验证密码强度（双重验证：Pydantic验证 + API层验证）
    is_valid, errors = validate_password_strength(data.password)
    if not is_valid:
        error_messages = [error.message for error in errors]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "密码不符合安全要求",
                "errors": error_messages,
                "requirements": get_password_requirements()
            }
        )
    
    # Security: Force all new users to have "viewer" role
    # This prevents privilege escalation through the registration endpoint
    user = UserProfile(
        email=data.email,
        password_hash=get_password_hash(data.password),
        display_name=data.display_name,
        role=Role.VIEWER,  # Forced role - ignore any role from user input
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(UserProfile).filter(UserProfile.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    user.last_login_at = datetime.utcnow()
    # ── 审计日志 ──
    from app.core.audit import write_audit_log
    write_audit_log(
        db=db,
        actor_id=user.id,
        action='user_login',
        subject_type='user',
        subject_id=user.id,
        after={"force_password_change": user.force_password_change},
    )

    
    # 检查是否需要强制修改密码
    if user.force_password_change:
        # 返回特殊token，表示需要修改密码
        access_token = create_access_token({"sub": user.id, "force_password_change": True}, token_version=user.token_version)
        refresh_token = create_refresh_token({"sub": user.id, "force_password_change": True}, token_version=user.token_version)
        set_auth_cookies(response, access_token, refresh_token)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role},
            force_password_change=True,
        )
    
    access_token = create_access_token({"sub": user.id}, token_version=user.token_version)
    refresh_token = create_refresh_token({"sub": user.id}, token_version=user.token_version)
    set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role},
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshTokenRequest, response: Response, db: Session = Depends(get_db)):
    payload = decode_token(request.token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    # 检查token是否在黑名单中
    token_id = payload.get("token_id")
    user_id = payload.get("sub")
    if token_id and is_token_blacklisted(token_id, db, user_id=user_id):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Verify token version
    token_ver = payload.get("ver")
    if token_ver is not None and token_ver != user.token_version:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    
    # 将旧token加入黑名单
    if token_id:
        from datetime import datetime, timedelta
        from jose import jwt
        from jose.utils import base64url_decode
        
        # 解码token获取过期时间
        try:
            token_payload = jwt.get_unverified_claims(request.token)
            exp_timestamp = token_payload.get("exp")
            if exp_timestamp:
                expires_at = datetime.utcfromtimestamp(exp_timestamp)
                blacklist_refresh_token(token_id, user.id, expires_at, db)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to blacklist old token during refresh: {e}")
    
    access_token = create_access_token({"sub": user.id}, token_version=user.token_version)
    new_refresh = create_refresh_token({"sub": user.id}, token_version=user.token_version)
    set_auth_cookies(response, access_token, new_refresh)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role},
    )


@router.post("/logout")
def logout(request: RefreshTokenRequest, response: Response, db: Session = Depends(get_db)):
    """用户登出，撤销当前refresh token"""
    payload = decode_token(request.token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    token_id = payload.get("token_id")
    if token_id:
        from datetime import datetime
        from jose import jwt
        
        # 解码token获取过期时间
        try:
            token_payload = jwt.get_unverified_claims(request.token)
            exp_timestamp = token_payload.get("exp")
            if exp_timestamp:
                expires_at = datetime.utcfromtimestamp(exp_timestamp)
                user_id = payload.get("sub")
                blacklist_refresh_token(token_id, user_id, expires_at, db)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to blacklist token during logout: {e}")
    
    # ── 审计日志 ──
    from app.core.audit import write_audit_log
    user_id = payload.get('sub')
    if user_id:
        write_audit_log(
            db=db,
            actor_id=user_id,
            action='user_logout',
            subject_type='user',
            subject_id=user_id,
        )
        db.commit()

    clear_auth_cookies(response)
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
def logout_all(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """撤销用户的所有刷新令牌"""
    revoke_all_user_tokens(current_user.id, db)
    return {"message": "All tokens have been revoked"}


@router.get("/me", response_model=UserOut)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码，支持强制密码修改"""
    # 验证当前密码
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # 验证新密码强度
    is_valid, errors = validate_password_strength(data.new_password)
    if not is_valid:
        error_messages = [error.message for error in errors]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "New password does not meet security requirements",
                "errors": error_messages,
                "requirements": get_password_requirements()
            }
        )
    
    # 更新密码
    old_force_flag = current_user.force_password_change
    current_user.password_hash = get_password_hash(data.new_password)
    current_user.force_password_change = False  # 解除强制修改密码状态
    
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action="password_change",
        subject_type="user",
        subject_id=current_user.id,
        before={"force_password_change": old_force_flag},
        after={"force_password_change": False},
    )
    
    # 先提交密码变更+审计，再撤销token（revoke_all 自行 commit）
    db.commit()
    revoke_all_user_tokens(current_user.id, db)

    return {"message": "Password changed successfully"}


@router.get("/password-requirements")
def get_password_requirements_endpoint():
    """
    获取密码要求信息
    
    Returns:
        dict: 密码要求和建议
    """
    return get_password_requirements()


@router.post("/check-password-strength")
def check_password_strength(data: PasswordStrengthRequest):
    """
    检查密码强度
    
    Args:
        password: 要检查的密码
        
    Returns:
        dict: 密码强度信息和建议
    """
    from app.utils.password_validator import get_password_strength
    return get_password_strength(data.password)
