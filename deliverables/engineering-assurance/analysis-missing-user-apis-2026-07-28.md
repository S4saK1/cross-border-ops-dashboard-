
# 文档一：缺失用户管理 API 分析说明

**日期**：2026-07-28
**工作流**：综合工程审查（后续专项分析 · 文档一）
**参与成员**：Archi（系统架构师）
**关联审计**：comprehensive-audit-404-route-security-2026-07-28.md

---

## 📌 TL;DR（执行摘要）

- 后端 `backend/app/api/users.py` 当前仅实现 4 个端点；`docs/api-reference.md` 与 `docs/PRD.md` 共同要求 7 个，其中**文档化但代码缺失 3 个**，另有 **2 个由数据模型/设计隐含需要**的端点此前未被任何文档覆盖。
- 5 个缺失 API 合计开发量约 **14 人日**，建议独立排期（不并入当前 Sprint 1/2/3 的 404 修复 + 安全加固）。
- 关键发现：① `api-reference.md` 的"更新清单"虚假标注 PUT/DELETE 用户「已存在」；② 用户管理变更当前**完全不写审计日志**；③ 后端**无邮件/通知模块**；④ 前端 `/settings/users/page.tsx` 现已存在但是只读表格且字段错配（`u.name` vs `u.display_name`）。

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🟡 需独立排期（新功能，非缺陷修复） |
| 缺失 API 数量 | 5 个（3 文档化缺失 + 2 设计隐含） |
| 关键行动项 | 5 条（API 规格 + 审计 + 文档修订） |
| 建议下一步 | 先修订 api-reference.md 虚假标注 → M1 设计+Schema → M2 后端+测试 → M3 前端 E2E |

---

## 1. 调查方法与实测依据

读取的真实文件：
- `backend/app/api/users.py`：仅 4 端点 `GET ""` / `GET /me` / `GET /{id}` / `PUT /{id}/role`；无 create/update/delete/reset/bulk；role 端点仅 `logger.info` 不写审计。
- `backend/app/main.py:139`：`users.router` 挂载 `prefix="/api/v1/users"`。
- `backend/app/models/user.py`：`UserProfile` 含 `is_active`、`force_password_change`、`last_login_at`、`role`。
- `backend/app/schemas/auth.py`：仅 `UserCreate`、`UserOut`(id/email/display_name/role/is_active)、`ChangePasswordRequest`；无 `UserUpdate`。
- `backend/app/core/deps.py`：`require_admin=require_role("admin")` 等四档 RBAC。
- `backend/app/core/security.py`：`get_password_hash`、`verify_password`、`revoke_all_user_tokens(user_id, db)` 可用。
- `backend/app/api/audit.py`：仅 GET，无写入帮助函数，无审计中间件。
- `frontend/src/components/Sidebar.tsx:79`：菜单 `用户管理 → /settings/users`（admin 可见）。
- `frontend/src/app/settings/users/page.tsx`：页面已存在，只读，调 `GET /api/v1/users`，字段用 `u.name`（错配）。
- `docs/api-reference.md` §用户管理：文档化 GET/POST/GET{id}/PUT{id}/DELETE{id}/PUT{id}/role 共 6 端点。
- `docs/PRD.md` §4.7：用户管理列 4 端点；§3.5 枚举含 `user_create`/`user_update`/`user_delete`。

### 与前置审计的两处偏差（已修正）
- **偏差 A**：前置审计称 `settings/users/page.tsx` 不存在(404)。实测已存在，404 已自行修复；但为只读，依赖本组 5 API 才有写能力。
- **偏差 B**：前置审计引用的 `api-reference-updated.md` 在本仓库**不存在**；`api-reference.md` 的更新清单错误标注 PUT/DELETE 已存在。

---

## 2. 现有用户 API 实测盘点

| 端点 | 状态 | 说明 |
|------|------|------|
| `GET /api/v1/users` | ✅ 存在 | admin |
| `GET /api/v1/users/me` | ✅ 存在 | 已认证 |
| `GET /api/v1/users/{id}` | ✅ 存在 | viewer+ |
| `PUT /api/v1/users/{id}/role` | ✅ 存在 | admin，但仅 logger.info，**无审计写入** |
| `POST /api/v1/users` | ❌ 缺失 | 文档要求 |
| `PUT /api/v1/users/{id}` | ❌ 缺失 | 文档要求 |
| `DELETE /api/v1/users/{id}` | ❌ 缺失 | 文档要求 |
| `POST /api/v1/users/{id}/reset-password` | ❌ 缺失 | 设计隐含（force_password_change 孤儿字段） |
| `POST /api/v1/users/bulk` | ❌ 缺失 | 设计隐含（仿 products/batch-delete） |

注：公开 `POST /auth/register` 强制 `role=viewer`，故管理员无法在后台直接创建带指定角色账号。

---

## 3. 五个缺失 API 的识别逻辑

- **文档化但缺失(3)**：`POST` / `PUT{id}` / `DELETE{id}`，来自 `api-reference.md` 与 `PRD §4.7`，声明"仅管理员"，但 `users.py` 无路由。
- **设计隐含(2)**：
  - **API-4 管理员重置他人密码**：依据 `force_password_change` 字段存在却无任何管理员触发路径（孤儿字段）+ `revoke_all_user_tokens` 已具备 + PRD 安全要求账号恢复能力。
  - **API-5 批量操作**：依据 `POST /products/batch-delete` 既有范式 + PRD「批量操作」核心价值 + 团队管理效率。

---

## 4. 缺失 API 详细规格

> 通用约束：基址 `/api/v1/users`；JWT Bearer；错误码 400/401/403/404/409；写操作须写 `AuditLog`（`action ∈ {user_create,user_update,user_delete,user_password_reset,user_bulk}`，`resource_type="user"`）；建议新建 `write_audit_log` 帮助函数。

### API-1 `POST /api/v1/users`（创建用户）— P0 · 2.0 人日
- **功能**：管理员后台创建成员并指定角色，复用密码强度校验。
- **请求**：`require_admin`；Body 复用 `UserCreate{email(EmailStr,唯一), password(过强度校验), display_name, role(默认viewer)}`。
- **响应**：`201`→`UserOut`；`400` 邮箱已注册/密码弱；`401`；`403` 非admin；建议 `409` 邮箱冲突。
- **依赖**：`require_admin`、`get_password_hash`、`validate_password_strength`、复用 `UserCreate`、审计 `user_create`(须新建写入)、可选欢迎邮件(无模块→v1 不阻塞)。
- **业务影响**：管理员无法一键开通带角色账号；workaround 是自助 register(viewer)后提权，流程割裂且无审计；团队扩容受阻。

### API-2 `PUT /api/v1/users/{user_id}`（更新用户）— P0 · 2.5 人日
- **功能**：更新 `display_name`/`role`/`is_active`（含重新启用）。
- **请求**：`require_admin`；需新建 `UserUpdate{display_name?, role?, is_active?}`。
- **响应**：`200`→`UserOut`；`400` 角色非法/禁止自降级停用；`401`；`403`；`404`。
- **依赖**：`require_admin`；复用 `update_user_role` 的合法角色表与"禁止自己降级"守卫(`users.py:118-124`)；新建 `UserUpdate`；审计 `user_update`(写差异)；`is_active false→true` 即重新启用。
- **业务影响**：无法修正姓名/调角色/重新启用被禁账号（唯一"启用"路径被堵）。建议本端点吸收角色变更，减少与现有 role 端点冗余。

### API-3 `DELETE /api/v1/users/{user_id}`（禁用/软删除）— P1 · 1.5 人日
- **功能**：置 `is_active=False`，非物理删除（PRD §4.7）。
- **请求**：`require_admin`；path `user_id`。
- **响应**：`200 {message}`；`400` 禁止禁用自己；`401`；`403`；`404`。
- **依赖**：`UserProfile.is_active`；建议禁用后 `revoke_all_user_tokens` 即时登出；审计 `user_delete`；关联产品/术语保留(created_by 不级联删，保审计追溯)。
- **业务影响（安全缺口）**：当前无任何路径禁用账号，`is_active` 恒 true；离职/被盗/可疑账号无法锁停，违反 PRD §8。

### API-4 `POST /api/v1/users/{user_id}/reset-password`（管理员重置他人密码）— P1 · 3.0 人日
- **功能**：生成强随机临时密码或重置令牌，置 `force_password_change=True`，强制下次改密；可选通知。
- **请求**：`require_admin`；新建 `AdminResetPasswordRequest{new_password?(可选,不传则后端生成), notify?(默认true)}`。
- **响应**：`200 {message, temp_password?(仅后端生成时), force_change_required:true}`；`400` 重置自己/密码弱；`401`；`403` 非admin(建议禁重置其他admin)；`404`。
- **依赖**：`get_password_hash`；`UserProfile.force_password_change=True`；`revoke_all_user_tokens` 强制重登；审计 `user_password_reset`(需向 PRD §3.5 枚举新增该常量)；通知——后端无邮件模块，v1 返回临时密码由前端交付，邮件后置。
- **业务影响**：忘密/可疑账号无恢复手段；消除 `force_password_change` 孤儿字段语义空洞。

### API-5 `POST /api/v1/users/bulk`（批量操作）— P2 · 3.5 人日
- **功能**：批量 `change_role`/`activate`/`deactivate`/`delete`，仿 `products/batch-delete`。
- **请求**：`require_admin`；新建 `BulkUserActionRequest{user_ids:[uuid], action:enum, role?(change_role必填)}`。
- **响应**：`200 {message, succeeded, failed, errors:[{user_id,reason}]}`；`400` 空列表/非法action/缺role；`401`；`403`；部分 404 计入 failed 不整体失败。
- **依赖**：复用 API-2/3 内部逻辑(建议抽 `_apply_user_action` 公共函数)；单事务逐条、失败回滚该条；审计每条独立写；`revoke_all_user_tokens` 用于 deactivate/delete。
- **业务影响**：团队重组/批量离职权/批量调角色无法高效完成，规模化运营不可行。

---

## 5. 为何独立排期（不并入 Sprint 1/2/3）

1. **范围**：新功能 ≠ Bug 修复，走特性开发流程而非 hotfix。
2. **风险**：新增攻击面需独立威胁建模——`POST/users` 权限提升、`DELETE/bulk` 批量锁号 DoS、`reset-password` 账号接管、用户枚举(须 403 不泄露资源)。属"扩展安全面"非"加固既有面"。
3. **前端依赖**：`page.tsx` 虽存在但只读且字段错配，5 个后端 API 须与前端增/改/禁/重置/批量 UI 同期交付才能 E2E 验收。
4. **测试**：需净新建单测+集成+Playwright E2E+RBAC 矩阵+审计断言。
5. **先还文档债**：`api-reference.md` 虚假标注须先更正再开工。

---

## 6. 工作量与优先级

| # | API | 优先级 | 工作量(人日) |
|---|-----|--------|------------|
| 1 | POST /users | P0 | 2.0 |
| 2 | PUT /users/{id} | P0 | 2.5 |
| 3 | DELETE /users/{id} | P1 | 1.5 |
| 4 | reset-password | P1 | 3.0 |
| 5 | bulk | P2 | 3.5 |
| — | 公共审计帮助函数 + 回填 role-change + 文档修订 | — | 1.5 |
| **合计** | | | **≈14 人日** |

---

## 7. 排期与里程碑

- **M1 设计+Schema(≈2d)**：ADR、OpenAPI、错误码契约、新建 3 个 Schema 的 PR、威胁模型 v0、修订 `api-reference.md`。退出：Schema 合并、契约一致、安全签核。
- **M2 后端+测试(≈8d)**：5 端点 + `write_audit_log` + RBAC 守卫 + pytest(≥85%) + 审计断言 + 回填 role-change。退出：单测/集成通过、RBAC 矩阵通过。
- **M3 前端+E2E(≈4.5d)**：`/settings/users` 写能力 + 修复 `u.name`→`display_name` + Playwright E2E。退出：E2E 通过、只读→读写验收。
- **合并前门禁**：威胁建模终稿 + 新端点渗透/越权测试 + 审计完整性复核。
- **周线**：W1 M1；W2 M2(API1/2/3)；W3 M2(API4/5+公共+集成)→门禁；W4 M3→发布。

---

## 8. 风险与建议

1. 立即修订 `api-reference.md` 虚假"已存在"标注。
2. 新建 `write_audit_log`；新端点全写；回填现有 `PUT /{id}/role`（违反 PRD §2.7）。
3. `reset-password` v1 返回临时密码由前端交付，邮件通知后置。
4. 修 `page.tsx` `u.name`→`u.display_name`；统一 `UserOut` 与文档对 `last_login_at`/`created_at`/`updated_at` 的描述。
5. M1 明确权限边界：是否允许 admin 重置其他 admin、bulk 是否可批量删 admin（写入 ADR）。
6. 软删除一致性：禁用后 `created_by` 关联保留，硬删除另立 ADR。

---

## ✅ 行动清单（按优先级排序）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 1 | 修订 `api-reference.md` 虚假"PUT/DELETE 用户已存在"标注 | 文档 | P0 | 0.5d |
| 2 | 新建 `UserUpdate`/`AdminResetPasswordRequest`/`BulkUserActionRequest` 三个 Schema + ADR | 架构 | P0 | 2d(M1) |
| 3 | 实现 POST/PUT 用户端点 + `write_audit_log` 帮助函数 | 后端 | P0 | 4.5d(M2) |
| 4 | 实现 DELETE/reset-password/bulk + RBAC 守卫 + pytest≥85% | 后端 | P1 | 8d(M2) |
| 5 | `/settings/users` 写能力 + 字段错配修复 + Playwright E2E | 前端 | P1 | 4.5d(M3) |

---

## ⚠️ 待完善 / 已知局限

- 本分析基于静态代码核查，未实际启动服务验证端点行为。
- `reset-password` 的邮件通知依赖尚未存在的邮件模块，v1 暂以"前端交付临时密码"替代。
- 批量删除 admin 的权限边界需在 M1 ADR 中明确。

---

## 📚 数据来源 & 成员产出索引

- Archi（系统架构师）原始产出：缺失用户管理 API 完整分析（5 API 规格、依赖矩阵、错误码、排期里程碑），基于对 `backend/app/api/users.py`、`models/user.py`、`schemas/auth.py`、`docs/PRD.md`、`docs/api-reference.md`、`frontend/src/app/settings/users/page.tsx` 的逐文件核查。

---

> 本文档由工程保障团队 AI 协作生成（甄宇航·工程督导 汇编），关键决策请由人类工程负责人复核。
