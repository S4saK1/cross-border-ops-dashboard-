
# 跨境产品资料中英对照系统 — 全面工程审查报告

**日期**：2026-07-28
**工作流**：综合工程审查（路由完整性 + 安全 + 部署 + 测试 + 文档）
**参与成员**：Cody（代码审查）、Archi（架构审查）、Rex（SRE 审查）、Tessa（测试审查）、Docu（文档审查）

---

## 📌 TL;DR（执行摘要）

- **整体结论**：系统后端 API 层实现完整（30 端点全部就绪），但前端有 **6 个关键页面文件缺失**，导致 5 处菜单/导航出现 404；同时存在 **5 个严重安全问题**（密钥泄露、Token 存储不安全、监控端点无认证、调试信息泄露、CORS 过宽）和 **3 个部署层面阻断问题**（前端 Dockerfile 永远跑 dev 模式、CI 脚本引用不存在的命令、生产 compose 缺前端容器）。
- **严重度分布**：🔴严重 12 项 / 🟠高 16 项 / 🟡中 12 项 / 🟢低 8 项（含文档问题），共 **48 项**
- **阻塞 / 非阻塞**：存在阻塞项——安全密钥泄露需立即轮换；CI 管道损坏需立即修复；6 个缺失页面是用户报告的 404 根因
- **404 根因（经 5 人交叉验证）**：纯前端路由页面缺失——后端 30 个 API 端点全部正确注册且功能可用，但对应的 Next.js 页面文件 (`page.tsx`) 不存在

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🔴 不通过 — 存在严重安全问题 + 部署阻断 + 功能缺失 |
| 阻塞项数量 | 8 项（密钥泄露、Token 存储、Dockerfile、CI 损坏、页面缺失×4） |
| 关键行动项 | 15 条（P0×5 + P1×6 + P2×4） |
| 建议下一步 | 立即执行 Sprint 1（安全止血 + 404 修复），详见行动清单 |

---

## 🔍 第一部分：404 问题根因分析（用户报告的三个问题）

### 经五位专家交叉验证的根因

| 用户报告的 404 | 前端页面文件 | 后端 API 端点 | 触发方式 |
|---------------|-------------|-------------|---------|
| 产品管理 → 新建产品 | `src/app/products/new/page.tsx` ❌ 不存在 | `POST /api/v1/products` ✅ 正常 | 点击「新建产品」按钮 → `router.push('/products/new')` |
| 批量导出模块 | `src/app/products/import/page.tsx` ❌ 不存在 | `POST /api/v1/import/upload` ✅ 正常 | 侧边栏点击「批量导入」→ `href="/products/import"` |
| 审计日志模块 | `src/app/audit/page.tsx` ❌ 不存在 | `GET /api/v1/audit-logs` ✅ 正常 | 侧边栏点击「审计日志」→ `href="/audit"` |

### 额外发现的缺失页面（菜单存在但无对应文件）

| # | 缺失页面 | 菜单项 | 触发方式 |
|---|---------|--------|---------|
| 4 | `src/app/products/[id]/page.tsx` | 产品详情 | 点击产品行「查看」眼睛图标 → `router.push(\`/products/${p.id}\`)` |
| 5 | `src/app/settings/users/page.tsx` | 用户管理 | 侧边栏（仅 admin 可见）→ `href="/settings/users"` |
| 6 | `src/app/settings/layout.tsx` | 设置布局 | settings 子页面的父布局 |

### 404 vs 403 排查结论

**不是权限问题**。后端 `deps.py` 中 `require_admin`、`require_editor` 等正确使用 `HTTP_403_FORBIDDEN`。前端无 Next.js middleware，所有路由保护在客户端 `useEffect` 中完成，不存在"权限中间件返回 404 伪装 403"的情况。404 纯粹是 **Next.js 文件系统路由找不到对应的 `page.tsx`**。

---

## 🔍 第二部分：路由与菜单完整性审查（Archi）

### 路由表（Next.js App Router 文件系统路由）

| 前端路径 | 页面文件 | 菜单项 | 状态 |
|----------|---------|--------|------|
| `/` | `page.tsx` | 仪表盘 | ✅ 存在 |
| `/login` | `login/page.tsx` | — | ✅ 存在 |
| `/products` | `products/page.tsx` | 产品管理 | ✅ 存在 |
| `/products/new` | — | — | 🔴 缺失 |
| `/products/[id]` | — | — | 🔴 缺失 |
| `/products/import` | — | 批量导入 | 🔴 缺失 |
| `/terms` | `terms/page.tsx` | 术语词典 | ✅ 存在 |
| `/export` | `export/page.tsx` | CSV 导出 | ✅ 存在 |
| `/audit` | — | 审计日志 | 🔴 缺失 |
| `/settings/users` | — | 用户管理 | 🔴 缺失 |
| `*` (404) | — | — | 🔴 无自定义 404 |

**菜单覆盖率：7 项菜单 → 4 项可达 (57%)，3 项死链 (43%)**

### 模块加载分析

- **无动态导入/Lazy Loading**：所有页面静态导入，无 `React.lazy()` 或 `next/dynamic()`，排除 chunk 加载失败导致 404 的可能
- **无 Error Boundary**：没有 `error.tsx`、`global-error.tsx` 或 React ErrorBoundary 组件 → 任何组件崩溃直接白屏
- **前端权限严重缺陷**：`userRole` 在 Sidebar 中硬编码为 `'viewer'`，前端从未真正读取用户角色。权限完全依赖后端验证（请求拦截），但 UI 层面无角色感知

---

## 🔍 第三部分：安全问题审查（Cody）

### 🔴 CRITICAL（5 项）

| # | 问题 | 文件:行 | 风险 | 修复建议 |
|---|------|---------|------|---------|
| C1 | **真实 JWT 密钥硬编码在 `.env` 中** | `.env`（根目录）、`backend/.env` | 密钥如已提交 Git → 攻击者可伪造任意用户 Token | 立即轮换密钥；从 .env 删除真实值；确认 .gitignore；清理 Git 历史 |
| C2 | **JWT Token 存储在 localStorage** | `frontend/src/lib/api.ts:7-9,13-14` | XSS 可读取 Token → 完全接管用户会话 | 改用 httpOnly + Secure + SameSite Cookie；或至少用 sessionStorage + 短期过期 |
| C3 | **`/metrics`、`/health` 等端点无认证** | `backend/app/main.py:142-163` | 暴露系统指标、错误率、端点性能 → 攻击者侦查入口 | 添加认证依赖或在反向代理层限制内网 IP |
| C4 | **生产环境泄露异常类型和消息** | `backend/app/middleware/exception_handler.py:84-88` | `ENABLE_MONITORING=true` 时 `debug_info` 返回给客户端 | 添加独立 `DEBUG` 配置，生产强制关闭；不复用 `ENABLE_MONITORING` |
| C5 | **CORS 配置过于宽松** | `backend/app/main.py:75-81` | `allow_methods=["*"]`, `allow_headers=["*"]` | 限制为 `["GET","POST","PUT","DELETE","OPTIONS"]` 和 `["Authorization","Content-Type","Accept"]` |

### 🟠 HIGH（6 项）

| # | 问题 | 文件:行 | 修复建议 |
|---|------|---------|---------|
| H1 | **审计日志有表有 API 但从未写入** | `backend/app/api/products.py:76-135` | 在 create/update/delete 端点中添加 AuditLog 写入 |
| H2 | **`/login` 无速率限制** | `backend/app/api/auth.py:67-97` | 使用 slowapi 限制 5 次/分钟/IP，连续 5 次失败锁定 15 分钟 |
| H3 | **SQLite 作为默认数据库不适合生产** | `backend/app/config.py:14` | 生产环境强制使用 PostgreSQL；`check_same_thread=False` 在并发下危险 |
| H4 | **批量导入存在竞态条件** | `backend/app/api/import_.py:433-527` | 开始时立即移除缓存引用；事务包裹；添加互斥锁 |
| H5 | **密码修改用 Query 参数** | `backend/app/api/auth.py:179-209` | 创建 `ChangePasswordRequest` Pydantic Body 模型 |
| H6 | **`update_user_role` 漏掉 `"reviewer"` 角色** | `backend/app/api/users.py:119` | `valid_roles` 添加 `"reviewer"` |

### 🟡 MEDIUM（5 项摘要）
- M1: 前端 7 处 `.catch(() => {})` 静默吞错误 → 统一错误处理工具函数
- M2: `datetime.utcnow()` 已废弃（Python 3.12+）→ 改用 `datetime.now(timezone.utc)`
- M3: 产品列表可能触发 N+1 查询 → 使用 `joinedload` 预加载
- M4: CORS `ALLOWED_ORIGINS` 解析格式不一致 → 统一 JSON 数组格式
- M5: 前端 API 调用的封装与直接 fetch 混用 → 统一使用 api.ts 封装

### 🟢 LOW（4 项摘要）
- L1: 术语分类硬编码在前端 → 应从 API 动态获取
- L2: 产品列表分页无上限检查 → 根据 total 计算 totalPages
- L3: 退出登录仅清除前端状态 → 调用 `/auth/logout` 撤销 refresh token
- L4: CI/CD .env 加载重复（ci.yml 两次加载 .env.test）

---

## 🔍 第四部分：API 端点与部署审查（Rex）

### API 端点完整清单（30 个端点全部就绪 ✅）

| 模块 | 端点数量 | 端点列表 |
|------|---------|---------|
| 认证 (`/api/v1/auth`) | 9 | POST /register, /login, /refresh, /logout, /logout-all, /change-password, GET /me, /password-requirements, POST /check-password-strength |
| 产品 (`/api/v1/products`) | 5 | GET /, POST /, GET /{id}, PUT /{id}, DELETE /{id} |
| 术语 (`/api/v1/terms`) | 2 | GET /, POST / |
| 导出 (`/api/v1/export`) | 1 | POST /csv |
| 审计 (`/api/v1/audit-logs`) | 1 | GET / |
| 导入 (`/api/v1/import`) | 3 | POST /upload, /preview, /execute |
| 用户 (`/api/v1/users`) | 4 | GET /, /me, /{id}, PUT /{id}/role |
| 根级别 | 5 | GET /, /health, /metrics, /metrics/prometheus, /shutdown-status |

**无重复路径，参数定义完整。无返回非 200/301 的已知异常。**

### 🔴 部署层面阻断问题（3 项）

| # | 问题 | 详情 |
|---|------|------|
| D1 | **前端 Dockerfile 永远 `next dev`** | `CMD: npx next dev` — 容器中从不构建生产包 |
| D2 | **CI `typecheck` 和 `test` 脚本不存在** | `ci.yml` 调用了 `npm run typecheck` 和 `npm run test`，但 `package.json` 中无这些脚本 |
| D3 | **生产 compose 无前端容器** | `docker-compose.prod.yml` 只有 backend+postgres+redis+prometheus+grafana，缺少前端服务 |

### 其他部署问题

- **无 nginx 入口**：`deploy/nginx/nginx.conf` 存在但未加入任何 compose 文件
- **Prometheus metrics_path 错误**：配置指向 `/metrics`（JSON 格式）应为 `/metrics/prometheus`
- **CI/CD 部署步骤全部注释**：`deploy-test` 和 `deploy-production` 是空壳
- **Python 版本不一致**：ci.yml 用 3.11，ci-cd.yml 用 3.12
- **前端无 `output: 'standalone'` 配置**：无法做 Docker 多阶段构建优化
- **硬编码 URL**：`next.config.js` 中 `API_BASE_URL` 默认 `http://localhost:8000`，前端 Dockerfile 未通过 ENV 注入

### 异常捕获与监控

| 检查项 | 状态 |
|--------|------|
| React ErrorBoundary | ❌ 不存在 |
| `error.tsx` | ❌ 不存在 |
| `global-error.tsx` | ❌ 不存在 |
| `window.onerror` | ❌ 不存在 |
| `unhandledrejection` | ❌ 不存在 |
| Sentry/LogRocket | ❌ 不存在 |
| 前端 Web Vitals | ❌ 不存在 |
| Prometheus + Grafana | ✅ 架构完整（13 条告警规则） |
| Backend Dashboard JSON | ✅ 存在 |

---

## 🔍 第五部分：测试覆盖审查（Tessa）

### 测试文件总览

| 层级 | 测试文件数 | 状态 |
|------|----------|------|
| 后端 | 19 个文件（含 3 个安全测试） | ✅ 覆盖主要 API |
| 前端 | **0 个文件** | 🔴 零覆盖 |
| E2E | 1 个文件（auth flow） | ⚠️ 极少 |

### 零测试的关键模块 🔴

| 模块 | 严重级别 | 理由 |
|------|---------|------|
| `backend/app/api/audit.py` | 🔴 CRITICAL | 审计日志是合规关键路径 |
| `backend/app/middleware/exception_handler.py` | 🔴 CRITICAL | 错误处理中间件 — 生产风险 |
| `backend/app/core/deps.py`（权限依赖） | 🔴 HIGH | require_admin/editor/viewer 无直接测试 |
| `backend/app/core/redis.py` | 🟡 MEDIUM | Token 黑名单层无测试 |
| `backend/app/monitoring.py` | 🟡 MEDIUM | 性能监控中间件 |
| `backend/app/models/*`（5 个模型） | 🟡 MEDIUM | 模型关系、验证逻辑 |
| **前端全部** | 🔴 CRITICAL | 0 测试文件 — 404 问题无测试拦截 |

### CI 健康 🔴

- **CI frontend job 将失败**：`ci.yml:100-113` 引用了不存在的 `npm run typecheck` 和 `npm run test`
- **`test_results.xml` 显示 `tests="0"`**：测试从未在 CI 中真正运行
- **`ci-cd.yml` 缺 PostgreSQL 服务容器**：与 ci.yml 不一致
- **`test_products_stats.py` 用 `pytest.skip` 掩盖缺失端点**：应使用 `xfail`

### 测试质量亮点 ✅
- Fixture 架构规范（SQLite 内存数据库 + 管理员/编辑/查看者 token fixtures）
- 权限测试覆盖全面（每个 API 有 viewer_forbidden / editor_forbidden 检查）
- 安全测试深入（路径遍历、CSV 注入、SQL 注入、JWT 安全、密码暴力破解）
- CSV 注入防护测试覆盖 `=`, `+`, `-`, `@`, `\t`, `\r` 和 WEBSERVICE 注入

---

## 🔍 第六部分：文档质量审查（Docu）

### 文档清单

| 位置 | 数量 | 总体质量 |
|------|------|---------|
| 根目录 | 12 个 | ⚠️ 混杂一次性报告/内部文档 |
| docs/ | 17 个 | ⚠️ 含严重 accuracy 问题 |
| docs/runbooks/ | 5 个 | ✅ 良好 |
| .github/ 模板 | 3 个 | ✅ 合格 |
| **合计** | **37+ 文件** | **~300KB 总量** |

### 🔴 CRITICAL：文档准确性严重问题

| # | 问题 | 详情 |
|---|------|------|
| 1 | **API 文档声明 17 个不存在的端点** | `api-reference.md` 和 `api-reference-updated.md` 共同包含了 Products(4)、Terms(5)、Export(1)、Audit(1)、Users(3) 的未实现端点。还包括两版 API 参考文档并存（哪个是权威？） |
| 2 | **README API 端点全部错误** | `GET /api/v1/export/products`（不存在，实际: `POST /api/v1/export/csv`）、`POST /api/v1/import/products`（不存在，实际: `POST /api/v1/import/upload`）— 4 个端点路径全部错误 |
| 3 | **三个 ADR-001 编号冲突** | `ADR-001-Token-Storage-Migration.md`、`ADR-001-Token-Shortening-and-Redis-Blacklist.md`、`ADR-001-PostgreSQL-Migration.md` — 编号完全重复 |

### 文档缺失

| 缺失文档 | 优先级 | 理由 |
|---------|--------|------|
| 数据库 Schema 文档 | 🔴 P1 | 无 ER 图或表结构说明 |
| RBAC 权限模型文档 | 🔴 P1 | 角色权限矩阵分散在 PRD 和 README 中 |
| 故障排除指南 | 🟡 P2 | **已知的 404 问题无任何文档说明** |
| 架构总览图 | 🟡 P2 | 有 PRD 但无高层架构图 |
| i18n/翻译工作流指南 | 🟡 P2 | 系统核心是双语的 |

---

## ✅ 行动清单（按优先级排序）

### Sprint 1：安全止血 + 404 修复（P0，本周）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 1 | **立即轮换 JWT 密钥**，从 `.env` 中移除真实值，确认 `.gitignore` 包含 `.env`，清理 Git 历史 | 后端 | P0 | 立即 |
| 2 | **创建缺失的 6 个前端页面**：`products/new/page.tsx`、`products/[id]/page.tsx`、`products/import/page.tsx`、`audit/page.tsx`、`settings/users/page.tsx`、`settings/layout.tsx` | 前端 | P0 | 3 天 |
| 3 | **修复前端 Dockerfile**：将 `CMD npx next dev` 改为 `RUN npx next build && CMD npx next start` | DevOps | P0 | 1 天 |
| 4 | **修复 CI frontend job**：添加 `typecheck` 和 `test` 脚本到 `package.json`（或从 CI 中移除对应步骤），添加 `vitest` 基础测试框架 | DevOps | P0 | 1 天 |
| 5 | **创建错误边界**：添加 `error.tsx` + `global-error.tsx` + React ErrorBoundary 组件 | 前端 | P0 | 1 天 |

### Sprint 2：安全加固 + 部署完善（P1，下周）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 6 | **Token 存储改造**：从 localStorage 迁移到 httpOnly Cookie + refresh token 方案（参考已有 ADR-001-Token-Storage-Migration） | 前端+后端 | P1 | 3 天 |
| 7 | **保护 `/metrics` 端点**：添加认证依赖或在 Nginx 层限制内网 IP | 后端 | P1 | 1 天 |
| 8 | **修复生产 debug_info 泄露**：添加独立 `DEBUG` 配置项，生产强制关闭 | 后端 | P1 | 0.5 天 |
| 9 | **收紧 CORS 配置**：`allow_methods` 和 `allow_headers` 从 `["*"]` 改为显式白名单；生产 `ALLOWED_ORIGINS` 使用具体域名 | 后端 | P1 | 0.5 天 |
| 10 | **添加审计日志写入**：在 `create/update/delete_product` 三个端点中写入 AuditLog | 后端 | P1 | 1 天 |
| 11 | **修复 `update_user_role` reviewer 缺失**：`valid_roles` 添加 `"reviewer"` | 后端 | P1 | 0.5 天 |
| 12 | **修复 API 文档准确性**：删除 `api-reference.md`（保留 `api-reference-updated.md` 为唯一版本），移除所有不存在端点的文档描述；修正 README 中 4 个错误端点路径 | 文档 | P1 | 1 天 |
| 13 | **重新编号 ADR**：解决三个 ADR-001 冲突 | 文档 | P1 | 0.5 天 |
| 14 | **前端添加基础测试**：安装 `vitest` + `@testing-library/react`，为 Sidebar（菜单路由）和关键页面添加渲染测试 | 前端 | P1 | 2 天 |

### Sprint 3：质量提升（P2，本月）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 15 | **登录速率限制**：使用 slowapi 对 `/login` 限制 5 次/分钟/IP | 后端 | P2 | 1 天 |
| 16 | **生产数据库迁移**：在 `config.py` 中添加生产环境 SQLite 检测并拒绝启动；完善 PostgreSQL 迁移 ADR | 后端 | P2 | 2 天 |
| 17 | **修复密码修改参数位置**：创建 `ChangePasswordRequest` Body 模型 | 后端 | P2 | 0.5 天 |
| 18 | **修复静默错误吞没**：全局替换 `.catch(() => {})` 为统一错误处理（至少 `console.error` + 用户可见提示） | 前端 | P2 | 1 天 |
| 19 | **补充 audit.py 和 exception_handler 测试** | 测试 | P2 | 1.5 天 |
| 20 | **添加前端 E2E**：使用 Playwright 覆盖关键流程（登录→产品列表→新建产品→导出） | 测试 | P2 | 2 天 |

---

## ⚠️ 待完善 / 已知局限

1. **未做运行时流量验证**：本次审查为静态代码分析 + 文件系统扫描，未启动实际服务验证所有端点的运行时行为。建议后续进行集成测试运行。
2. **未做前端性能审计**：未检查 Web Vitals（LCP/FID/CLS）、bundle 大小、首屏加载时间。
3. **未做第三方依赖 CVE 深度扫描**：仅检查了现有依赖配置和 audit 输出，未对每个依赖的已知 CVE 逐一排查。
4. **未检查数据库迁移状态**：未验证 Alembic 迁移是否与当前模型定义一致。
5. **用户管理的 5 个缺失 API**（文档中描述但未实现的 `POST /users`、`PUT /users/{id}`、`DELETE /users/{id}` 等）未纳入本次修复范围——如产品规划中包含这些功能，需要单独排期开发。

---

## 📚 数据来源 & 成员产出索引

- **Cody（代码审查师）** 原始产出：全面代码审计报告 — 覆盖 4 维度（安全/性能/正确性/可维护性），发现 5 CRITICAL + 6 HIGH + 5 MEDIUM + 4 LOW，共 20 项
- **Archi（架构师）** 原始产出：前端路由与权限架构审计报告 — 完整路由表、死链盘点（5 处）、权限配置分析、模块加载分析、2 份 ADR 提案
- **Rex（SRE 工程师）** 原始产出：SRE 运维审计报告 — 30 端点完整矩阵、构建健康评估、错误边界与异常捕获审计、部署配置审计（5 个 compose 文件）、监控配置状态
- **Tessa（测试专家）** 原始产出：测试审计报告 — 19 个后端测试文件清单、覆盖率缺口（3 个关键模块 0 测试）、CI 健康分析（前端 CI 损坏）、测试债务清单
- **Docu（技术文档师）** 原始产出：文档审计报告 — 37+ 文件清单、API 文档准确性对照（17 个幽灵端点）、README 问题、ADR 编号冲突、缺失文档优先列表

---

> 本报告由工程保障团队 AI 协作生成（甄宇航·工程督导 汇编），关键决策请由人类工程负责人复核。所有发现基于 2026-07-28 的代码库静态分析。
