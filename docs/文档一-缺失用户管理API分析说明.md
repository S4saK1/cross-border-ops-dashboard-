# 文档一：缺失用户管理 API 分析说明

**文档类型**：工程审计后续 — 系统架构分析
**负责人**：Archi（系统架构师 / architect）
**日期**：2025-07-28
**关联系统**：跨境产品资料中英对照系统（bilingual-product-cms）
**前置依据**：综合审计报告（404 修复 + 安全加固 Sprint 1/2/3）

---


> # ⚠️ 重要勘误（2026-07-29 工程审查复核）
> 
> 本文档于 2025-07-28 由架构师 Archi 撰写，经 2026-07-29 工程保障团队（Cody/Archi/Tessa/Docu）专项代码审查 + 主理人逐文件直读源码复核，发现以下 **3 处误判 + 1 处误报**。阅读本文档时请以本勘误为准，原始分析中有误的部分已用 ~~删除线~~ 标记。
> 
> | 编号 | 误判位置 | 原始声称 | 复核事实 | 证据 |
> |------|---------|---------|---------|------|
> | **E1** | §8 第7条"令牌撤销表为运行期硬依赖"(L355) | `init_db.py` 的 `create_all` 不会加载 `RefreshTokenBlacklist`，新建库将缺表 | ❌ **错误**。`models/__init__.py:5` 已导入该模型；`main.py:6,24` 启动时执行 `Base.metadata.create_all`；`init_db.py:9,32` 同样导入并建表。**走正常启动/init_db 流程，表一定会被建出。** | Cody 实证 + 主理人直读 `models/__init__.py`、`main.py`、`init_db.py` |
> | **E2** | 关键发现 #2 (L27)、调查表 (L40)、端点盘点 (L68)、§6 估时 (L310) | `PUT /{id}/role` "仅 `logger.info`，不写审计" | ❌ **错误**。`users.py:131-139` 已通过 `write_audit_log(...)` 写入 `AuditLog`，参数含 actor_id、action="user_role_change"、subject_type、subject_id、before/after、ip_address。 | 主理人直读 `backend/app/api/users.py:131-139` |
> | **E3** | 关键发现 #1 (L26) | `api-reference.md` "文档更新清单"错误标注 `PUT /users/{id}` 与 `DELETE /users/{id}`「已存在」 | ❌ **错误**。实际 `api-reference.md` 更新清单第 7-8 条标注为 **"规划中"**，并非「已存在」。这是对源文档的误读。 | 主理人直读 `docs/api-reference.md` 文档更新清单 |
> | **E4** | 测试专家 Tessa 原始产出 | `config.py` 存在缩进错误 | ❌ **误报**。经主理人直读源码核实，`config.py` 无缩进错误。 | 主理人直读 `backend/app/config.py` |
> 
> **注意**：尽管存在以上误判，本文档的核心结论——**5 个 API 确属缺失、优先级 P0×2/P1×2/P2×1、约 14 人日工作量**——仍然成立。误判仅涉及对既有代码行为的错误描述，不影响缺失 API 的分析主体。
> 
> **P0 代码修复已交付（2026-07-29）**：
> - API-1 `POST /api/v1/users` — `backend/app/api/users.py` ✅
> - API-2 `PUT /api/v1/users/{user_id}` — `backend/app/api/users.py` ✅
> - 配套 Schema `AdminUserCreate` / `UserUpdate` — `backend/app/schemas/auth.py` ✅

---

## TL;DR

经对真实代码库的逐文件核查，确认**后端 `backend/app/api/users.py` 当前仅实现 4 个用户端点**，而 `docs/api-reference.md` 与 `docs/PRD.md` 共同要求 7 个端点（含 `GET /users/me` 与 `PUT /users/{id}/role`）。其中**文档化但代码缺失的有 3 个**，另有 **2 个由系统设计与数据模型隐含需要的端点**此前未被任何文档覆盖。

**5 个缺失 API 一览表**

| # | 方法 & 路径 | 预期功能 | 优先级 | 工作量(人日) | 里程碑 |
|---|------------|---------|--------|-------------|--------|
| 1 | `POST /api/v1/users` | 管理员创建团队成员账号（指定角色） | **P0** | 2.0 | M2 |
| 2 | `PUT /api/v1/users/{user_id}` | 管理员更新用户资料/角色/激活态 | **P0** | 2.5 | M2 |
| 3 | `DELETE /api/v1/users/{user_id}` | 管理员禁用（软删除）用户 | **P1** | 1.5 | M2 |
| 4 | `POST /api/v1/users/{user_id}/reset-password` | 管理员重置他人密码（强制改密） | **P1** | 3.0 | M2 |
| 5 | `POST /api/v1/users/bulk` | 批量用户操作（角色/启用停用/删除） | **P2** | 3.5 | M2 |

**关键发现（影响排期决策）**
1. **`docs/api-reference.md` 的"文档更新清单"错误地标注 `PUT /users/{id}` 与 `DELETE /users/{id}`「已存在」** —— 这正是审计阶段漏判该缺口的根因，必须先修文档。
2. **用户管理变更当前完全没有写入审计日志**：~~~~现有 `PUT /users/{id}/role` 仅做 `logger.info(...)`，全仓只有 `products.py` 手动写 `AuditLog`，**不存在审计中间件**。新端点必须自带审计写入（并建议回填现有 role-change）。~~ ⚠️ **已勘误（E2）**：users.py:131-139 已通过 write_audit_log(...) 写入 AuditLog，审计功能已存在。新端点仅需复用同一帮助函数。~~ ⚠️ **已勘误（E2）**：`users.py:131-139` 已通过 `write_audit_log(...)` 写入 `AuditLog`，审计功能已存在。新端点仅需复用同一帮助函数。
3. **后端无邮件/通知模块**：`reset-password` 的"通知用户"能力需新建或后置，v1 可先返回临时密码 + 前端提示。
4. **无 `UserUpdate` / 批量请求 Schema**：需新建（类比已有的 `ProductUpdate`）。
5. **前端 `/settings/users/page.tsx` 现已存在且不再 404**，但为只读表格，且字段错配（`u.name` 应为 `u.display_name`，`UserOut` 无 `name` 字段）。

---

## 1. 调查方法与实测依据

所有结论均来自对以下真实文件的读取（非推测）：

| 文件 | 关键事实 |
|------|---------|
| `backend/app/api/users.py` | 仅 4 个端点：`GET ""`、`GET /me`、`GET /{user_id}`、`PUT /{user_id}/role`；**无 create/update/delete/reset/bulk**；`update_user_role` ~~仅 `logger.info`，不写审计~~ ⚠️ 已勘误（E2）：实测已写 AuditLog |
| `backend/app/main.py` (L139) | `users.router` 挂载于 `prefix="/api/v1/users"` → 完整基址 `/api/v1/users` |
| `backend/app/models/user.py` | `UserProfile` 字段含 `is_active`、`force_password_change`、`last_login_at`、`role`、`email`、`display_name` |
| `backend/app/models/audit.py` | `AuditLog(action, resource_type, resource_id, details, ...)`；PRD §3.5 枚举含 `user_create/user_update/user_delete` |
| `backend/app/schemas/auth.py` | 仅有 `UserCreate`、`UserOut`(id/email/display_name/role/is_active)、`ChangePasswordRequest`；**无 `UserUpdate`** |
| `backend/app/core/deps.py` | `require_admin=require_role("admin")` 等四档 RBAC 依赖 |
| `backend/app/core/security.py` | `get_password_hash`、`verify_password`、`revoke_all_user_tokens(user_id, db)` 可用 |
| `backend/app/api/audit.py` | **仅 GET**，无写入帮助函数；无审计中间件 |
| `frontend/src/components/Sidebar.tsx` (L79) | 菜单项 `用户管理 → /settings/users`（admin 可见） |
| `frontend/src/app/settings/users/page.tsx` | **页面已存在**，只读表格，调 `GET /api/v1/users`，字段用 `u.name`（错配） |
| `docs/api-reference.md` §用户管理 | 文档化 `GET/POST/GET{id}/PUT{id}/DELETE{id}/PUT{id}/role` 6 个端点 |
| `docs/PRD.md` §4.7 | 用户管理仅列 4 个端点（GET/POST/PUT/DELETE）；同文件 §3.5 定义 `user_*` 审计动作 |
| `docs/api-reference-updated.md` | **不存在**（任务引用的该文件缺失，以 `api-reference.md` 为准） |

### 与前置审计的两处偏差（已修正）

- **偏差 A**：前置审计称"`src/app/settings/users/page.tsx` 不存在（导致 404）"。实测该文件已存在（2933 字节），404 问题已自行修复；但页面为只读，依赖本文件列出的 5 个缺失 API 才能具备写能力。
- **偏差 B**：前置审计引用 `docs/api-reference-updated.md`，该文件在当前仓库不存在；正确权威文档为 `docs/api-reference.md`，且其"文档更新清单"第 5、6、7 条**虚假标注** `PUT /users/{id}`、`DELETE /users/{id}` 已存在——这是缺口被掩盖的直接原因。

---

## 2. 现有用户管理 API 实测盘点

| 方法 | 路径 | 鉴权依赖 | 状态 |
|------|------|---------|------|
| `GET` | `/api/v1/users` | `require_admin` | ✅ 存在（列表） |
| `GET` | `/api/v1/users/me` | `get_current_user` | ✅ 存在（当前用户） |
| `GET` | `/api/v1/users/{user_id}` | `require_viewer`（非 admin 仅看自己） | ✅ 存在（详情） |
| `PUT` | `/api/v1/users/{user_id}/role` | `require_admin` | ✅ 存在（改角色，~~但无审计写入~~ ⚠️ 已勘误（E2）：审计已实现） |
| `POST` | `/api/v1/users` | `require_admin` | ❌ **缺失** |
| `PUT` | `/api/v1/users/{user_id}` | `require_admin` | ❌ **缺失** |
| `DELETE` | `/api/v1/users/{user_id}` | `require_admin` | ❌ **缺失** |
| `POST` | `/api/v1/users/{user_id}/reset-password` | `require_admin` | ❌ **缺失（设计隐含）** |
| `POST` | `/api/v1/users/bulk` | `require_admin` | ❌ **缺失（设计隐含）** |

> 注：公开端点 `POST /api/v1/auth/register` 强制 `role="viewer"`（防越权），故普通用户只能自助注册为 viewer；管理员无法在后台直接创建带指定角色（editor/reviewer/admin）的账号。

---

## 3. 五个缺失 API 的识别逻辑

### 3.1 文档化但缺失（3 个）
来自 `docs/api-reference.md` §用户管理（L1162 `POST`、L1230 `PUT`、L1270 `DELETE`）与 `docs/PRD.md` §4.7，三者均被文档声明为"仅管理员"，但 `users.py` 中无对应路由。

### 3.2 设计隐含需要（2 个）

**API-4 管理员重置他人密码** —— 依据：
- `UserProfile.force_password_change` 字段已存在于模型（L16），且 `auth.py` 的 `change_password` 仅用于**本人**改密并清零该标志；**没有任何管理员路径能触发"强制他人改密"**，该字段成为孤儿字段。
- `security.py` 已提供 `revoke_all_user_tokens(user_id, db)`（L98），可直接用于重置后强制重登。
- PRD §8 安全模型将"密码哈希"列为 Restricted，要求管理员具备账号恢复能力。

**API-5 批量用户操作** —— 依据：
- 既有范式：`POST /api/v1/products/batch-delete`（`products.py`）已确立"批量动作"端点模式；PRD §1.3 将"批量操作"列为核心价值。
- 团队管理效率：管理员对多成员批量改角色/启用停用/离职权，逐条调用缺失的 PUT/DELETE 不可行。

---

## 4. 缺失 API 详细规格

> 通用约定：
> - **基址**：`/api/v1/users`
> - **认证**：JWT Bearer（`Authorization: Bearer <access_token>`）
> - **错误码**：`400` 参数/校验失败；`401` 未认证；`403` 权限不足（非 admin）；`404` 用户不存在；`409` 资源冲突（邮箱已存在）
> - **审计**：每个写操作须向 `AuditLog` 写入 `action∈{user_create,user_update,user_delete,user_password_reset,user_bulk}`，`resource_type="user"`；建议新建 `app/core/audit.py::write_audit_log(...)` 帮助函数（参照 `products.py:L32` 写法）。
> - **响应包格式**：错误统一 `{"detail": "..."}`（与 `api-reference.md` §错误处理一致）。

---

### API-1：`POST /api/v1/users` — 创建用户

**预期功能**：管理员在后台创建团队成员账号并指定角色（editor/reviewer/viewer/admin），复用密码强度校验。

**请求结构**
- Method / Path：`POST /api/v1/users`
- Auth：`require_admin`
- Body（复用现有 `UserCreate`，`backend/app/schemas/auth.py:6`）：
  ```json
  {
    "email": "string (EmailStr, 唯一)",
    "password": "string (须通过 validate_password_strength)",
    "display_name": "string",
    "role": "string (默认 viewer；建议仅允许 admin/editor/reviewer，禁止自创 admin 除非调用者为 admin)"
  }
  ```

**响应结构**
- 成功 `201`：`UserOut`（`{id, email, display_name, role, is_active:true}`）
- `400`：邮箱已注册 / 密码强度不足（返回 `{"message","errors","requirements"}`）
- `401`：未认证
- `403`：非 admin
- `409`：邮箱已存在（建议与 400 合并为 409 以契合 REST 语义）

**依赖关系**
- Auth：`get_current_user` + `require_admin`（`deps.py`）
- 密码：`get_password_hash`（`security.py`）
- 校验：复用 `validate_password_strength`（`utils/password_validator.py`）
- Schema：复用 `UserCreate`（无需新建）
- 审计：`user_create`（**须新建写入**，当前无）
- 通知：可选——创建后发欢迎邮件（**当前无邮件模块 → v1 不阻塞**）

**业务流程影响**
管理员无法在后台一键开通带指定角色的团队成员账号。现状 workaround：用户自助 `POST /auth/register`（强制 viewer）后，再由 admin 经 `PUT /{id}/role` 提权——流程割裂、**该创建动作无审计记录**。团队扩容/外包协作开通受阻。

---

### API-2：`PUT /api/v1/users/{user_id}` — 更新用户

**预期功能**：管理员更新 `display_name`、`role`、`is_active` 等字段（合并原文档中"更新用户"与部分"更新角色"语义）。

**请求结构**
- Method / Path：`PUT /api/v1/users/{user_id}`
- Auth：`require_admin`
- Path：`user_id: string (UUID)`
- Body（**需新建 `UserUpdate` Schema**，类比 `ProductUpdate`）：
  ```json
  {
    "display_name": "string (可选)",
    "role": "string (可选；admin/editor/reviewer/viewer)",
    "is_active": "boolean (可选；用于重新启用被禁用账号)"
  }
  ```

**响应结构**
- 成功 `200`：`UserOut`
- `400`：角色非法（不在四档）或**管理员试图降级/停用自己**
- `401`：未认证
- `403`：非 admin
- `404`：用户不存在

**依赖关系**
- RBAC：`require_admin`；复用 `update_user_role` 中的合法角色表 `["admin","editor","reviewer","viewer"]` 与"禁止自己降级"守卫逻辑（`users.py:118-124`）
- Schema：**新建 `UserUpdate`**（`schemas/auth.py`，可选字段）
- 审计：`user_update`（写入变更前后差异 `details={"fields_changed":[...]}`）
- 软删除回转：当 `is_active` 由 false→true 时，等价于"重新启用"，应与 API-3 / API-5 共用逻辑

**业务流程影响**
管理员无法修正成员姓名、调整角色、或重新启用曾被禁用的账号（因 PUT 缺失，唯一的"启用"路径被堵死）。与现有 `PUT /{id}/role` 功能重叠，建议本端点吸收角色变更以减少冗余路由。

---

### API-3：`DELETE /api/v1/users/{user_id}` — 禁用（软删除）用户

**预期功能**：管理员禁用账号（置 `is_active=False`，**非物理删除**），符合 PRD §4.7"禁用用户（软删除）"。

**请求结构**
- Method / Path：`DELETE /api/v1/users/{user_id}`
- Auth：`require_admin`
- Path：`user_id: string`

**响应结构**
- 成功 `200`：`{"message": "User disabled successfully"}`
- `400`：**禁止禁用自己**
- `401`：未认证
- `403`：非 admin
- `404`：用户不存在

**依赖关系**
- 模型：`UserProfile.is_active`（软删除标记）
- 安全（建议）：禁用后调用 `revoke_all_user_tokens(user_id, db)` 使该用户即时登出
- 审计：`user_delete`（PRD §3.5 枚举已预留）
- 关联：禁用账号后其创建的产品/术语**保留**（`created_by` 外键不应级联删，符合审计可追溯）

**业务流程影响**
**安全缺口**：当前无任何路径可禁用账号，`is_active` 恒为 true。离职员工、被盗用账号、可疑登录均无法被管理员锁停，违反 PRD §8 数据安全要求，是 5 个缺失点中安全优先级最高者之一。

---

### API-4：`POST /api/v1/users/{user_id}/reset-password` — 管理员重置他人密码

**预期功能**：管理员为指定用户重置密码，生成强随机临时密码（或重置令牌），置 `force_password_change=True`，强制其下次登录改密；可选通过邮件/站内信通知。

**请求结构**
- Method / Path：`POST /api/v1/users/{user_id}/reset-password`
- Auth：`require_admin`
- Path：`user_id: string`
- Body（**新建 `AdminResetPasswordRequest`**）：
  ```json
  {
    "new_password": "string (可选；不传则由后端生成强随机临时密码)",
    "notify": "boolean (默认 true；是否通知用户)"
  }
  ```

**响应结构**
- 成功 `200`：`{"message":"Password reset successfully","temp_password":"<仅当后端生成时返回>","force_change_required":true}`
- `400`：试图重置自己 / 密码强度不足（若自带）
- `401`：未认证
- `403`：非 admin（**且应禁止 admin 重置其他 admin**，或仅限超级管理员——需产品确认）
- `404`：用户不存在

**依赖关系**
- 密码：`get_password_hash`（`security.py`）
- 模型：`UserProfile.force_password_change=True`；`last_login_at` 不变
- 会话：`revoke_all_user_tokens(user_id, db)` 强制重登
- 审计：`user_password_reset`（**需向 PRD §3.5 枚举新增该 action 常量**）
- 通知：**当前后端无邮件/SMTP/通知模块**（全仓 grep 无 `send_email`/`smtp`）。v1 方案：返回临时密码由前端当面/安全渠道交付；邮件通知列为后续迭代，或接入现有告警通道

**业务流程影响**
帮助台/锁户场景被堵：用户忘密或账号可疑时，管理员除"知道其明文密码"外无任何恢复手段。同时消除 `force_password_change` 孤儿字段的语义空洞。

---

### API-5：`POST /api/v1/users/bulk` — 批量用户操作

**预期功能**：管理员对一批用户执行同一动作：批量改角色、批量启用/停用、批量禁用。仿 `POST /products/batch-delete` 的批量范式。

**请求结构**
- Method / Path：`POST /api/v1/users/bulk`
- Auth：`require_admin`
- Body（**新建 `BulkUserActionRequest`**）：
  ```json
  {
    "user_ids": ["uuid", "..."],
    "action": "string (enum: change_role | activate | deactivate | delete)",
    "role": "string (仅当 action=change_role 时必填)"
  }
  ```

**响应结构**
- 成功 `200`：`{"message":"Bulk action completed","succeeded":N,"failed":M,"errors":[{"user_id":..,"reason":..}]}`
- `400`：空列表 / 非法 action / change_role 缺 role
- `401`：未认证
- `403`：非 admin
- `404`：部分 user_id 不存在（计入 failed，不整体失败）

**依赖关系**
- 复用：API-2（角色/启用）、API-3（停用/删除）的内部逻辑；建议抽公共 `_apply_user_action(db, admin, user, action, role)` 以避免三处重复
- 事务：批量操作为**单事务**，任一失败回滚该条、记录错误，整体不中断
- 审计：对每条成功操作写一条 `user_bulk` / 对应 `user_update`/`user_delete`（建议每条独立审计行，满足 PRD §2.7 追溯）
- 安全：`revoke_all_user_tokens` 用于 deactivate/delete

**业务流程影响**
团队重组、批量离职权、按项目批量调整角色等场景无法高效完成；当前只能逐条调用缺失的单点端点，规模化运营不可行。

---

## 5. 为何需要独立排期（不并入 Sprint 1/2/3：404 修复 + 安全加固）

当前 Sprint 1/2/3 的实质是**缺陷修复与安全加固**（`P1_P2_Issue_Report.md` 显示重点为 refresh-token 黑名单、越权测试、路径遍历等；PRD §Phase1 W11 为"安全加固"）。将本组 5 个 API 并入的理由不成立，原因如下：

1. **范围属性不同（新功能 ≠ Bug 修复）**
   404 与加固是对**已有**代码修洞；本组是**新增可写资源端点**，属特性交付，应走特性开发流程（设计→实现→E2E→发布），而非 hotfix 通道。

2. **风险：新增攻击面需独立威胁建模**
   - `POST /users`：角色参数若未强制校验，存在**权限提升**风险（类比 `auth/register` 已踩过的坑）。
   - `DELETE /users` 与 `bulk(delete)`：可被滥用为**批量锁号/DoS**。
   - `reset-password`：若允许重置其他 admin 或自己，构成**账号接管**后门。
   - 用户枚举：列表/详情错误响应须严格遵循 PRD §8.2"403 不泄露资源信息"。
   上述需在合并前完成威胁建模 + 权限矩阵渗透测试，属于"扩展安全面"而非"加固既有面"。

3. **强依赖缺失的前端写能力**
   前端 `/settings/users/page.tsx` 虽已存在但**只读**，且字段错配（`u.name`→`u.display_name`）。5 个后端 API 必须与前端增/改/禁/重置/批量 UI **同期交付**才能做 E2E 验证；纯后端修复无法独立验收。

4. **测试覆盖需净新建**
   现有测试基线覆盖已存在的端点；本组需新建单元测试 + 集成测试（pytest/httpx）+ Playwright E2E + RBAC 矩阵测试 + 审计写入断言，工作量与缺陷修复不在一个量级。

5. **须先偿还文档债务**
   `api-reference.md` 虚假标注 PUT/DELETE 已存在，会在排期前误导评估；必须先发更正（ADR + 文档修订）再开工。

---

## 6. 工作量估算与优先级

| # | API | 优先级 | 工作量(人日) | 主要工作拆解 |
|---|-----|--------|-------------|-------------|
| 1 | `POST /users` | P0 | 2.0 | 路由+RBAC+复用 UserCreate/密码校验+邮箱唯一性+审计写入 |
| 2 | `PUT /users/{id}` | P0 | 2.5 | **新建 UserUpdate Schema**+角色/启用逻辑+自降级守卫+审计差异 |
| 3 | `DELETE /users/{id}` | P1 | 1.5 | 软删除+自禁用守卫+`revoke_all_user_tokens`+审计 |
| 4 | `reset-password` | P1 | 3.0 | **新建请求 Schema**+临时密码生成+`force_password_change`+令牌撤销+审计（通知后置） |
| 5 | `bulk` | P2 | 3.5 | **新建 BulkRequest Schema**+事务+复用单点逻辑+逐条审计+错误聚合 |
| — | 公共 | — | ~1.5 | ~~新建 `write_audit_log` 帮助函数 + 回填现有 `PUT /{id}/role` 审计~~ + 文档修订 ⚠️ 已勘误（E2）：write_audit_log 已存在，role-change 审计已实现 |
| **合计** | | | **≈14.0** | |

> 估算基于小团队（1 后端 + 0.5 前端协作 + 架构评审），含联调与单测，不含 Playwright E2E（计入 M3）。

---

## 7. 排期计划与里程碑

### 里程碑节点

- **M1 — API 设计 + Schema（≈2 人日）**
  - 产出：ADR（记录本 5 端点决策与权衡）、OpenAPI 规格、错误码契约（400/401/403/404/409）、`UserUpdate`/`AdminResetPasswordRequest`/`BulkUserActionRequest` Schema PR、威胁建模 v0、修订 `api-reference.md`（纠正虚假"已存在"标注）。
  - 退出标准：Schema 合并、文档与代码契约一致、安全团队签核威胁模型。

- **M2 — 后端实现 + 单元/集成测试（≈8 人日，含公共 1.5）**
  - 产出：5 端点实现、`write_audit_log` 帮助函数、RBAC 守卫、pytest 覆盖（目标 ≥85%）、审计写入断言、回填现有 role-change 审计。
  - 退出标准：所有新端点单测/集成测试通过；权限矩阵测试（admin 可、非 admin 403）通过。

- **M3 — 前端页面 + E2E（≈4.5 人日）**
  - 产出：`/settings/users` 写能力（创建弹窗、行内编辑、禁用/重置按钮、批量勾选）、**修复 `u.name`→`u.display_name` 字段错配**、Playwright E2E 覆盖 RBAC 与关键流程。
  - 退出标准：E2E 通过；只读→可读写验收；字段正确渲染。

- **合并前加固门禁（Gating）**
  - 威胁建模终稿 + 新端点渗透/越权测试（提权、批量锁号、枚举、重置滥用）+ 审计完整性复核。

### 周时间线（建议）

```
第 1 周:  [M1 设计+Schema+文档修订+威胁模型 v0]
第 2 周:  [M2 后端 API-1/2/3 实现+测试]
第 3 周:  [M2 后端 API-4/5 + 公共审计帮助函数 + 集成测试]   → 门禁：威胁建模终稿
第 4 周:  [M3 前端写能力 + 字段修复 + Playwright E2E]       → 发布
```

---

## 8. 风险与建议

1. **立即修订文档**：将 `api-reference.md` §用户管理"文档更新清单"中 PUT/DELETE「已存在」改为「缺失/待实现」，避免再次误判。
2. ~~**审计日志补齐**：新建 `write_audit_log` 帮助函数；新端点全部写入；**回填**现有 `PUT /{id}/role`（当前仅 `logger.info`，违反 PRD §2.7）。~~ ⚠️ 已勘误（E2）：write_audit_log 帮助函数已存在，PUT /{id}/role 审计已实现。新端点复用即可。
3. **无通知模块处理**：`reset-password` v1 返回临时密码由前端安全交付，邮件通知作为后续迭代或接入现有告警通道，不阻塞发布。
4. **字段错配修复**：前端 `page.tsx` 的 `u.name` 改为 `u.display_name`；同时 `UserOut` 与 `api-reference.md` 对 `last_login_at/created_at/updated_at` 的描述不一致，需统一（建议 `UserOut` 增字段或文档降级）。
5. **权限边界确认**：`reset-password` 是否允许 admin 重置其他 admin、bulk 是否允许批量删 admin，需在 M1 由产品/安全明确，写入 ADR。
6. **软删除一致性**：用户禁用后，其 `created_by` 关联的产品/术语保留，审计可追溯；若未来需要"硬删除"，须另立 ADR（当前按 PRD 仅软删除）。
7. **令牌撤销表为运行期硬依赖（已 live，建议 P1）**：令牌撤销与强制改密相关端点（含 `/logout-all` 及规划中的 API-3/4/5）依赖 `refresh_token_blacklist` 表，须在建库阶段（init_db 导入该模型或 Alembic 迁移）确保该表存在，否则运行时 500。该故障当前已由 `POST /api/auth/logout-all`（auth.py:172）触发——`revoke_all_user_tokens` 在 `security.py:98` 对 `RefreshTokenBlacklist` 做 `db.query(...).update(...)`，而~~该模型仅在函数内惰性 import、`init_db.py` 的 `create_all` 不会加载它，新建库将缺表~~ ⚠️ 已勘误（E1）：models/__init__.py 已导入，create_all 会自动建表；API-3/4/5 仅放大故障面，非风险起点。另：`force_password_change` 列因 `init_db.py` 已导入 `UserProfile` 会被 `create_all` 建出，仅"走陈旧迁移 001"路径才缺，真正当前 bug 是**缺表**而非缺列。

---

## 附录 A：依赖矩阵

| 依赖项 | 位置 | 被哪些缺失 API 使用 | 现状 |
|--------|------|-------------------|------|
| `require_admin` | `core/deps.py` | 全部 5 个 | ✅ 已有 |
| `get_password_hash` | `core/security.py` | API-1, API-4 | ✅ 已有 |
| `revoke_all_user_tokens` | `core/security.py` | API-3, API-4, API-5 | ✅ 已有 |
| `validate_password_strength` | `utils/password_validator.py` | API-1, API-4 | ✅ 已有 |
| `UserCreate` | `schemas/auth.py` | API-1 | ✅ 已有（复用） |
| `UserUpdate` | `schemas/auth.py` | API-2 | ❌ 需新建 |
| `AdminResetPasswordRequest` | `schemas/auth.py` | API-4 | ❌ 需新建 |
| `BulkUserActionRequest` | `schemas/auth.py` | API-5 | ❌ 需新建 |
| `write_audit_log` 帮助函数 | `core/audit.py`（建议） | 全部写操作 | ❌ 需新建（含回填 role-change） |
| 邮件/通知模块 | — | API-4（可选） | ❌ 缺失，v1 后置 |
| 审计中间件 | — | — | ❌ 不存在（采用手动写入） |

## 附录 B：错误码约定（写操作统一）

| 状态码 | 含义 | 触发场景 |
|--------|------|---------|
| 400 | 参数/校验失败 | 角色非法、密码弱、空批量、自降级/自禁用、重置自己 |
| 401 | 未认证 | 缺/无效 token |
| 403 | 权限不足 | 非 admin（且 403 不泄露资源是否存在） |
| 404 | 资源不存在 | user_id 查无此人（部分批量失败计入 errors） |
| 409 | 资源冲突 | 邮箱已注册（建议替代 400 邮箱冲突） |

---

*— 文档一完 —*
