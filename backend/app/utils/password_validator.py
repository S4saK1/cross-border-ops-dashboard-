import re
from typing import List, Tuple


class PasswordValidationError:
    """密码验证错误信息"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message


def validate_password_strength(password: str) -> Tuple[bool, List[PasswordValidationError]]:
    """
    验证密码强度
    
    密码要求：
    1. 最小长度：8个字符
    2. 必须包含大写字母
    3. 必须包含小写字母
    4. 必须包含数字
    5. 可选：特殊字符（推荐）
    
    Args:
        password: 要验证的密码
        
    Returns:
        Tuple[bool, List[PasswordValidationError]]: 
            - 第一个值：是否通过验证
            - 第二个值：错误信息列表（如果验证通过则为空列表）
    """
    errors = []
    
    # 检查密码长度
    if len(password) < 8:
        errors.append(PasswordValidationError(
            code="PASSWORD_TOO_SHORT",
            message="密码长度不能少于8个字符"
        ))
    
    # 检查大写字母
    if not re.search(r'[A-Z]', password):
        errors.append(PasswordValidationError(
            code="PASSWORD_NO_UPPERCASE",
            message="密码必须包含至少一个大写字母"
        ))
    
    # 检查小写字母
    if not re.search(r'[a-z]', password):
        errors.append(PasswordValidationError(
            code="PASSWORD_NO_LOWERCASE",
            message="密码必须包含至少一个小写字母"
        ))
    
    # 检查数字
    if not re.search(r'\d', password):
        errors.append(PasswordValidationError(
            code="PASSWORD_NO_DIGIT",
            message="密码必须包含至少一个数字"
        ))
    
    # 检查特殊字符（推荐但不强制）
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?|\\]', password))
    
    # 检查常见弱密码模式
    weak_patterns = [
        r'^12345678',
        r'^password',
        r'^admin',
        r'^qwerty',
        r'^abc123',
        r'^11111111',
    ]
    
    for pattern in weak_patterns:
        if re.search(pattern, password.lower()):
            errors.append(PasswordValidationError(
                code="PASSWORD_TOO_COMMON",
                message="密码过于常见，请使用更复杂的密码"
            ))
            break
    
    return len(errors) == 0, errors


def get_password_strength(password: str) -> dict:
    """
    获取密码强度信息
    
    Args:
        password: 要检查的密码
        
    Returns:
        dict: 包含强度信息和提示
    """
    is_valid, errors = validate_password_strength(password)
    
    # 计算强度分数
    score = 0
    
    # 长度分数
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    
    # 复杂度分数
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'\d', password):
        score += 1
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?|\\]', password):
        score += 1
    
    # 判断强度等级
    if score <= 2:
        strength = "弱"
    elif score <= 4:
        strength = "中等"
    else:
        strength = "强"
    
    return {
        "is_valid": is_valid,
        "strength": strength,
        "score": score,
        "max_score": 6,
        "errors": [{"code": e.code, "message": e.message} for e in errors],
        "suggestions": _get_suggestions(password)
    }


def _get_suggestions(password: str) -> List[str]:
    """获取密码改进建议"""
    suggestions = []
    
    if len(password) < 8:
        suggestions.append("使用至少8个字符")
    
    if len(password) < 12:
        suggestions.append("建议使用12个或更多字符以提高安全性")
    
    if not re.search(r'[A-Z]', password):
        suggestions.append("添加大写字母（A-Z）")
    
    if not re.search(r'[a-z]', password):
        suggestions.append("添加小写字母（a-z）")
    
    if not re.search(r'\d', password):
        suggestions.append("添加数字（0-9）")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':\\"|,.<>/?]', password):
        suggestions.append("添加特殊字符（如!@#$%^&*）")
    
    return suggestions


def get_password_requirements() -> dict:
    """获取密码要求信息"""
    return {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_digit": True,
        "require_special": False,
        "recommended_length": 12,
        "description": "密码必须至少包含8个字符，包括大写字母、小写字母和数字。建议使用特殊字符以提高安全性。"
    }