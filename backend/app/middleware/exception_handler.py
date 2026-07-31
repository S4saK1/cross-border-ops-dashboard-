from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from typing import Any
import sys

logger = logging.getLogger(__name__)


class GlobalExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    全局异常处理器中间件
    - 标准化错误响应格式
    - 防止内部栈追踪暴露
    - 记录异常信息用于调试
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self.handle_exception(request, exc)
    
    async def handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """处理异常并返回标准化响应"""
        
        # 记录异常信息（用于调试，但不暴露给客户端）
        logger.error(
            f"Unhandled exception: {str(exc)}",
            extra={
                "request_method": request.method,
                "request_url": str(request.url),
                "request_headers": {k: ("***REDACTED***" if k.lower() in ("authorization", "cookie") else v) for k, v in request.headers.items()},
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc()
            }
        )
        
        # 根据异常类型返回不同的响应
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": True,
                    "message": exc.detail,
                    "status_code": exc.status_code,
                    "type": "http_error"
                }
            )
        elif isinstance(exc, ValueError):
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "message": f"Invalid input: {str(exc)}",
                    "status_code": 400,
                    "type": "validation_error"
                }
            )
        elif isinstance(exc, KeyError):
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "message": f"Missing required field: {str(exc)}",
                    "status_code": 400,
                    "type": "missing_field_error"
                }
            )
        else:
            # 对于未知异常，返回通用错误信息
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Internal server error",
                    "status_code": 500,
                    "type": "internal_error",
                    # 在生产环境中不暴露详细信息
                    "debug_info": {
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc)
                    } if self._is_debug_mode() else None
                }
            )
    
    def _is_debug_mode(self) -> bool:
        """检查是否为调试模式"""
        try:
            from app.config import settings
            return getattr(settings, "DEBUG", False)
        except:
            return False