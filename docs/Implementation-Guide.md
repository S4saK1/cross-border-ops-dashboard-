# 架构问题修复实施指南

## 概述
本指南详细说明如何实施四个架构问题的修复方案，包括代码示例、配置说明和测试方法。

## 1. Token存储迁移到httpOnly Cookie

### 后端修改

#### 1.1 修改登录接口
```python
# backend/app/api/auth.py
from fastapi import Response

@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(UserProfile).filter(UserProfile.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    
    # 设置httpOnly Cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # 仅HTTPS传输
        samesite="strict",  # CSRF防护
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/"
    )
    
    # 生成CSRF Token（非httpOnly，前端可读取）
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # 前端可读取
        secure=True,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role},
    )
```

#### 1.2 修改Token验证逻辑
```python
# backend/app/core/security.py
from fastapi import Request

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    # 优先从Cookie中获取Token
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        token = cookie_token
    
    payload = decode_token(token)
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
    return user
```

#### 1.3 添加CSRF防护中间件
```python
# backend/app/middleware/csrf.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 只检查状态修改请求
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # 排除特定端点（如登录、注册）
            if request.url.path in ["/api/v1/auth/login", "/api/v1/auth/register"]:
                return await call_next(request)
            
            # 从Cookie中获取CSRF Token
            csrf_cookie = request.cookies.get("csrf_token")
            if not csrf_cookie:
                raise HTTPException(status_code=403, detail="CSRF token missing")
            
            # 从请求头中获取CSRF Token
            csrf_header = request.headers.get("X-CSRF-Token")
            if not csrf_header or csrf_header != csrf_cookie:
                raise HTTPException(status_code=403, detail="CSRF token invalid")
        
        return await call_next(request)
```

### 前端修改

#### 1.1 修改API客户端
```typescript
// frontend/src/lib/api.ts
const API_BASE = '/api/v1';

async function request(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  };
  
  // 添加CSRF Token到请求头
  if (typeof window !== 'undefined') {
    const csrfToken = getCookie('csrf_token');
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }
  
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  // 启用Cookie自动携带
  const fetchOptions: RequestInit = {
    ...options,
    headers,
    credentials: 'include',  // 关键：自动携带Cookie
  };

  const res = await fetch(`${API_BASE}${path}`, fetchOptions);
  
  if (res.status === 401) {
    // 尝试刷新Token
    const refreshed = await refreshToken();
    if (refreshed) {
      // 重试原请求
      return fetch(`${API_BASE}${path}`, fetchOptions);
    }
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  
  if (res.headers.get('content-type')?.includes('text/csv')) {
    return res;
  }
  
  return res.json();
}

// 辅助函数：获取Cookie值
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null;
  }
  return null;
}

// Token刷新函数
async function refreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    return response.ok;
  } catch {
    return false;
  }
}
```

#### 1.2 修改登录页面
```typescript
// frontend/src/app/login/page.tsx
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setError('');
  setLoading(true);
  
  try {
    const data = await auth.login(email, password);
    // 不再手动存储Token，Cookie会自动设置
    // localStorage.setItem('user', JSON.stringify(data.user));
    router.push('/');
  } catch (err: any) {
    setError(err.message || '登录失败');
  } finally {
    setLoading(false);
  }
};
```

## 2. 审计日志中间件

### 2.1 创建审计日志中间件
```python
# backend/app/middleware/audit.py
import time
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import SessionLocal
from app.models.audit import AuditLog

class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.excluded_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 只记录状态修改请求
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            return await call_next(request)
        
        # 排除特定路径
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取请求信息
        user_id = await self._get_user_id(request)
        resource_type = self._extract_resource_type(request.url.path)
        resource_id = self._extract_resource_id(request.url.path)
        
        # 获取请求体（仅对POST/PUT请求）
        body = None
        if request.method in ["POST", "PUT"]:
            try:
                body = await request.body()
                body = body.decode('utf-8') if body else None
            except:
                body = None
        
        # 执行请求
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 创建审计日志
        await self._create_audit_log(
            user_id=user_id,
            action=request.method,
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "body": self._sanitize_body(body),
                "status_code": response.status_code,
                "process_time": process_time,
            },
            ip_address=self._get_client_ip(request),
        )
        
        return response
    
    async def _get_user_id(self, request: Request) -> str:
        """从请求中提取用户ID"""
        try:
            # 尝试从Cookie中获取Token
            token = request.cookies.get("access_token")
            if not token:
                # 尝试从Authorization头获取
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
            
            if token:
                from app.core.security import decode_token
                payload = decode_token(token)
                return payload.get("sub", "anonymous")
        except:
            pass
        
        return "anonymous"
    
    def _extract_resource_type(self, path: str) -> str:
        """从URL路径提取资源类型"""
        if "/products" in path:
            return "product"
        elif "/terms" in path:
            return "term"
        elif "/users" in path:
            return "user"
        elif "/auth" in path:
            return "auth"
        elif "/import" in path:
            return "import"
        elif "/export" in path:
            return "export"
        else:
            return "unknown"
    
    def _extract_resource_id(self, path: str) -> str:
        """从URL路径提取资源ID"""
        parts = path.strip('/').split('/')
        # 检查是否有UUID格式的ID
        for part in parts:
            if len(part) == 36 and part.count('-') == 4:
                return part
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 尝试从各种头部获取真实IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _sanitize_body(self, body: str) -> str:
        """清理请求体中的敏感信息"""
        if not body:
            return None
        
        # 移除密码等敏感字段
        sensitive_fields = ["password", "token", "secret", "key"]
        try:
            import json
            data = json.loads(body)
            for field in sensitive_fields:
                if field in data:
                    data[field] = "***"
            return json.dumps(data)
        except:
            return "***"
    
    async def _create_audit_log(self, **kwargs):
        """异步创建审计日志"""
        try:
            db = SessionLocal()
            try:
                audit_log = AuditLog(**kwargs)
                db.add(audit_log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            # 日志记录失败不应影响正常请求
            print(f"Failed to create audit log: {e}")
```

### 2.2 添加审计日志查询API
```python
# backend/app/api/audit.py
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.audit import AuditLog
from app.core.deps import require_admin

router = APIRouter()

@router.get("/logs")
async def get_audit_logs(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    action: Optional[str] = Query(None, description="操作类型"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """查询审计日志（仅管理员）"""
    query = db.query(AuditLog)
    
    # 应用过滤条件
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    # 计算总数
    total = query.count()
    
    # 分页查询
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "logs": [log.to_dict() for log in logs]
    }
```

## 3. 导出流程一致性检测

### 3.1 修改导出API
```python
# backend/app/api/export.py
from fastapi import HTTPException
from app.core.consistency import ConsistencyEngine, get_consistency_status

@router.post("/csv")
def export_csv(
    req: ExportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_reviewer),
):
    platform = req.platform
    product_ids = req.product_ids
    
    if platform not in ("amazon", "alibaba"):
        raise HTTPException(status_code=400, detail="Platform must be 'amazon' or 'alibaba'")
    
    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.is_deleted == False,
    ).all()
    
    if not products:
        raise HTTPException(status_code=404, detail="No products found")
    
    # 执行一致性检查
    consistency_engine = ConsistencyEngine(db)
    all_issues = []
    
    for product in products:
        issues = consistency_engine.check_product(product)
        all_issues.extend(issues)
    
    # 检查是否有ERROR级别问题
    error_issues = [i for i in all_issues if i["severity"] == "ERROR"]
    warning_issues = [i for i in all_issues if i["severity"] == "WARNING"]
    
    if error_issues:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "数据一致性检查失败",
                "errors": error_issues,
                "warnings": warning_issues,
                "total_errors": len(error_issues),
                "total_warnings": len(warning_issues),
                "suggestion": "请先修复数据一致性问题再导出"
            }
        )
    
    # 执行导出
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    
    if platform == "amazon":
        # ... 现有导出逻辑 ...
        pass
    else:
        # ... 现有导出逻辑 ...
        pass
    
    output.seek(0)
    csv_content = output.getvalue()
    
    # 添加警告信息到响应头
    response_headers = {
        "Content-Disposition": f"attachment; filename={platform}_export.csv",
        "X-Consistency-Warnings": str(len(warning_issues)),
    }
    
    if warning_issues:
        response_headers["X-Consistency-Warning-Details"] = json.dumps(warning_issues[:5])  # 只返回前5个警告
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers=response_headers,
    )
```

## 4. CSV导出注入防护修复

### 4.1 重写sanitize_csv_cell函数
```python
# backend/app/utils/csv_utils.py
def sanitize_csv_cell(value: str) -> str:
    """
    防止 CSV 公式注入和格式攻击
    
    处理策略：
    1. 检测并处理公式注入字符
    2. 转义换行符防止格式破坏
    3. 处理引号字符防止字段逃逸
    4. 确保UTF-8编码安全
    
    Args:
        value: 需要清洗的单元格值
        
    Returns:
        清洗后的安全值
    """
    if not isinstance(value, str):
        return str(value)
    
    # 1. 处理公式注入字符
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        value = "'" + value
    
    # 2. 处理换行符（防止格式破坏）
    if "\n" in value or "\r" in value:
        value = value.replace("\n", "\\n").replace("\r", "\\r")
        if not value.startswith("'"):
            value = "'" + value
    
    # 3. 处理引号字符（防止字段逃逸）
    if '"' in value:
        value = value.replace('"', '\\"')
        if not value.startswith("'"):
            value = "'" + value
    
    return value
```

### 4.2 创建测试用例
```python
# backend/tests/test_csv_utils.py
import pytest
from app.utils.csv_utils import sanitize_csv_cell

class TestSanitizeCsvCell:
    def test_formula_injection(self):
        """测试公式注入防护"""
        test_cases = [
            ("=SUM(A1:A10)", "'=SUM(A1:A10)"),
            ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
            ("-2+3", "'-2+3"),
            ("@SUM(A1:A10)", "'@SUM(A1:A10)"),
        ]
        for input_val, expected in test_cases:
            assert sanitize_csv_cell(input_val) == expected
    
    def test_newline_injection(self):
        """测试换行符注入防护"""
        test_cases = [
            ("line1\nline2", "'line1\\nline2"),
            ("line1\r\nline2", "'line1\\r\\nline2"),
            ("line1\rline2", "'line1\\rline2"),
        ]
        for input_val, expected in test_cases:
            assert sanitize_csv_cell(input_val) == expected
    
    def test_quote_injection(self):
        """测试引号注入防护"""
        test_cases = [
            ('value with "quotes"', "'value with \\"quotes\\""),
            ('"quoted value"', "'\\"quoted value\\""),
            ("value with 'single quotes'", "value with 'single quotes'"),
        ]
        for input_val, expected in test_cases:
            assert sanitize_csv_cell(input_val) == expected
    
    def test_normal_values(self):
        """测试正常值"""
        test_cases = [
            ("normal text", "normal text"),
            ("12345", "12345"),
            ("", ""),
            (None, "None"),
        ]
        for input_val, expected in test_cases:
            assert sanitize_csv_cell(input_val) == expected
```

## 部署和配置

### 1. 环境变量配置
```env
# .env文件
SECRET_KEY=your-secure-secret-key-here
DATABASE_URL=sqlite:///./bilingual_cms.db
ENABLE_MONITORING=true
CSRF_PROTECTION=true
AUDIT_LOGGING=true
```

### 2. 中间件配置
```python
# backend/app/main.py
from app.middleware.csrf import CSRFMiddleware
from app.middleware.audit import AuditMiddleware

# 添加中间件
app.add_middleware(CSRFMiddleware)
app.add_middleware(AuditMiddleware)
```

### 3. 数据库迁移
```bash
# 创建审计日志表迁移
alembic revision --autogenerate -m "add_audit_logs_table"
alembic upgrade head
```

## 测试验证

### 1. 单元测试
```bash
# 运行所有测试
cd backend
pytest tests/ -v

# 运行特定测试
pytest tests/test_csv_utils.py -v
pytest tests/test_auth_flow.py -v
```

### 2. 集成测试
```bash
# 测试登录流程
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123!"}'

# 测试CSRF防护
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: invalid-token" \
  -d '{"name": "Test Product"}'
```

### 3. 安全测试
```python
# 安全测试脚本
def test_xss_protection():
    """测试XSS攻击防护"""
    # 模拟XSS攻击尝试
    malicious_script = "<script>alert('xss')</script>"
    # 验证脚本被正确转义
    assert "<script>" not in sanitize_csv_cell(malicious_script)

def test_csrf_protection():
    """测试CSRF攻击防护"""
    # 模拟CSRF攻击尝试
    # 验证缺少CSRF Token的请求被拒绝
    pass
```

## 监控和维护

### 1. 监控指标
- 认证成功率
- 审计日志写入延迟
- CSV导出性能
- 安全事件统计

### 2. 日志分析
- 定期分析审计日志
- 监控异常操作模式
- 生成安全报告

### 3. 定期维护
- 清理过期审计日志
- 轮换Secret Key
- 更新安全规则