# -*- coding: utf-8 -*-
"""国际化支持模块（F-42）"""

import json
import os
import logging

logger = logging.getLogger(__name__)

# 默认语言
_DEFAULT_LANG = "zh"

# 消息缓存
_messages: dict = {}

# 支持的语言
SUPPORTED_LANGS = {"zh": "中文", "en": "English"}

# 默认消息（内嵌，防止文件缺失）
_FALLBACK_MESSAGES = {
    "zh": {
        "error.invalid_credentials": "邮箱或密码错误",
        "error.inactive_user": "用户已被禁用",
        "error.email_exists": "邮箱已被注册",
        "error.password_weak": "密码不符合安全要求",
        "error.product_not_found": "产品不存在",
        "error.sku_exists": "SKU 已存在",
        "error.import_blocked": "导入被一致性检测错误阻断",
        "error.export_blocked": "导出被一致性检测错误阻断",
        "error.rate_limited": "请求过于频繁，请稍后重试",
        "error.forbidden": "权限不足",
        "error.not_found": "资源不存在",
        "success.login": "登录成功",
        "success.logout": "已登出",
        "success.product_created": "产品创建成功",
        "success.product_updated": "产品更新成功",
        "success.product_deleted": "产品删除成功",
        "success.import_complete": "导入完成",
        "success.export_complete": "导出完成",
    },
    "en": {
        "error.invalid_credentials": "Invalid email or password",
        "error.inactive_user": "User is disabled",
        "error.email_exists": "Email already registered",
        "error.password_weak": "Password does not meet security requirements",
        "error.product_not_found": "Product not found",
        "error.sku_exists": "SKU already exists",
        "error.import_blocked": "Import blocked by consistency errors",
        "error.export_blocked": "Export blocked by consistency errors",
        "error.rate_limited": "Too many requests, please try again later",
        "error.forbidden": "Insufficient permissions",
        "error.not_found": "Resource not found",
        "success.login": "Login successful",
        "success.logout": "Logged out",
        "success.product_created": "Product created successfully",
        "success.product_updated": "Product updated successfully",
        "success.product_deleted": "Product deleted successfully",
        "success.import_complete": "Import completed",
        "success.export_complete": "Export completed",
    },
}


def _load_messages():
    """从文件加载消息（如无可回退到内嵌字典）"""
    global _messages
    if _messages:
        return _messages

    # 尝试从文件加载自定义消息
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "data", "i18n_messages.json"),
    ]
    for p in paths:
        abs_path = os.path.abspath(p)
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                _messages = json.load(f)
                logger.info(f"Loaded i18n messages from {abs_path}")
                return _messages
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    # 回退到内嵌消息
    _messages = _FALLBACK_MESSAGES
    return _messages


def get_message(key: str, lang: str = "zh", **kwargs) -> str:
    """获取本地化消息"""
    msgs = _load_messages()
    lang_msgs = msgs.get(lang, msgs.get(_DEFAULT_LANG, {}))
    template = lang_msgs.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    return template


def _(key: str, lang: str = "zh", **kwargs) -> str:
    """短别名"""
    return get_message(key, lang, **kwargs)
