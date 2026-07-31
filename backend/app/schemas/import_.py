from pydantic import BaseModel
from typing import Optional


class ImportPreviewRequest(BaseModel):
    """导入预览请求"""
    file_id: str
    field_mapping: Optional[dict] = None  # {"上传列名": "系统字段名"}


class ImportExecuteRequest(BaseModel):
    """执行导入请求"""
    file_id: str
    field_mapping: dict  # {"上传列名": "系统字段名"}
    mode: str = "create"  # create 或 update（按 SKU 匹配）


class ImportResult(BaseModel):
    """导入结果"""
    success_count: int
    skip_count: int
    error_count: int
    errors: list[dict]
