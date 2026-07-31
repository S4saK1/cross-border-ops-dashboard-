"""
用户管理API模块

提供用户管理功能，包括：
- 用户列表查询
- 用户信息获取
- 用户状态管理
- 用户角色管理
- 管理员创建/更新/删除用户（P0/P1）
- 管理员重置用户密码（P1）
"""
import logging
import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserProfile
from app.schemas.auth import UserOut, AdminUserCreate, UserUpdate, AdminResetPasswordRequest, BulkUserActionRequest
from app.core.deps import require_admin, require_viewer
from app.models.role import Role
from app.core.audit import write_audit_log
from app.core.security import get_current_user, get_password_hash, revoke_all_user_tokens

router = APIRouter()
logger = logging.getLogger(__name__)


def _generate_temp_password(length: int = 16) -> str:
    """生成满足密码强度要求的临时密码"""
    # 确保至少包含大写、小写、数字、特殊字符
    upper = secrets.choice(string.ascii_uppercase)
    lower = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    special = secrets.choice("!@#$%^&*")
    remaining = ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for _ in range(length - 4))
    chars = list(upper + lower + digit + special + remaining)
    # Fisher-Yates shuffle
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return ''.join(chars)


@router.get("", response_model=list[UserOut])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    获取用户列表（仅管理员）
    """
    q = db.query(UserProfile)
    if role:
        q = q.filter(UserProfile.role == role)

    users = q.offset((page - 1) * page_size).limit(page_size).all()
    return [UserOut.model_validate(user) for user in users]


@router.get("/me", response_model=UserOut)
def get_current_user_info(current_user=Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_viewer),
):
    """
    获取指定用户信息

    安全：不区分"不存在"与"无权查看"，统一返回 404，防止用户枚举（ADR-006/PRD §8.2）。
    """
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 非管理员只能查看自己的信息——但统一返回 404 防止枚举
    if current_user.role != Role.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put("/{user_id}/role")
def update_user_role(
    user_id: str,
    role: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    更新用户角色（仅管理员）
    """
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    valid_roles = Role.values()
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    if current_user.id == user_id and role != Role.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot change your own admin role")

    old_role = user.role
    user.role = role

    ip = request.client.host if request.client else None
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action="user_role_change",
        subject_type="user",
        subject_id=user_id,
        before={"role": old_role},
        after={"role": role},
        ip_address=ip,
    )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update role: {e}")
        raise HTTPException(500, "Failed to update user role")

    logger.info(f"User {user_id} role updated to {role} by admin {current_user.id}")
    return {"message": f"User role updated to {role}"}


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    data: AdminUserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    管理员创建用户（P0: API-1）
    """
    existing = db.query(UserProfile).filter(UserProfile.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    valid_roles = Role.values()
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    user = UserProfile(
        email=data.email,
        password_hash=get_password_hash(data.password),
        display_name=data.display_name,
        role=data.role,
        force_password_change=True,
    )
    db.add(user)

    ip = request.client.host if request.client else None
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action="user_create",
        subject_type="user",
        subject_id=user.id,
        after={
            "email": data.email,
            "display_name": data.display_name,
            "role": data.role,
        },
        ip_address=ip,
    )

    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(500, "Failed to create user")

    logger.info(f"Admin {current_user.id} created user {user.id} with role {data.role}")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    管理员更新用户（P0: API-2）
    """
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    before = {}
    after = {}
    changed = False

    if data.email is not None and data.email != user.email:
        existing = db.query(UserProfile).filter(
            UserProfile.email == data.email,
            UserProfile.id != user_id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")
        before["email"] = user.email
        after["email"] = data.email
        user.email = data.email
        changed = True

    if data.display_name is not None and data.display_name != user.display_name:
        before["display_name"] = user.display_name
        after["display_name"] = data.display_name
        user.display_name = data.display_name
        changed = True

    if data.role is not None and data.role != user.role:
        if current_user.id == user_id and data.role != Role.ADMIN:
            raise HTTPException(status_code=400, detail="Cannot change your own admin role")
        before["role"] = user.role
        after["role"] = data.role
        user.role = data.role
        changed = True

    if data.is_active is not None and data.is_active != user.is_active:
        if current_user.id == user_id and not data.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        before["is_active"] = user.is_active
        after["is_active"] = data.is_active
        user.is_active = data.is_active
        changed = True

    if data.force_password_change is not None and data.force_password_change != user.force_password_change:
        before["force_password_change"] = user.force_password_change
        after["force_password_change"] = data.force_password_change
        user.force_password_change = data.force_password_change
        changed = True

    if not changed:
        return user

    ip = request.client.host if request.client else None
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action="user_update",
        subject_type="user",
        subject_id=user_id,
        before=before,
        after=after,
        ip_address=ip,
    )

    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update user: {e}")
        raise HTTPException(500, "Failed to update user")

    logger.info(f"Admin {current_user.id} updated user {user_id}: {list(after.keys())}")
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    管理员禁用用户 — 软删除（P1: API-3）

    将目标用户的 is_active 置为 False，同时撤销其所有活跃令牌。
    禁止管理员禁用自己。

    Args:
        user_id: 目标用户ID
        request: HTTP 请求对象
        db: 数据库会话
        current_user: 当前管理员用户

    Returns:
        dict: 操作结果
    """
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    if not user.is_active:
        # 幂等：已禁用的用户再次禁用不报错
        return {"message": "User already deactivated", "user_id": user_id}

    user.is_active = False

    ip = request.client.host if request.client else None
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action="user_delete",
        subject_type="user",
        subject_id=user_id,
        before={"is_active": True},
        after={"is_active": False},
        ip_address=ip,
    )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to deactivate user: {e}")
        raise HTTPException(500, "Failed to deactivate user")

    # 撤销目标用户所有令牌（独立事务，失败不影响主操作）
    try:
        revoke_all_user_tokens(user_id, db)
    except Exception as e:
        logger.warning(f"Failed to revoke tokens for deactivated user {user_id}: {e}")

    logger.info(f"Admin {current_user.id} deactivated user {user_id}")
    return {"message": "User deactivated successfully", "user_id": user_id}


@router.post("/{user_id}/reset-password")
def reset_user_password(
    user_id: str,
    data: AdminResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    管理员重置用户密码（P1: API-4）

    为目标用户生成临时密码，设置强制改密标志，撤销所有活跃令牌。
    v1 返回临时密码（无邮件通知模块）。

    Args:
        user_id: 目标用户ID
        data: 重置密码请求体（v1 无额外参数）
        request: HTTP 请求对象
        db: 数据库会话
        current_user: 当前管理员用户

    Returns:
        dict: 包含临时密码和提示信息
    """
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Cannot reset password for deactivated user")

    # 生成符合强度要求的临时密码
    temp_password = _generate_temp_password()
    user.password_hash = get_password_hash(temp_password)
    user.force_password_change = True

    ip = request.client.host if request.client else None
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action="user_password_reset",
        subject_type="user",
        subject_id=user_id,
        after={"force_password_change": True},
        ip_address=ip,
    )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset password for user {user_id}: {e}")
        raise HTTPException(500, "Failed to reset user password")

    # 撤销目标用户所有令牌（独立事务，失败不影响主操作）
    try:
        revoke_all_user_tokens(user_id, db)
    except Exception as e:
        logger.warning(f"Failed to revoke tokens after password reset for user {user_id}: {e}")

    logger.info(f"Admin {current_user.id} reset password for user {user_id}")
    return {"message": "Password reset successfully. User must change password on next login.", "temporary_password": temp_password, "user_id": user_id}


@router.post("/bulk")
def bulk_user_operations(
    data: BulkUserActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    批量用户操作（P2: API-5）

    支持批量角色变更、启用、禁用。
    先预校验全部操作，全部通过后在单事务中执行，逐条写审计。

    Args:
        data: 批量操作请求体（最多 100 条）
        request: HTTP 请求对象
        db: 数据库会话
        current_user: 当前管理员用户

    Returns:
        dict: 操作结果汇总
    """
    ip = request.client.host if request.client else None
    users_map: dict[str, UserProfile] = {}
    errors: list[dict] = []

    # ── Phase 1: 预校验全部操作 ──
    for idx, op in enumerate(data.operations):
        user = db.query(UserProfile).filter(UserProfile.id == op.user_id).first()
        if not user:
            errors.append({"index": idx, "user_id": op.user_id, "error": "User not found"})
            continue

        users_map[op.user_id] = user

        if op.action == "update_role":
            if current_user.id == op.user_id and op.role != Role.ADMIN:
                errors.append({"index": idx, "user_id": op.user_id, "error": "Cannot change your own admin role"})
        elif op.action == "disable":
            if current_user.id == op.user_id:
                errors.append({"index": idx, "user_id": op.user_id, "error": "Cannot deactivate yourself"})

    if errors:
        raise HTTPException(status_code=400, detail={"message": "Validation failed", "errors": errors})

    # ── Phase 2: 单事务执行 ──
    results: list[dict] = []
    user_ids_to_revoke: set[str] = set()

    try:
        for idx, op in enumerate(data.operations):
            user = users_map[op.user_id]
            action = op.action
            before_state = {}
            after_state = {}

            if action == "update_role":
                before_state["role"] = user.role
                after_state["role"] = op.role
                user.role = op.role
                user_ids_to_revoke.add(op.user_id)

            elif action == "disable":
                if user.is_active:
                    before_state["is_active"] = True
                    after_state["is_active"] = False
                    user.is_active = False
                    user_ids_to_revoke.add(op.user_id)
                else:
                    # 幂等，跳过但记录
                    results.append({"index": idx, "user_id": op.user_id, "action": action, "status": "skipped", "reason": "Already deactivated"})
                    continue

            elif action == "enable":
                if not user.is_active:
                    before_state["is_active"] = False
                    after_state["is_active"] = True
                    user.is_active = True
                else:
                    results.append({"index": idx, "user_id": op.user_id, "action": action, "status": "skipped", "reason": "Already active"})
                    continue

            write_audit_log(
                db=db,
                actor_id=current_user.id,
                action=f"user_{action}",
                subject_type="user",
                subject_id=op.user_id,
                before=before_state,
                after=after_state,
                ip_address=ip,
            )
            results.append({"index": idx, "user_id": op.user_id, "action": action, "status": "success"})

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk operation failed: {e}")
        raise HTTPException(500, f"Bulk operation failed: {str(e)}")

    # ── Phase 3: 撤销受影响用户的令牌（独立事务，失败不影响主结果）──
    for uid in user_ids_to_revoke:
        try:
            revoke_all_user_tokens(uid, db)
        except Exception as e:
            logger.warning(f"Failed to revoke tokens for user {uid} after bulk operation: {e}")

    logger.info(f"Admin {current_user.id} executed bulk operation: {len(results)} items, {len(user_ids_to_revoke)} tokens revoked")
    return {
        "message": f"Bulk operation completed: {len(results)} items processed",
        "results": results,
        "tokens_revoked": len(user_ids_to_revoke),
    }
