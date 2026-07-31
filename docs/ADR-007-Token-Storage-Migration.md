# ADR-007: JWT 认证 — httpOnly Cookie + Bearer Token 双通道
**状态:** Accepted
**日期:** 2024-01-15
**更新:** 2026-07-31 — K1 cookie 迁移已激活

## 背景
当前系统将JWT Token存储在前端localStorage中，存在以下安全风险：
1. XSS攻击可直接读取localStorage中的Token
2. Token容易被恶意脚本窃取
3. 不符合现代Web应用安全最佳实践

根据技术债评估报告#5，需要将Token存储迁移到更安全的httpOnly Cookie方案。

## 选项分析

### 选项A: 继续使用localStorage
| 维度 | 评估 |
|------|------|
| 复杂度 | Low |
| 成本 | 无额外开发成本 |
| 可扩展性 | 差 - 安全性问题会随系统规模扩大而加剧 |

**优点：**
- 实现简单，无需修改现有代码
- 前端可直接访问Token，便于调试

**缺点：**
- XSS攻击风险高
- 不符合OWASP安全指南
- 无法利用浏览器安全机制

### 选项B: 迁移到httpOnly Cookie
| 维度 | 评估 |
|------|------|
| 复杂度 | Medium |
| 成本 | 需要修改前后端代码 |
| 可扩展性 | 优 - 安全性高，符合最佳实践 |

**优点：**
- httpOnly Cookie无法被JavaScript访问，有效防止XSS攻击
- 可设置Secure标志，确保仅通过HTTPS传输
- 可设置SameSite属性，提供CSRF防护
- 符合现代Web应用安全标准

**缺点：**
- 需要修改前端Token获取逻辑
- 需要实现CSRF防护机制
- 调试相对困难

### 选项C: 使用内存存储 + 短期Token
| 维度 | 评估 |
|------|------|
| 复杂度 | High |
| 成本 | 需要频繁刷新Token |
| 可扩展性 | 中 - 安全性好但用户体验受影响 |

**优点：**
- Token不持久化，安全性最高
- 无XSS风险

**缺点：**
- 用户需要频繁重新登录
- 实现复杂，需要自动刷新机制
- 用户体验差

## 决策
推荐**选项B: 迁移到httpOnly Cookie**，理由如下：
1. **安全性提升显著**：有效防止XSS攻击，符合OWASP安全指南
2. **实现成本适中**：前后端改动可控，不影响现有功能
3. **用户体验无影响**：用户无需改变登录流程
4. **符合行业标准**：现代Web应用普遍采用此方案

## 具体实现方案

### 后端修改
1. **Token生成与响应**
   - 登录接口返回Token时，同时设置httpOnly Cookie
   - Cookie属性：`HttpOnly`, `Secure`, `SameSite=Strict`
   - 设置合理的过期时间（与Token过期时间一致）

2. **Token验证**
   - 从Cookie中读取Token进行验证
   - 保留Authorization Header作为备选方案（向后兼容）

3. **CSRF防护**
   - 实现CSRF Token机制
   - 所有状态修改请求（POST/PUT/DELETE）需要携带CSRF Token

### 前端修改
1. **移除localStorage操作**
   - 删除`setToken()`, `getToken()`, `clearToken()`函数
   - 修改登录逻辑，不再手动存储Token

2. **API请求修改**
   - 所有请求自动携带Cookie（浏览器默认行为）
   - 添加CSRF Token到请求头

3. **状态管理**
   - 用户状态从Cookie或会话中获取
   - 登出时清除Cookie

### 安全考虑
1. **Cookie安全配置**
   ```python
   # FastAPI示例
   response.set_cookie(
       key="access_token",
       value=token,
       httponly=True,
       secure=True,
       samesite="strict",
       max_age=3600  # 1小时
   )
   ```

2. **CSRF防护实现**
   - 生成随机CSRF Token存储在Cookie中
   - 前端从Cookie读取CSRF Token（非httpOnly）
   - 所有状态修改请求在Header中携带CSRF Token
   - 后端验证CSRF Token有效性

3. **传输安全**
   - 强制HTTPS（生产环境）
   - 设置HSTS头部
   - 定期轮换Secret Key

## 当前实施状态（2026-07-31 更新）

K1 cookie 迁移**已完成并激活**。当前认证架构：

### 后端 (backend/app/core/security.py)
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
```
- `auto_error=False`：不强制要求 Bearer token，允许 cookie-only 认证
- `get_current_user` 双通道策略：优先 Bearer token，回退到 `access_token` cookie
- `set_auth_cookies()` / `clear_auth_cookies()` 管理 httpOnly cookie

### Cookie 配置
| 属性 | 开发 | 生产 |
|------|------|------|
| `httponly` | True | True |
| `secure` | False | True (自动) |
| `samesite` | lax | lax |
| `path` (access) | / | / |
| `path` (refresh) | /api/v1/auth | /api/v1/auth |

### CSRF 防护
`CSRFTokenMiddleware` 已注册（`main.py` 第 133 行），为状态修改请求提供 CSRF Token 验证。

### 注销流程
- `POST /api/v1/auth/logout`：黑名单 refresh token + 清除 cookies
- `POST /api/v1/auth/logout-all`：撤销用户所有 token（Redis 黑名单 + token_version 递增）

## 影响
### 变容易
- XSS攻击防护能力显著提升
- 符合安全合规要求
- 系统安全性得到行业认可

### 变困难
- 前端调试Token相对困难
- 需要处理跨域请求的Cookie配置
- 需要实现CSRF防护机制

### 需要重新审视的部分
- 所有使用Token的前端代码
- API认证逻辑
- 跨域CORS配置
- 测试用例中的Token处理

## 测试验证方案
1. **单元测试**
   - Cookie设置正确性测试
   - CSRF Token验证测试
   - Token过期处理测试

2. **集成测试**
   - 登录流程完整性测试
   - API请求认证测试
   - 登出流程测试

3. **安全测试**
   - XSS攻击模拟测试
   - CSRF攻击防护测试
   - Token窃取防护测试

4. **兼容性测试**
   - 不同浏览器Cookie支持测试
   - 移动端适配测试
   - 向后兼容性测试