# API参考文档

## 概述

本文档提供跨境产品资料中英对照系统API的完整参考。所有API端点都遵循RESTful设计原则，使用JSON格式进行数据交换。

## 基础信息

**基础URL**: `http://localhost:8000/api/v1`

**认证方式**: JWT Bearer Token

**内容类型**: `application/json`

## 认证API

### 用户注册
**POST** `/auth/register`

注册新用户账户。

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "StrongPass123!",
  "display_name": "用户显示名称"
}
```

**响应**:
```json
{
  "id": "用户ID",
  "email": "user@example.com",
  "display_name": "用户显示名称",
  "role": "viewer",
  "is_active": true,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

**错误响应**:
- `400`: 邮箱已存在或密码不符合要求

### 用户登录
**POST** `/auth/login`

用户登录获取访问令牌。

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```

**响应**:
```json
{
  "access_token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "display_name": "用户显示名称",
    "role": "viewer"
  },
  "force_password_change": false
}
```

**错误响应**:
- `401`: 无效的凭据
- `400`: 用户账户未激活

### 刷新令牌
**POST** `/auth/refresh`

使用刷新令牌获取新的访问令牌。

**请求体**:
```json
{
  "token": "refresh_token_string"
}
```

**响应**:
```json
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "display_name": "用户显示名称",
    "role": "viewer"
  }
}
```

**错误响应**:
- `401`: 无效的刷新令牌或令牌已撤销

### 用户登出
**POST** `/auth/logout`

撤销当前刷新令牌。

**请求头**:
```
Authorization: Bearer <access_token>
```

**请求体**:
```json
{
  "token": "refresh_token_string"
}
```

**响应**:
```json
{
  "message": "Successfully logged out"
}
```

### 撤销所有令牌
**POST** `/auth/logout-all`

撤销用户的所有刷新令牌。

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "message": "All tokens have been revoked"
}
```

### 修改密码
**POST** `/auth/change-password`

修改当前用户密码。

**请求头**:
```
Authorization: Bearer <access_token>
```

**查询参数**:
- `current_password` (string, required): 当前密码
- `new_password` (string, required): 新密码

**响应**:
```json
{
  "message": "Password changed successfully"
}
```

**错误响应**:
- `400`: 当前密码不正确或新密码不符合安全要求
- `401`: 未授权

### 密码强度验证
**POST** `/auth/check-password-strength`

验证密码强度是否符合安全要求。

**请求体**:
```json
{
  "password": "StrongPass123!"
}
```

**响应**:
```json
{
  "is_valid": true,
  "strength": "strong",
  "requirements": {
    "min_length": true,
    "uppercase": true,
    "lowercase": true,
    "number": true,
    "special_char": true
  },
  "score": 95
}
```

**错误响应**:
- `400`: 密码不符合要求

### 密码要求
**GET** `/auth/password-requirements`

获取系统密码策略要求。

**响应**:
```json
{
  "min_length": 8,
  "require_uppercase": true,
  "require_lowercase": true,
  "require_number": true,
  "require_special_char": true,
  "max_length": 128,
  "forbidden_patterns": ["password", "123456", "qwerty"]
}
```

### 获取当前用户
**GET** `/auth/me`

获取当前登录用户的信息。

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "id": "user-id",
  "email": "user@example.com",
  "display_name": "用户显示名称",
  "role": "viewer",
  "is_active": true,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

**错误响应**:
- `401`: 无效的访问令牌

## 产品API

### 获取产品列表
**GET** `/products`

获取产品列表，支持分页和筛选。

**查询参数**:
- `page` (int, 默认1): 页码
- `page_size` (int, 默认20): 每页数量
- `search` (string): 搜索关键词
- `category` (string): 分类筛选
- `brand` (string): 品牌筛选
- `consistency_status` (string): 一致性状态筛选
- `sort_by` (string, 默认`updated_at`): 排序字段
- `sort_order` (string, 默认`desc`): asc/desc

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "items": [
    {
      "id": "product-id",
      "sku": "SKU-001",
      "product_name_zh": "产品中文名称",
      "product_name_en": "Product English Name",
      "category": "分类",
      "brand": "品牌",
      "price": 9.99,
      "currency": "USD",
      "stock": 100,
      "created_at": "2026-01-01T00:00:00",
      "updated_at": "2026-01-01T00:00:00"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

### 创建产品
**POST** `/products`

创建新产品。

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "sku": "SKU-001",
  "product_name_zh": "产品中文名称",
  "product_name_en": "Product English Name",
  "category": "分类",
  "brand": "品牌",
  "description_zh": "产品中文描述",
  "description_en": "Product English Description",
  "price": 9.99,
  "currency": "USD",
  "stock": 100,
  "color_zh": "红色",
  "color_en": "Red",
  "material_zh": "塑料",
  "material_en": "Plastic",
  "weight": 0.5,
  "weight_unit": "kg",
  "origin": "China"
}
```

**响应**:
```json
{
  "id": "product-id",
  "sku": "SKU-001",
  "product_name_zh": "产品中文名称",
  "product_name_en": "Product English Name",
  "category": "分类",
  "brand": "品牌",
  "created_at": "2026-01-01T00:00:00"
}
```

**错误响应**:
- `400`: SKU已存在或必填字段缺失
- `403`: 权限不足

### 获取产品详情
**GET** `/products/{product_id}`

获取指定产品的详细信息。

**路径参数**:
- `product_id` (string): 产品ID

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "id": "product-id",
  "sku": "SKU-001",
  "product_name_zh": "产品中文名称",
  "product_name_en": "Product English Name",
  "category": "分类",
  "brand": "品牌",
  "description_zh": "产品中文描述",
  "description_en": "Product English Description",
  "price": 9.99,
  "currency": "USD",
  "stock": 100,
  "color_zh": "红色",
  "color_en": "Red",
  "material_zh": "塑料",
  "material_en": "Plastic",
  "weight": 0.5,
  "weight_unit": "kg",
  "origin": "China",
  "created_by": "user-id",
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

**错误响应**:
- `404`: 产品不存在

### 更新产品
**PUT** `/products/{product_id}`

更新指定产品信息。

**路径参数**:
- `product_id` (string): 产品ID

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "product_name_zh": "更新后的产品中文名称",
  "product_name_en": "Updated Product English Name",
  "price": 19.99
}
```

**响应**:
```json
{
  "id": "product-id",
  "sku": "SKU-001",
  "product_name_zh": "更新后的产品中文名称",
  "product_name_en": "Updated Product English Name",
  "price": 19.99,
  "updated_at": "2026-01-02T00:00:00"
}
```

**错误响应**:
- `403`: 权限不足
- `404`: 产品不存在

### 删除产品
**DELETE** `/products/{product_id}`

软删除指定产品。

**路径参数**:
- `product_id` (string): 产品ID

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "message": "Product deleted successfully"
}
```

**错误响应**:
- `403`: 权限不足
- `404`: 产品不存在






















## 术语API

### 获取术语列表
**GET** `/terms`

获取术语列表，支持分页和筛选。

**查询参数**:
- `page` (int, 默认1): 页码
- `page_size` (int, 默认20): 每页数量
- `search` (string): 搜索关键词
- `category` (string): 分类筛选
- `is_builtin` (boolean): 筛选内置/自定义

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "items": [
    {
      "id": "term-id",
      "zh": "术语中文",
      "en": "Term English",
      "category": "分类",
      "note": "备注",
      "synonyms": ["同义词1", "同义词2"],
      "platform_amazon": "Amazon术语",
      "platform_alibaba": "阿里巴巴术语",
      "is_builtin": false,
      "created_at": "2026-01-01T00:00:00"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

### 创建术语
**POST** `/terms`

创建新术语。

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "zh": "术语中文",
  "en": "Term English",
  "category": "分类",
  "note": "备注",
  "synonyms": ["同义词1", "同义词2"],
  "platform_amazon": "Amazon术语",
  "platform_alibaba": "阿里巴巴术语"
}
```

**响应**:
```json
{
  "id": "term-id",
  "zh": "术语中文",
  "en": "Term English",
  "category": "分类",
  "created_at": "2026-01-01T00:00:00"
}
```

**错误响应**:
- `400`: 必填字段缺失
- `403`: 权限不足

> ⚠️ **注意**：以下按 ID 操作的单术语端点（GET/PUT/DELETE `/terms/{term_id}`）当前代码中未实现。实际 API 仅支持 `GET /terms`（列表+分页+筛选）和 `POST /terms`（创建）。如需单术语操作，请使用列表接口的 `q` 参数筛选后通过前端处理。










## 导入导出API

### 上传导入文件
**POST** `/import/upload`

上传CSV/Excel文件进行批量导入。

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**请求体**:
- `file`: CSV或Excel文件

**响应**:
```json
{
  "file_id": "file-uuid",
  "filename": "import.csv",
  "total_rows": 100,
  "headers": ["SKU", "中文名称", "英文名称", "品类"],
  "preview_rows": [
    {
      "SKU": "SKU-001",
      "中文名称": "产品中文名称",
      "英文名称": "Product English Name",
      "品类": "分类"
    }
  ],
  "auto_mapping": {
    "SKU": "sku",
    "中文名称": "product_name_zh",
    "英文名称": "product_name_en",
    "品类": "category"
  },
  "available_fields": {
    "sku": "SKU",
    "product_name_zh": "中文名称",
    "product_name_en": "英文名称",
    "category": "品类"
  }
}
```

**错误响应**:
- `400`: 文件格式不支持或文件过大
- `403`: 权限不足

### 预览导入
**POST** `/import/preview`

预览导入结果，检查数据质量。

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "file_id": "file-uuid",
  "field_mapping": {
    "SKU": "sku",
    "中文名称": "product_name_zh",
    "英文名称": "product_name_en",
    "品类": "category"
  }
}
```

**响应**:
```json
{
  "total_rows": 100,
  "mapped_fields": 4,
  "missing_required": [],
  "sku_duplicates": ["SKU-001", "SKU-002"],
  "rows_with_issues": [
    {
      "row": 5,
      "issues": ["必填字段 'SKU' 为空"]
    }
  ],
  "can_proceed": false
}
```

### 执行导入
**POST** `/import/execute`

执行批量导入操作。

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "file_id": "file-uuid",
  "field_mapping": {
    "SKU": "sku",
    "中文名称": "product_name_zh",
    "英文名称": "product_name_en",
    "品类": "category"
  },
  "mode": "create"
}
```

**响应**:
```json
{
  "success_count": 95,
  "skip_count": 3,
  "error_count": 2,
  "errors": [
    {
      "row": 10,
      "error": "Missing required fields (sku or product_name_zh)"
    }
  ],
  "mode": "create"
}
```

### 导出CSV
**POST** `/export/csv`

导出产品数据为CSV格式。

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "platform": "amazon",
  "product_ids": ["product-id-1", "product-id-2"],
  "encoding": "utf-8-sig",
  "skip_on_error": false
}
```

**响应**:
CSV文件流（带UTF-8 BOM）

**错误响应**:
- `400`: 无效的平台参数或一致性错误
- `404`: 未找到产品






## 审计日志API

### 获取审计日志
**GET** `/audit-logs`

获取系统审计日志。

**查询参数**:
- `page` (int, 默认1): 页码
- `page_size` (int, 默认20): 每页数量
- `user_id` (string): 用户ID筛选
- `action` (string): 操作类型筛选
- `resource_type` (string): 资源类型筛选

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "items": [
    {
      "id": "log-id",
      "user_id": "user-id",
      "action": "create",
      "resource_type": "product",
      "resource_id": "product-id",
      "details": {
        "sku": "SKU-001"
      },
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2026-01-01T00:00:00"
    }
  ],
  "total": 1000,
  "page": 1,
  "page_size": 20,
  "total_pages": 50
}
```







#
### GET /api/v1/users/me

获取当前登录用户信息。

**权限**: 所有已认证用户

**响应**:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "User Name",
  "role": "viewer",
  "is_active": true,
  "last_login_at": "2026-01-01T00:00:00",
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```
# 用户管理API

### 获取用户列表
**GET** `/users`

获取系统用户列表（仅管理员）。

**查询参数**:
- `page` (int, 默认1): 页码
- `page_size` (int, 默认20): 每页数量
- `role` (string): 角色筛选

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "items": [
    {
      "id": "user-id",
      "email": "user@example.com",
      "display_name": "用户显示名称",
      "role": "editor",
      "is_active": true,
      "last_login": "2026-01-01T00:00:00",
      "created_at": "2026-01-01T00:00:00"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**错误响应**:
- `403`: 权限不足

### 创建用户
**POST** `/users`

> ✅ **状态：已实现（2026-07-29 P0 交付）**。管理员创建带指定角色的用户，首次登录强制改密。

创建新用户（仅管理员）。

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "email": "newuser@example.com",
  "password": "StrongPass123!",
  "display_name": "新用户",
  "role": "viewer"
}
```

**响应**:
```json
{
  "id": "new-user-id",
  "email": "newuser@example.com",
  "display_name": "新用户",
  "role": "viewer",
  "is_active": true,
  "created_at": "2026-01-01T00:00:00"
}
```

**错误响应**:
- `400`: 邮箱已存在或密码不符合要求
- `403`: 权限不足

### 获取用户详情
**GET** `/users/{user_id}`

获取指定用户信息。

**路径参数**:
- `user_id` (string): 用户ID

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "id": "user-id",
  "email": "user@example.com",
  "display_name": "用户显示名称",
  "role": "editor",
  "is_active": true,
  "last_login": "2026-01-01T00:00:00",
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

**错误响应**:
- `403`: 权限不足（非管理员且非查看自己）
- `404`: 用户不存在

### 更新用户
**PUT** `/users/{user_id}`

> ✅ **状态：已实现（2026-07-29 P0 交付）**。部分更新（PATCH 语义），仅更新提交字段，禁止自降级/自禁用。

更新用户信息或角色（仅管理员）。

**路径参数**:
- `user_id` (string): 用户ID

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "display_name": "更新后的名称",
  "role": "editor",
  "is_active": true
}
```

**响应**:
```json
{
  "id": "user-id",
  "email": "user@example.com",
  "display_name": "更新后的名称",
  "role": "editor",
  "is_active": true,
  "updated_at": "2026-01-02T00:00:00"
}
```

**错误响应**:
- `400`: 无效的角色或不能降级自己
- `403`: 权限不足
- `404`: 用户不存在

### 禁用用户
**DELETE** `/users/{user_id}`

> ✅ **状态：已实现**。软删除（将 is_active 置为 False），同时撤销目标用户所有活跃令牌。禁止管理员禁用自己，已禁用用户幂等返回。

禁用用户账户（软删除，仅管理员）。

**路径参数**:
- `user_id` (string): 用户ID

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "message": "User disabled successfully"
}
```

**错误响应**:
- `400`: 不能禁用自己
- `403`: 权限不足
- `404`: 用户不存在


### 重置用户密码
**POST** `/users/{user_id}/reset-password`

> ✅ **状态：已实现**。管理员为目标用户生成临时密码（16位强密码），设置强制改密标志，撤销所有活跃令牌。v1 在响应中直接返回临时密码。

管理员重置指定用户的密码（强制下次登录改密）。v1 返回临时密码，邮件通知后置。

**路径参数**:
- `user_id` (string): 用户ID

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**响应**:
```json
{
  "temporary_password": "生成的临时密码",
  "message": "Password reset successfully. User must change password on next login."
}
```

### 批量用户操作
**POST** `/users/bulk`

> ✅ **状态：已实现**。支持批量角色变更、启用、禁用（最多 100 条）。先预校验全部操作，全部通过后单事务执行，逐条写审计，失败回滚。

批量执行用户操作（角色变更/启用/停用）。单事务 + 逐条审计 + 错误聚合。

**请求体**:
```json
{
  "operations": [
    {"user_id": "id1", "action": "update_role", "role": "editor"},
    {"user_id": "id2", "action": "disable"}
  ]
}
```
### 更新用户角色
**PUT** `/users/{user_id}/role`

更新用户角色（仅管理员）。

**路径参数**:
- `user_id` (string): 用户ID

**查询参数**:
- `role` (string, required): 新角色（admin/editor/viewer）

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "message": "User role updated to editor"
}
```

**错误响应**:
- `400`: 无效的角色或不能降级自己
- `403`: 权限不足
- `404`: 用户不存在

## 系统监控API

### 健康检查
**GET** `/health`

系统健康检查端点。

**响应**:
```json
{
  "status": "healthy",
  "timestamp": 1704067200.0,
  "database": "connected"
}
```

### 系统指标
**GET** `/metrics`

获取系统运行指标（JSON格式）。

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "system": {
    "cpu_usage": 25.5,
    "memory_usage": 65.2,
    "disk_usage": 45.0
  },
  "application": {
    "active_users": 10,
    "total_products": 150,
    "total_terms": 242,
    "requests_per_minute": 120
  },
  "database": {
    "connections": 5,
    "queries_per_second": 50
  }
}
```

### Prometheus指标
**GET** `/metrics/prometheus`

获取Prometheus格式的系统指标。

**响应**:
```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET", endpoint="/products", status="200"} 1234
http_requests_total{method="POST", endpoint="/products", status="201"} 567

# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET", endpoint="/products", le="0.1"} 1000
http_request_duration_seconds_bucket{method="GET", endpoint="/products", le="0.5"} 1200
http_request_duration_seconds_bucket{method="GET", endpoint="/products", le="1"} 1230
http_request_duration_seconds_bucket{method="GET", endpoint="/products", le="+Inf"} 1234
```

### 关闭状态
**GET** `/shutdown-status`

检查应用关闭状态。

**响应**:
```json
{
  "shutdown_requested": false,
  "active_requests": 5,
  "status": "running"
}
```

## 错误处理

所有API错误响应遵循以下格式：

```json
{
  "detail": "错误描述信息"
}
```

### 常见HTTP状态码

- `200`: 成功
- `201`: 创建成功
- `400`: 请求错误（参数错误、数据验证失败）
- `401`: 未授权（未登录或令牌无效）
- `403`: 禁止访问（权限不足）
- `404`: 资源不存在
- `500`: 服务器内部错误

## 限流说明

API请求有以下限制：
- 未认证请求：每分钟60次
- 已认证请求：每分钟600次
- 文件上传：最大5 login attempts per 60s (login only)

## 数据格式

### 日期时间格式
所有日期时间字段使用ISO 8601格式：`2026-01-01T00:00:00`

### 货币格式
价格字段使用十进制数字格式，货币代码使用ISO 4217标准：`USD`, `CNY`, `EUR`

### 分页格式
分页响应包含以下字段：
- `items`: 数据列表
- `total`: 总记录数
- `page`: 当前页码
- `page_size`: 每页数量
- `total_pages`: 总页数

## 文档更新清单

### ✅ 已补充的端点
1. `/auth/change-password` - 修改密码（新增）
2. `/shutdown-status` - 关闭状态（新增）
3. `/metrics/prometheus` - Prometheus指标（新增）
4. `/audit-logs/{log_id}` - 审计日志详情（新增）

### ✅ 已完善的端点
1. `/auth/logout-all` - 撤销所有令牌（已存在）
2. `/auth/password-requirements` - 密码要求（已存在）
3. `/auth/check-password-strength` - 密码强度检查（已存在）


