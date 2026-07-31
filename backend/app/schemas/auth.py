from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional, List, Any, Literal
from app.utils.password_validator import validate_password_strength


class UserCreate(BaseModel):
    email: str
    password: str
    display_name: str
    role: str = "viewer"
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度"""
        if not v:
            raise ValueError('密码不能为空')
        
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            # 返回第一个错误信息
            error_messages = [error.message for error in errors]
            raise ValueError('; '.join(error_messages))
        
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    token: Optional[str] = None  # P0-5: 优先从 cookie 读取
    token: str
    
    @field_validator('token')
    @classmethod
    def validate_token(cls, v: str) -> str:
        """验证token格式"""
        if not v or not v.strip():
            raise ValueError('Token不能为空')
        return v.strip()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None  # P0-5: 不再通过 JSON body 返回，仅 set-cookie
    token_type: str = "Bearer"
    expires_in: int
    user: dict
    force_password_change: bool = False


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Request body models for auth endpoints
class ChangePasswordRequest(BaseModel):
    """修改密码请求体"""
    current_password: str = Field(..., min_length=1, description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")


class AdminUserCreate(BaseModel):
    """管理员创建用户请求体"""
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="viewer", max_length=20)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v:
            raise ValueError("密码不能为空")
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            error_messages = [error.message for error in errors]
            raise ValueError("; ".join(error_messages))
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        from app.models.role import Role
        if v not in Role.values():
            raise ValueError(f"Invalid role. Must be one of: {Role.values()}")
        return v


class UserUpdate(BaseModel):
    """管理员更新用户请求体（所有字段可选）"""
    email: Optional[str] = Field(default=None, min_length=1, max_length=255)
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    role: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None
    force_password_change: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from app.models.role import Role
        if v not in Role.values():
            raise ValueError(f"Invalid role. Must be one of: {Role.values()}")
        return v



class AdminResetPasswordRequest(BaseModel):
    """管理员重置用户密码请求体（v1：无需额外参数，直接触发重置）"""
    pass


class BulkUserOperation(BaseModel):
    """批量操作中的单条操作"""
    user_id: str = Field(..., min_length=1)
    action: Literal["update_role", "disable", "enable"] = Field(...)
    role: Optional[str] = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_operation(self):
        if self.action == "update_role":
            if self.role is None:
                raise ValueError("role is required when action is 'update_role'")
            from app.models.role import Role
            if self.role not in Role.values():
                raise ValueError(f"Invalid role. Must be one of: {Role.values()}")
        return self


class BulkUserActionRequest(BaseModel):
    """批量用户操作请求体"""
    operations: list[BulkUserOperation] = Field(..., min_length=1, max_length=100)


class PasswordStrengthRequest(BaseModel):
    """密码强度检查请求体"""
    password: str = Field(..., min_length=1, description="要检查的密码")
