# 全面工程审查报告 — 跨境产品资料中英对照系统

**日期**：2026-07-30
**工作流**：技术债评估（Workflow 5）+ 综合代码审查（Workflow 1）合并执行
**参与成员**：Cody（代码审查师）/ Archi（架构师）/ Rex（SRE 工程师）/ Tessa（测试专家）/ Docu（技术文档师）

---

## 📌 TL;DR（执行摘要）

- **整体结论**：相较 2026-07-24 的 🔴 不通过，系统已发生**跨越式改善**——原 77 项发现中约 **58 项已 RESOLVED / 收敛**，认证安全、审计日志、生产 PG、Alembic 迁移、全局异常处理、资源限制、Runbook、CORS 等核心债已还清；本次评级上调为 **🟡 有条件通过**。
- **当前开放债务分布**：🔴 高优先级 12 项 / 🟠 高 32 项 / 🟡 中 14 项 / 🟢 低 10 项（已合并去重，含 prior 未关闭项 + 新发现）。
- **真正的生产阻断点（P0）共 3 项**：① 生产 Prometheus 未挂载告警规则（N1）；② 生产 nginx 缺 TLS 证书无法启动（N2）；③ 数据库迁移脚本验证步骤崩溃（N3）。这三项不修，生产部署即"盲飞/起不来"。
- **最强信号**：代码与架构质量已到"良好"区间（认证 A、可观测性 A-），但**可运维链路最后一公里**与**测试金字塔结构性倒挂**仍是主要短板。

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🟡 有条件通过 |
| 阻塞项数量（P0 生产阻断） | 3 项（Prometheus 告警未挂载 / nginx 缺证书 / 迁移脚本崩溃） |
| 关键行动项 | 18 条（P0×3 / P1×9 / P2×6） |
| 建议下一步 | 先打 **Sprint-Hotfix**（≤3 天）修掉 3 个 P0 运维阻断 + refresh-token XSS + 限流 fail-open，再进入一轮结构性还债（测试/E2E/同步 I/O/文档契约） |
| 与上次对比 | 77 项 → 当前开放约 68 项（其中 58 项原债已解决，新增/残留约 68 项以结构性债为主） |

---

## 🔄 与 2026-07-24 审查的对比（Prior 解决情况）

| 维度 | 参与成员 | Prior 项数 | RESOLVED | PARTIAL | UNRESOLVED | 代表性已解决项 |
|------|---------|-----------|-----------|---------|-----------|---------------|
| 代码/安全 | Cody | 12 | 7 | 5 | 0 | 默认 admin 凭证、localStorage Token、无 CORS/异常处理器、无优雅停机 |
| 架构 | Archi | 15 | 11 | 3 | 1 | httpOnly Cookie、审计日志、导出阻断、生产 PG、Alembic、Docker 标签、全局异常 |
| 运维/SRE | Rex | 33 | 8 | 17 | 8 | 资源限制、Grafana 强密码、Runbook、CORS、健康检查 curl、JUnit XML |
| 测试 | Tessa | 20 | 9 | 9 | 2(含 WORSENED) | pytest markers、reviewer fixture、audit/consistency/密码强度覆盖、全量 145 测试绿 |
| 文档 | Docu | 13 | 8 | 2 | 3 | LICENSE/CHANGELOG/CONTRIBUTING/Runbook/README 目录名/monitoring-guide |

> 注：Rex 的"PARTIAL/UNRESOLVED"多为"配置已就位但未接通/未验证"（如告警规则写了但 prod 未挂载），这正是本次 P0 的来源。

---

## 🔍 当前开放债务清单（合并去重，按严重度排序）

> 合并规则：跨成员重复项已合一（如"导出双重全表扫描"=Cody N5+Archi B3；"限流缺陷"=Cody N2+Tessa B5；"API 契约漂移"=Docu N1+Archi B11；"依赖债"=Cody N7+Archi B10；".env/密钥管理"=Cody N11+Rex N17+Docu #64）。
> 紧急度：P0=生产阻断，P1=本迭代必须，P2=结构性还债。

### 🔴 高优先级（12 项）

| # | 严重度 | 维度 | 问题 | 来源 | 紧急度 |
|---|--------|------|------|------|--------|
| F1 | 🔴 | 运维/告警 | 生产 Prometheus 仅挂载 prometheus.yml，**未挂载 alerts.yml** → 12+ 告警规则在 prod 不生效（Prometheus 甚至可能因 rule_files 缺失而启动失败） | Rex N1 | P0 |
| F2 | 🔴 | 运维/安全 | 生产 nginx 引用 `deploy/nginx/ssl` 证书目录但**该目录不存在** → nginx 因缺 fullchain.pem/privkey.pem 启动失败，HTTPS 无法启用 | Rex N2 | P0 |
| F3 | 🔴 | 部署/数据 | `postgresql_migration.py:266` 验证步骤引用未定义变量 `postgres_table`（应为 `table`）→ NameError，迁移后自动验证崩溃 | Rex N3 | P0 |
| F4 | 🔴 | 安全运维 | dev/base compose 仍 `ports: "5432:5432"` 暴露宿主机 + `POSTGRES_PASSWORD=...:-postgres` 默认弱密码 | Rex N4 | P1 |
| F5 | 🔴 | 安全/架构 | **同步 DB I/O**：async FastAPI + 同步 SQLAlchemy/psycopg2，无 async session，并发吞吐受 uvicorn 线程池限制 | Archi B1 | P2 |
| F6 | 🔴 | 测试/配置 | **双配置文件冲突**：pytest.ini 与 pyproject.toml 并存，pytest 取 pytest.ini，pyproject 的 --cov/pythonpath 被忽略 → 默认 `pytest` 不跑覆盖率 | Tessa B1 | P1 |
| F7 | 🔴 | 测试/E2E | **无真实端到端测试**：后端 tests/e2e 仅用 TestClient 伪 E2E；前端 Playwright 未被 CI 执行 | Tessa B2 | P2 |
| F8 | 🔴 | 测试/CI | **CI 配 Postgres 服务但测试跑 SQLite**（conftest 硬编码 sqlite 忽略 DATABASE_URL）→ 方言相关缺陷（JSON/数组/UUID/排序）漏测 | Tessa B3 | P1 |
| F9 | 🔴 | 测试/覆盖 | **核心写端点零覆盖**：users.py 覆盖率仅 29%，/auth/change-password、/users(CRUD/me/bulk)、import 更新模式无回归保护 | Tessa B4 | P1 |
| F10 | 🔴 | 测试/并发 | **限流计数器非线程安全** + fail-open：main.py 用普通 dict 作登录限流计数；RateLimiter.check 异常时 `return True`（Redis 不可用即放行） | Cody N2 + Tessa B5 | P1 |
| F11 | 🔴 | 文档/契约 | **API 契约漂移**：api-reference.md 含 3 个未实现 `/terms/{term_id}` 幽灵端点；已实现的 /users 禁用/重置/批量被误标"未实现"；与 CHANGELOG"删 11 虚构端点"声明矛盾 | Docu N1 + Archi B11 | P1 |
| F12 | 🔴 | 文档/过时 | `docs/P1-P2-修复报告.md` §4 仍称"用户手册和API文档 未实现"，但 07-30 已交付 | Docu #19 | P1 |

### 🟠 高（32 项，精选关键项，完整清单见各成员附录）

| # | 维度 | 问题 | 来源 | 紧急度 |
|---|------|------|------|--------|
| F13 | 安全/认证 | **refresh token 经 JSON body 返回且服务端从不读取该 cookie** → 客户端必然存 JS 存储，7d TTL 可被 XSS 窃取，部分抵消 Cookie 改造收益 | Cody N1 | P1 |
| F14 | 安全/认证 | `force_password_change` 仅作前端提示，**服务端 get_current_user 不拦截** → 带该标志用户仍可调用全部 API | Cody N3 | P1 |
| F15 | 安全/认证 | `/auth/register` 开放注册、无独立限流 → 可批量建号/邮箱枚举 | Cody N4 | P1 |
| F16 | 安全/正确 | CSV 注入防护仍缺 `\n` 检查（csv_utils 仅查 `= + - @ \t \r`） | Cody #18 | P1 |
| F17 | 架构/正确 | **一致性规则文件路径错位**：consistency.py 解析到 `/data/consistency-rules.json`，但 prod 挂载 `./data→/app/data` 且 build 不含仓库根 data/ → L2/L3 检测 FileNotFoundError 被吞，**静默失效** | Archi B2 | P1 |
| F18 | 架构/性能 | 导出全表扫描 + 双重调用（check_products_batch 内已调 check_all_products，export.py 又调一次） | Archi B3 / Cody N5 | P1 |
| F19 | 架构/惯用 | 全局异常用 BaseHTTPMiddleware 实现，对 StreamingResponse(CSV) 有交互风险 | Archi B4 | P2 |
| F20 | 运维/可观测 | **多 worker 指标分片**：`/metrics/prometheus` 仅返回单 worker 数据，Redis 聚合器未接入暴露端点，仍手工拼字符串、重启归零 | Rex N6 | P1 |
| F21 | 运维/可观测 | prod 未部署 node-exporter/cadvisor/postgres_exporter；prometheus.yml 仍 scrape 不存在的 target（永久 DOWN 噪音） | Rex N7 | P1 |
| F22 | 告警 | alertmanager webhook 指向未定义服务 `alertmanager-webhook`（死配置），默认走 email 需 SMTP | Rex N8 | P1 |
| F23 | 运维/备份 | 备份无自动调度（无 cron/systemd） | Rex N9 | P1 |
| F24 | 部署 | 单实例单点故障（backend/postgres/redis 无副本） | Rex N10 | P2 |
| F25 | 部署 | Graceful shutdown 在 gunicorn 多 worker 下未验证 | Rex N11 | P1 |
| F26 | 运维 | prod Prometheus 保留期未显式配置（默认 15d，与 monitoring-only 200h 不一致） | Rex N12 | P1 |
| F27 | 运维 | 无自动 synthetic/外部探测（仅手动 health-check.sh） | Rex N13 | P2 |
| F28 | 部署/验证 | 部署清单监控验证项引用不存在的指标名（job/histogram 名不符）→ 假阳性"监控已验证" | Rex N14 | P1 |
| F29 | 安全运维 | `docker-compose.full.yml` 硬编码默认管理员密码回退 `CmsAdmin2026!`；staging 硬编码弱 SECRET_KEY | Rex N15 | P1 |
| F30 | 运维 | Docker 日志无轮转（默认 json-file 无上限） | Rex N16 | P1 |
| F31 | 安全运维 | 根 `.env` 含真实硬编码 SECRET_KEY 且 gitignore 行为异常，有误提交泄露风险 | Rex N17 | P1 |
| F32 | 部署 | `instant_fixes.py` 多数为空操作/打印，不真正修复（误导"已修复"） | Rex N18 | P2 |
| F33 | 测试/异味 | test_products.py:103 仍 `__import__` 且查询结果未使用（死代码） | Tessa B6 | P2 |
| F34 | 测试/重复 | test_auth.py 与 test_security.py/test_security_comprehensive.py 重复（register 越权、401-no-token） | Tessa B7 | P2 |
| F35 | 测试/质量 | 速率限制测试模糊：断言 `in [401,429]`，从不验证 429；Redis mock 致 429 分支基本不执行 | Tessa B8 | P1 |
| F36 | 测试/覆盖 | 缺黑名单/过期 token fixture，token 黑名单机制无直接测试 | Tessa B9 | P1 |
| F37 | 测试/结构 | tests/integration/ 空置，集成测试散落根目录并打 @integration，命名误导 | Tessa B10 | P2 |
| F38 | 测试/覆盖 | import 更新模式(mode=update)未测试，schemas/import_.py 覆盖率 0% | Tessa B11 | P1 |
| F39 | 测试/分布 | 覆盖率极不均：整体 73% 但 users.py 29%、terms.py 44%、utils/i18n.py 0%、redis.py 58% | Tessa B12 | P2 |
| F40 | 文档/完整 | api-reference.md 漏记 GET /users/me（代码+README 均有） | Docu N2 | P1 |
| F41 | 文档/可用 | backup-strategy.md 备份脚本先 `stop` 再 `exec cp` → 容器已停，exec 必失败 | Docu N3 | P1 |
| F42 | 文档/准确 | api-reference.md"文档更新清单"声称"新增 /audit-logs/{log_id}"，但代码/正文均无该端点 | Docu N4 | P2 |
| F43 | 文档/配置 | 3×.env + 6×docker-compose 变体，无"哪种场景用哪个"配置矩阵 | Docu #64 | P2 |
| F44 | 架构/审计 | 导入操作无审计日志写入（与 products/users 不一致） | Archi B5 | P1 |

### 🟡 中（14 项，摘要）

| # | 维度 | 问题 | 来源 |
|---|------|------|------|
| F45 | 架构/i18n | i18n 模块未接入 API 响应层，无 Accept-Language 协商 | Archi B7 |
| F46 | 架构/治理 | 无 API 弃用/sunset 机制；audit_logs 无保留/清理策略 | Archi B8 |
| F47 | 安全 | Refresh 有效期 7d 偏长（原 24h 反而变长） | Archi B9 |
| F48 | 交付 | python:3.12-slim 未锁补丁；psycopg2-binary 为开发构建 | Archi B10 |
| F49 | 依赖 | passlib 1.7.4+bcrypt 4.3 每次 hash 触发 trapped AttributeError；python-jose 停滞；psycopg2-binary 非生产推荐 | Cody N7 |
| F50 | 正确 | extra_fields Schema 校验在文件缺失时静默跳过且不校验 required | Cody #40/N9 |
| F51 | 数据模型 | term_dictionary.created_by 仍无 FK | Cody #14 / Archi B6 |
| F52 | 测试/占位 | /products/stats 端点不存在且测试被整体 skip | Tessa B13 |
| F53 | 测试/性能 | 测试套件极慢：145 测试 ≈9.6 分钟（每测试重建全库） | Tessa B14 |
| F54 | 测试/CI | coverage.xml 在沙箱因回收站不可用写出失败（真实 ubuntu CI 不受影响） | Tessa B15 |
| F55 | 文档/过时 | monitoring-guide.md 示例日志日期仍 2024 | Docu N5 |
| F56 | 文档/可用 | monitoring-guide.md Prometheus target 配置乱码 | Docu N6 |
| F57 | 架构/认证 | 单设备 /logout 只把 refresh 入黑名单、不 bump token_version，access token(24h) 登出后仍可用 | Cody #10 |
| F58 | 性能 | change_password/upload_file 为 async def 却做阻塞 bcrypt/DB/文件 I/O | Cody N6 |

### 🟢 低（10 项，摘要）

| # | 维度 | 问题 | 来源 |
|---|------|------|------|
| F59 | CSRF | middleware 无 Origin/Referer 时放行（samesite+lax 已大幅缓解） | Cody N8 |
| F60 | 资源泄漏 | 上传临时文件仅靠 TTLCache 淘汰，淘汰后文件永不删 | Cody N10 |
| F61 | 配置 | 根 .env 与 backend/.env 双份 SECRET_KEY 不同 | Cody N11 |
| F62 | 维护 | 工程根残留 _patch_auth.py / temp_patch1.txt / nul 等调试文件 | Cody N12 |
| F63 | 维护 | 仅 1 个 Alembic 迁移，后续模型变更易 schema 漂移 | Cody N13 |
| F64 | 运维 | /metrics/prometheus 经 nginx 暴露无 IP 白名单 | Rex N20 |
| F65 | 部署 | monitoring-only compose + backend/frontend 无版本标签，回滚靠 git checkout+rebuild | Rex N21 |
| F66 | 部署 | ephemeral SECRET_KEY 致重启后 JWT 全失效（副作用） | Rex N22 |
| F67 | 文档 | user-manual.md 无真实截图，screenshots/ 仅 README.md | Docu #74 |
| F68 | 文档/结构 | README 空标题"### 数据库迁移"死章节 | Docu N7 |

---

## 📊 修复优先级排序（Priority = (Impact + Risk) × (6 - Effort)）

| 排名 | 修复项 | I | R | E | Priority | 紧急度 |
|------|--------|---|---|---|----------|--------|
| 1 | F1 生产挂载 alerts.yml | 4 | 5 | 1 | **45** | P0 |
| 2 | F3 修复迁移脚本验证变量 | 4 | 4 | 1 | **40** | P0 |
| 3 | F4 关闭 dev PG 暴露+默认密码 | 4 | 4 | 1 | **40** | P1 |
| 4 | F2 提供 nginx TLS 证书 | 5 | 4 | 2 | **36** | P0 |
| 5 | F13 refresh token 改 httpOnly cookie | 4 | 4 | 2 | **32** | P1 |
| 6 | F10 限流 fail-open+线程安全 | 4 | 4 | 2 | **32** | P1 |
| 7 | F17 一致性规则路径配置化 | 4 | 4 | 2 | **32** | P1 |
| 8 | F16 CSV 补 `\n` 检查 | 2 | 3 | 1 | **25** | P1 |
| 9 | F11 API 契约对齐(删幽灵/改误标) | 3 | 3 | 2 | **24** | P1 |
| 10 | F14 强制改密服务端拦截 | 3 | 3 | 2 | **24** | P1 |
| 11 | F6 合并 pytest 配置 | 3 | 3 | 2 | **24** | P1 |
| 12 | F8 CI 改用 Postgres 测试库 | 3 | 4 | 3 | **21** | P1 |
| 13 | F40 补 /users/me 文档 | 2 | 2 | 1 | **20** | P1 |
| 14 | F5 异步 DB 访问(ADR-008) | 3 | 4 | 5 | **7** | P2 |
| 15 | F9 补核心写端点测试 | 4 | 3 | 5 | **7** | P2 |
| 16 | F7 Playwright 入 CI | 3 | 3 | 4 | **12** | P2 |

---

## 🗂️ 分阶段修复计划

### Sprint-Hotfix（≤3 天）— 打通生产最后一公里
1. **F1** 生产 Prometheus 挂载 alerts.yml + `promtool check rules` 进 CI — DevOps
2. **F2** certbot 脚本/预置证书 + 部署前校验证书存在 — DevOps
3. **F3** 改 `postgres_table`→`table` + 加迁移集成测试 — 后端
4. **F13** refresh token 改由 httpOnly cookie 读取/轮换，缩短 TTL — 全栈
5. **F10** RateLimiter.check 异常改 fail-closed + 移除/加锁内存回退 — 后端

### Sprint-A（第 1-2 周）— 安全边界 + 契约一致性
6. **F4/F29/F31** 密钥与 .env 治理：移除硬编码回退、统一 .env.example、密钥入 vault — DevOps
7. **F14/F15/F57** 强制改密服务端拦截、关闭/审批公开注册、单设备登出 bump token_version — 后端
8. **F16** CSV 注入补 `\n` — 后端
9. **F17/F18** 一致性规则路径配置化 + 导出去重/增量 — 后端
10. **F11/F12/F40/F41** API 文档与代码对齐（删幽灵端点、改误标、补 /users/me、修备份脚本、更新 P1-P2 报告）— 文档
11. **F20/F21/F22** 指标多 worker 聚合、prod 加 exporter、alertmanager webhook 落地 — DevOps
12. **F6/F8** 合并 pytest 配置、CI 改用 Postgres 测试库 — QA

### Sprint-B（第 3-5 周）— 结构性还债
13. **F9/F35/F36/F38** 补核心写端点 + 黑名单 token + import update 模式测试；速率限制测试改真 429 — QA
14. **F7/F39** Playwright 接入 CI；按模块设覆盖门槛（users/terms/i18n 优先）— QA
15. **F5/F19/F58** ADR-008 异步 DB 访问；异常处理迁原生 exception_handlers；async 阻塞点改线程池 — 后端
16. **F23/F24/F25/F26/F27** 备份调度、单点故障评估、graceful shutdown 验证、Prom 保留期、synthetic 探测 — DevOps
17. **F44/F45/F51** 导入审计、i18n 接入、term FK 迁移 — 后端
18. **F49/F48** 依赖债：弃 passlib 直用 bcrypt/argon2、python-jose→PyJWT、psycopg→psycopg、镜像锁版本 — 后端

---

## ✅ 行动清单（按优先级排序）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 1 | **生产 Prometheus 挂载 alerts.yml** — prod compose 增加 volumes 挂载，CI 加 `promtool check rules` | DevOps | P0 | Hotfix |
| 2 | **提供 nginx TLS 证书** — certbot 脚本 + 部署前证书存在校验，否则 nginx 起不来 | DevOps | P0 | Hotfix |
| 3 | **修复迁移脚本验证崩溃** — `postgres_table`→`table`，加迁移集成测试 | 后端 | P0 | Hotfix |
| 4 | **refresh token 改 httpOnly cookie** — 杜绝 JS 存储 XSS 窃取，缩短 TTL | 全栈 | P1 | Sprint-A |
| 5 | **限流 fail-closed + 线程安全** — Redis 不可用时拒绝放行，移除死内存回退 | 后端 | P1 | Hotfix |
| 6 | **一致性规则路径配置化** — 修复 prod L2/L3 静默失效 | 后端 | P1 | Sprint-A |
| 7 | **API 文档与代码对齐** — 删 3 幽灵端点、改"未实现"误标、补 /users/me、更新 P1-P2 报告 | 文档 | P1 | Sprint-A |
| 8 | **强制改密服务端拦截** — force_password_change 用户仅放行 /change-password 与 /me | 后端 | P1 | Sprint-A |
| 9 | **合并 pytest 配置 + CI 改 Postgres 测试库** — 消除双配置冲突与方言漏测 | QA | P1 | Sprint-A |
| 10 | **CSV 注入补 `\n` 检查** — 对齐 OWASP 全集 | 后端 | P1 | Sprint-A |
| 11 | **密钥/.env 治理** — 移除 full.yml 默认密码回退、统一 .env.example、密钥入 vault | DevOps | P1 | Sprint-A |
| 12 | **补核心写端点测试** — users.py 29%→目标 80%+，覆盖 change-password/users CRUD/bulk | QA | P2 | Sprint-B |
| 13 | **Playwright E2E 接入 CI** — 填补金字塔顶端 | QA | P2 | Sprint-B |
| 14 | **异步 DB 访问(ADR-008)** — asyncpg + async session 或正式确立同步多进程架构 | 后端 | P2 | Sprint-B |
| 15 | **依赖债清理** — passlib→bcrypt/argon2、python-jose→PyJWT、psycopg2-binary→psycopg | 后端 | P2 | Sprint-B |
| 16 | **导入操作补审计日志** — 与 products/users 一致 | 后端 | P1 | Sprint-A |
| 17 | **prod 加 node/cadvisor/postgres exporter** — 消除永久 DOWN 噪音与监控盲区 | DevOps | P1 | Sprint-A |
| 18 | **部署清单监控验证项对齐真实指标名** — 消除假阳性"已验证" | DevOps | P1 | Sprint-A |

---

## ⚠️ 待完善 / 已知局限

- **本报告基于静态代码/配置核查 + Tessa 实测 145 测试**；未实际 `docker compose up` 运行，F1/F2 的"启动失败"为强推断，建议在预发环境实测确认。
- **前端构建未深度审查** — 本次聚焦后端 + 配置 + 文档；前端 Next.js 打包/产物未做安全/性能走查。
- **无性能/负载基准** — 未跑 Locust/k6，同步 I/O（F5）在高并发下的具体退化未量化。
- **依赖漏洞未跑 pip-audit/safety** — F49 依赖债基于代码导入推断，建议补一次 `pip-audit`。
- **Cody 的逐行审查结论已纳入**；Archi/Rex/Tessa/Docu 的细分项见下方索引，完整原始产出可回溯。

---

## 📚 数据来源 & 成员产出索引

- **Cody（代码审查师）原始产出**：prior 12 项核对（7 RESOLVED / 5 PARTIAL）+ 新发现 N1-N13。关键：refresh token XSS(N1)、限流 fail-open(N2)、强制改密未拦截(N3)、开放注册(N4)、导出双扫(N5)、async 阻塞(N6)、依赖债(N7)、双 .env(N11)、根残留文件(N12)、单迁移(N13)。
- **Archi（架构师）原始产出**：prior 15 项核对（11 RESOLVED / 3 PARTIAL / 1 UNRESOLVED）+ 新债 B1-B11 + ADR-008~013。关键：同步 I/O(B1🔴)、一致性路径错位(B2)、导出双扫(B3)、BaseHTTPMiddleware(B4)、导入无审计(B5)、API 契约漂移(B11)。
- **Rex（SRE 工程师）原始产出**：prior 33 项核对（8 RESOLVED / 17 PARTIAL / 8 UNRESOLVED）+ 新债 N1-N22。关键：Prometheus 未挂载告警(N1🔴)、nginx 缺证书(N2🔴)、迁移崩溃(N3🔴)、dev PG 暴露(N4🔴)、多 worker 指标分片(N6)、exporter 缺失(N7)、webhook 死配置(N8)。
- **Tessa（测试专家）原始产出**：prior 20 项核对（9 RESOLVED / 9 PARTIAL / 2 含 WORSENED）+ 新债 B1-B15，**实测 145 测试通过 / 2 skip / 覆盖率 73%**。关键：双配置冲突(B1🔴)、无真实 E2E(B2🔴)、CI/SQLite 错配(B3🔴)、写端点零覆盖(B4🔴)、限流非线程安全(B5🔴)、users.py 29%。
- **Docu（技术文档师）原始产出**：prior 13 项核对（8 RESOLVED / 2 PARTIAL / 3 UNRESOLVED）+ 新债 N1-N8。关键：幽灵端点(N1🔴)、P1-P2 报告过时(#19🔴)、漏记 /users/me(N2)、备份脚本不可跑(N3)、配置矩阵缺失(#64)。

---

> 本报告由工程保障团队 AI 协作生成，关键决策请由人类工程负责人复核。
> 参与成员：Cody（代码审查师）· Archi（架构师）· Rex（SRE 工程师）· Tessa（测试专家）· Docu（技术文档师）
> 编排整合：甄宇航 · 工程督导
