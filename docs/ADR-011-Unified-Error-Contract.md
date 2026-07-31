# ADR-011: 统一错误响应契约
**状态:** Accepted
**日期:** 2026-07-31

## 背景

当前 API 错误响应存在**三种不同 JSON 形状**，来源不同：

| 来源 | 形状 | 触发条件 |
|------|------|----------|
| FastAPI 内置处理器 | `{"detail": "msg"}` | 路由中 `raise HTTPException(status_code=400, detail="msg")` |
| `GlobalExceptionHandlerMiddleware` | `{"error": true, "message": "...", "status_code": N, "type": "..."}` | 非 HTTPException 的未捕获异常 |
| 登录频率限制中间件 | `{"error": True, "message": "...", "status_code": 429}` | 登录频率限制触发 |
| 导出 API | `HTTPException(detail={"message": "...", "issues": [...]})` | 一致性错误阻断导出 |

### 根本原因

`GlobalExceptionHandlerMiddleware` 是 `BaseHTTPMiddleware`，运行在 Starlette 中间件层。当路由抛出 `HTTPException` 时，**FastAPI 内置的异常处理器先于中间件捕获**它，生成 `{"detail": "msg"}` 格式的响应。中间件的 `except Exception` 只能捕获**非 HTTPException** 的异常（如 `ValueError`、`KeyError`）。

因此，客户端解析错误时需要处理不兼容的 JSON 形状：

```python
# 客户端需要这样处理（脆弱）
if "detail" in response:
    msg = response["detail"]        # FastAPI 格式
elif "message" in response:
    msg = response["message"]       # 中间件格式
elif "error" in response:
    msg = str(response)             # 未知格式
```

## 选项分析

### 选项 A: 统一为 `{"detail": "msg"}`（FastAPI 原生格式）
| 维度 | 评估 |
|------|------|
| 复杂度 | Low — 最小改动 |
| 信息量 | 低 — 缺少错误码、类型等结构化信息 |
| 兼容性 | 好 — 与 FastAPI 生态一致 |

### 选项 B: 统一为 `{"error": true, "message": "...", "code": "ERROR_CODE", "detail": "..."}`
| 维度 | 评估 |
|------|------|
| 复杂度 | Medium — 需重写异常处理器 |
| 信息量 | 高 — 包含错误码、类型、详情 |
| 客户端友好 | 高 — 统一字段名，易于解析 |

### 选项 C: 使用 RFC 7807 Problem Details
| 维度 | 评估 |
|------|------|
| 复杂度 | High — 需适配现有代码 |
| 信息量 | 最高 — 标准格式 |
| 标准化 | 好 — RFC 标准 |

## 决策

选择**选项 B: 统一错误契约为 `{"error": true, "message": "...", "code": "ERROR_CODE", "detail": "..."}`**。

### 理由
1. **单一形状**：所有 API 错误使用相同字段名，客户端只需一个解析路径
2. **已有基础**：`GlobalExceptionHandlerMiddleware` 和登录频率限制器已使用类似格式，迁移成本低
3. **结构化错误码**：`code` 字段支持客户端程序化处理（如 `RATE_LIMIT_EXCEEDED`、`CONSISTENCY_ERROR`）
4. **弃用中间件方案**：使用 FastAPI 原生 `@app.exception_handler` 装饰器替代 `BaseHTTPMiddleware`，确保所有异常（包括 HTTPException）都经过统一处理

### 统一格式

```json
{
  "error": true,
  "message": "Human-readable summary",
  "code": "CONSISTENCY_ERROR",
  "detail": "Optional structured details (list of issues, field names, etc.)",
  "status_code": 409
}
```

### 实施要点

1. **移除** `GlobalExceptionHandlerMiddleware` 中间件注册（`main.py` 第 132 行）
2. **注册** FastAPI 异常处理器覆盖 HTTPException 和通用 Exception

```python
# main.py — 统一异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail if isinstance(exc.detail, str) else exc.detail.get("message", str(exc.detail)),
            "code": get_error_code(exc),
            "detail": exc.detail if not isinstance(exc.detail, str) else None,
            "status_code": exc.status_code,
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(...)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "code": "INTERNAL_ERROR",
            "detail": None,
            "status_code": 500,
        }
    )
```

3. 登录频率限制器直接使用相同格式（已使用 `{"error": True, "message": "..."}`）

## 影响

### 变容易
- 前端错误处理：单一解析路径
- API 文档：一致的错误响应格式
- 错误追踪：统一日志字段便于检索

### 变困难
- 迁移期间：调用方需同时适配新旧格式（如有外部调用方）
- 现有测试：需要更新断言中的错误格式

### 需要重新审视
- 所有 `raise HTTPException(status_code=N, detail="msg")` 调用点
- 前端 `apiClient` 中的错误处理逻辑
- API 文档中的错误响应示例
