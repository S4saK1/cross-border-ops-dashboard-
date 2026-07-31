# 工程审查状态更新 — 待修复项清单（R1–R4 实测复核）

**日期**：2026-07-31
**工作流**：技术债评估（Workflow 5）+ 综合代码审查（Workflow 1）更新
**参与成员**：Cody（代码审查师）/ Archi（架构师）/ Rex（SRE 工程师）/ Tessa（测试专家）/ Docu（技术文档师）
**基线**：2026-07-30 综合审查（🟡 有条件通过，68 项开放）+ 2026-07-31 修复验证（🔴 不通过，61 项含 6 P0）
**本次动作**：五成员**并行实读代码/配置 + 实跑检查**复核 R1–R4 修复真实落地情况，重标开放项。

---

## 📌 TL;DR（执行摘要）

- **整体结论：🔴 不通过（仍不可宣布可部署）**。历史记录称"R1–R4 修复后 148 测试全绿、评级可从 🔴→🟡"——**本次实测推翻该结论**：R4 三项核心声称（refresh-cookie 读取 / /register 限流 / conftest StaticPool）**均未真正进入代码**，仅 refresh cookie 的"写入"半落地、"读取"从未实现。
- **严重度分布（剩余开放项，已去重合并）**：🔴 严重 ~15 项 / 🟠 高 ~32 项 / 🟡 中 ~15 项 / 🟢 低 ~10 项，合计约 **72 项**（含本轮新发现 9 项高优 + 若干低优）。
- **真正的硬阻断（P0）仍有约 9 项**：nginx 缺 TLS 证书起不来、根 `.env` 真实密钥被 compose 自动注入 prod、alertmanager 邮件告警链路死配置、备份无任何调度、生产 4-worker 密钥分裂、/register 开放无限流、强制改密服务端不拦截、refresh token 仍走 JSON body 可被 XSS、真实覆盖率 69% 已跌破 CI 70% 门槛。
- **最强信号**：R2 的"一致性引擎守护测试"是唯一实质性加固；但安全边界（认证/限流/审计/密钥治理）与测试可信度（覆盖率虚高、terms 测试静默 0 条）仍是全局最大短板。

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🔴 不通过（R1–R4 未如记录全落地，硬阻断仍在） |
| 阻塞项数量（P0 硬阻断/高优） | 约 9 项（见下方 P0 段） |
| 关键行动项 | 21 条（P0×9 / P1×8 / P2×4） |
| 建议下一步 | 先做 **P0 止血包**（证书 / 密钥治理 / 告警链路 / 备份调度 / 覆盖率诚实化 / 认证安全边界），再进入 P1 安全加固 + 测试可信度修复 |
| 与 07-31 报告对比 | 原"6 P0 硬阻断"中运维侧 4 项（NEW-1/NEW-2/R3/F1）实测已修；但 R4 三项安全声称集体落空，叠加本轮新发现 9 项高优，开放债不降反增 |

---

## 一、R1–R4 修复落地实测（纠正历史结论）

> 历史会话记录称 R1–R4 已执行并"145/148 测试全绿"。本次逐项目实读代码，**纠正如下**：

| 修复轮 | 历史声称 | 实测结论 | 关键证据 | 判定 |
|--------|---------|---------|---------|------|
| **R1** | auto_error=False / .dockerignore 加 .env / redis 依赖 / 两处 ImportError→日志 | 基本落地，1 处偏差 | security.py:13 ✅；.dockerignore ✅；requirements.txt:11 ✅；monitoring.py:15-16 / import_.py:106-107 ✅；**但 'x-csrf-token' 脱敏未加**（exception_handler.py:36 仅含 authorization/cookie） | ⚠️ 基本 RESOLVED |
| **R2** | backup.sh 重写 / 迁移变量修复 / /health 503 / api-reference 幽灵端点清除 / 一致性路径修复 | 全部实测属实 | backup.sh:1-102 ✅（**但带 UTF-8 BOM**，见新#1）；postgresql_migration.py ✅；main.py:225-229 503 ✅；api-reference.md:560 ✅；consistency.py:19,27 ✅ | ✅ RESOLVED（BOM 待清） |
| **R3** | test_consistency +3 守护 / test_permissions 严格断言 / conftest 读 DATABASE_URL / README 等补 SECRET_KEY 前置 / backup-strategy 重写 | 基本落地，1 处偏差 | test_consistency.py:85-149 ✅（R9 真守护）；test_permissions.py:82 ==200 ✅；conftest.py:30-54 读 DATABASE_URL（**但失败静默 fallback SQLite**，H2 假绿未消）；README/DEPLOY/QUICKSTART ✅；backup-strategy.md ✅ | ✅ RESOLVED（H2 待消） |
| **R4** | refresh token 迁 cookie 读取 / /register 限流 / ADR-008~013 / conftest StaticPool / alerts.yml 挂载 / 日志轮转 | **三项核心安全声称集体落空** | ① refresh **只写不读**：auth.py:117-118 仍强制从 JSON body 读 token，全码无读 refresh cookie 逻辑（security.py:174-209 仅 set）→ N1/F13 **实质未修**；② **/register 无限流**：main.py:146 限流仅匹配 login（N4/F15 仍 OPEN）；③ **conftest 无 StaticPool**：conftest.py:46-54 仍是 tempfile 文件型 SQLite（Archi 与 Tessa 双重确认；R4 报告表述必须改写）；④ ADR-008~013 文档存在但未实施（对应 B12/B3/B5 仍 OPEN）；⑤ alerts.yml 挂载 ✅（N1/F1 RESOLVED）；⑥ 日志轮转 ✅（N16 RESOLVED） | ❌ 部分 RESOLVED / 安全声称落空 |

---

## 二、已验证修复（RESOLVED，可从开放债勾销）

- **运维**：prod 裸 `ports:` 已删（R1/NEW-1）、backup.sh 重写（R2/NEW-2）、恢复手册改 docker compose cp（R3/N23）、prod 挂载 alerts.yml（N1/F1）、迁移脚本 `postgres_table`→`table`（N3/F3）、部署清单指标名对齐（N14）、Docker 日志轮转（N16）、monitoring-guide 乱码清除（N24）、PRD 旧 db 路径（N26）、/health 返回 503（H1）。
- **架构**：.dockerignore 密钥（backend 侧，A-N1）、redis 依赖（A-N2）、/health 503（A-N3）、一致性规则路径（B2/F17）、API 契约幽灵端点清除（B11）。
- **代码**：auto_error 死代码激活（C-1）、两处 ImportError 改日志（C-5*）、一致性路径（F17）。
- **测试**：一致性守护 3 条（R9）、覆盖率 xml 沙箱问题（B15/F54，环境）。
- **文档**：README/DEPLOY/QUICKSTART SECRET_KEY 前置（R13）、api-reference 幽灵端点（R14/N1）、backup-strategy 恢复章节（N3/F41）、monitoring-guide 乱码（F56）。

---

## 三、🔍 仍需修复的开放项（按领域 + 严重度排序）

> 合并规则：跨成员重复项已合一（如 F17=B2、F13=N1=H3、F10=H9、F15=N4、F14=N3、F18=B3、F44=B5、F51=B6、F47=B9、F48=B10、F6=B1、F7=B2-test、F8=B3-test、F9=B4、F33=B6、F34=B7、F35=B8、F36=B9、F37=B10、F38=B11、F39=B12、F52=B13、F53=B14、F54=B15）。

### 🔴 P0 — 硬阻断 / 高优安全阻断（约 9 项，必须先行）

| # | 维度 | 问题 | 来源 | 文件:行 |
|---|------|------|------|---------|
| P0-1 | 运维/TLS | 生产 nginx 引用 `deploy/nginx/ssl` 证书目录**不存在** → nginx 起不来，HTTPS 全站白屏 | Rex N2/F2 | prod.yml:210 / deploy/nginx/ |
| P0-2 | 安全/密钥 | 根 `.env` 含真实 SECRET_KEY，compose 自动读入并注入 prod；`docker compose config -q` 实测 SECRET_KEY 不报缺失即因被根 .env 填坑 | Rex N17 / Archi#5 | .env:2 |
| P0-3 | 运维/告警 | alertmanager 邮件链路死配置：prod alertmanager **无 environment 段** → SMTP 变量 envsubst 全空；镜像为 busybox 基底**无 envsubst 二进制** → 告警全链路不通 | Rex 新#2 | prod.yml:148-165 |
| P0-4 | 运维/备份 | 备份**无任何调度**（cron/ofelia/systemd 均无），runbook 称"daily via cron"与实现不符 | Rex N9 | 全仓 |
| P0-5 | 安全/认证 | **refresh token 仍走 JSON body 返回 + 服务端不读 refresh cookie**（R4 声称落空）→ 7d TTL 可被 XSS 窃取 | Cody N1/F13/H3 | auth.py:117-118 / security.py:174-209 |
| P0-6 | 安全/认证 | **/auth/register 开放注册、无限流** → 可批量建号/邮箱枚举（R4 声称落空） | Cody N4/F15 | main.py:146 |
| P0-7 | 安全/认证 | **强制改密服务端不拦截**：get_current_user 不检查 force_password_change claim → 持该标志用户可调全部接口 | Cody N3/F14 | auth.py:92-103 / core/deps.py |
| P0-8 | 测试/可信度 | **test_terms.py 静默收集 0 测试**（3 个 def 误缩进嵌套进 `_seed_terms`，且 admin_token 误用）→ terms 端点"零覆盖假象"，terms.py 仅 44% | Tessa 新N1 | test_terms.py:10-40 |
| P0-9 | 测试/可信度 | **真实覆盖率 69% 已跌破 CI 门槛 70%**：pyproject 排除 `except Exception`/`pass`/`return None` 粉饰出名义 73%（虚高 4pp） | Tessa 新N2 | pyproject.toml:16-26 |

### 🟠 高（约 32 项，精选关键项）

| # | 维度 | 问题 | 来源 | 文件:行 |
|---|------|------|------|---------|
| H1 | 安全/审计 | login 端点**无 db.commit()** → last_login_at 与 user_login 审计随 session 关闭回滚丢失（logout 有 commit 对比） | Cody 新NEW-2 | auth.py:71-113 / database.py:27-32 |
| H2 | 运维/编码 | **UTF-8 BOM 污染** backup.sh（shebang 前 BOM 致 `./backup.sh` 执行失败）+ 多个 YAML 带 BOM；ci-content-gates 的 R1-R4 规则不检 BOM（门禁盲区） | Rex 新#1 | backup.sh:1 |
| H3 | 安全/日志 | import_.py:386 `logger.error` 但模块内**从未定义 logger** → 文件解析失败预期 400 变 500（NameError） | Cody 新NEW-1 | import_.py:386 |
| H4 | 安全/密钥 | 生产 4-worker 各持不同临时密钥（SECRET_KEY 缺失时每进程 token_urlsafe）→ token 跨 worker 随机 401 | Archi 新#5 / Rex N22 | config.py:54-77 |
| H5 | 架构/性能 | **导出双重全表扫描**：check_all_products 无视 product_ids 恒扫全表，export.py 又调一次 → 重复 + ERROR 重复 | Cody N5/H7 / Archi B3/F18 | export.py:45-48 / consistency.py:62,243 |
| H6 | 架构/正确 | **导出审计早写且顺序错**：write_audit_log 在 404 分支之前提交 → 空导出也留"成功"记录（审计不可信） | Archi 新#1 | export.py:59-68 |
| H7 | 架构/中间件 | 三层 BaseHTTPMiddleware（csrf+exception+monitoring）包裹 StreamingResponse，异常逃逸 + 缓冲削弱真流式收益 | Archi B4/H8 / 新#7 | exception_handler.py:12,20-25 / csrf.py:20 / monitoring.py:31 |
| H8 | 架构/审计 | import 操作零审计（write_audit_log 全仓仅 auth/export/products/users 命中） | Archi B5/F44 | import_.py:583 |
| H9 | 安全/限流 | **限流 fail-open + 非线程安全**：redis.py `except: return True`；main.py 内存回退是死代码；IP 键无限增长无锁 | Cody H9/F10 | redis.py:154-155 / main.py:31,152-162 |
| H10 | 代码/正确 | async 端点做阻塞 I/O：change_password（bcrypt×2+DB）、upload_file（open/write/parse）未用线程池/aiofiles | Cody N6/F58 | auth.py:221 / import_.py:326 |
| H11 | 安全/运维 | dev compose 仍 `5432:5432` 暴露 + 默认弱密码（dev 范围，可接受但未改） | Rex N4/F4 | docker-compose.yml:22,40,44 |
| H12 | 运维/可观测 | 多 worker 指标分片：/metrics 进程内内存计数，无 multiprocess registry → 计数失真 | Rex N6 | monitoring.py:145-170 |
| H13 | 运维/可观测 | prod 缺 node-exporter/cadvisor/postgres_exporter → 两个 scrape target 永久 DOWN | Rex N7 | prometheus.yml:22-28 |
| H14 | 安全/运维 | /metrics/prometheus 经 nginx 公网可达，无 IP 白名单/无 auth（代码注释 unauthenticated） | Rex N20 | nginx.conf:48-51 / main.py:239-243 |
| H15 | 运维 | 单点故障：各服务 1 副本无 HA | Rex N10 | prod.yml |
| H16 | 运维 | 无 synthetic/外部探测（仅 healthcheck + up{}） | Rex N13 | monitoring/ |
| H17 | 安全/运维 | 根 .env 真实密钥在盘 + gitignore 仅挡仓库泄漏（compose 注入风险见 P0-2） | Rex N17 | .env:2 |
| H18 | 运维 | instant_fixes.py 正则热补丁危险遗留物未删 | Rex N18 | scripts/instant_fixes.py |
| H19 | 安全/依赖 | requirements 全 `>=` 零锁定 + 无 lockfile；bcrypt 上限仍允许 4.1+ 与 passlib 1.7.4 有探测冲突 | Cody H18 | requirements.txt:8-9 |
| H20 | 架构/交付 | python:3.12-slim 无 digest、psycopg2-binary 非生产推荐 | Archi B10/F48 | Dockerfile:1 / requirements.txt:17 |
| H21 | 代码/正确 | CSV 注入防护仍缺 `\n` 检查 | Cody F16 | csv_utils.py:21 |
| H22 | 代码/正确 | extra_fields schema 静默跳过 required（except FileNotFoundError: pass） | Cody F50 | product.py:69-70 |
| H23 | 数据模型 | term_dictionary.created_by 无 FK | Cody F51 / Archi B6 | term.py:20 |
| H24 | 安全/认证 | 单设备 logout 不 bump token_version → access(24h) 登出仍有效 | Cody F57 | auth.py:166-205 |
| H25 | 代码/维护 | 根目录残留调试文件 _patch_auth.py / temp_patch1.txt / nul | Cody N12/F62 | 仓库根 |
| H26 | 代码/配置 | 双 .env 密钥不同（根 vs backend）生效取决于 CWD | Cody N11/F61 | .env vs backend/.env |
| H27 | 代码/维护 | 仅 1 个 Alembic 迁移，后续模型变更易 schema 漂移 | Cody N13/F63 | alembic/versions/ |
| H28 | 代码/泄漏 | 上传临时文件仅靠 TTLCache 淘汰，淘汰后永不删 | Cody N10/F60 | import_.py:364,587 |
| H29 | 安全/配置 | ACCESS_TOKEN_EXPIRE_MINUTES=1440 覆盖默认 30min 为 24h | Cody H13 | .env:4 |
| H30 | 文档 | .env.example 默认 DATABASE_URL 占位值使 `cp .env.example .env` 后一键启动失败（容器内 localhost 不可达） | Docu 新#1 | .env.example:3 |
| H31 | 文档 | QUICKSTART 称 up 后可访问 :3000/:3001 但基础 compose 无 frontend/grafana | Docu 新#2 | QUICKSTART.md:23-25 |
| H32 | 文档 | DEPLOY.md 围栏损坏未修完（4 处 ``` 退化为 /ash）+ 第 5 节重复 | Docu 新#3 | DEPLOY.md:120-146 |

### 🟡 中（约 15 项，摘要）

| # | 维度 | 问题 | 来源 |
|---|------|------|------|
| M1 | 测试 | pytest.ini 与 pyproject 双配置冲突 → 本地跑无覆盖率（CI 靠命令行显式传） | Tessa B1/F6 |
| M2 | 测试 | 无真实 E2E：e2e 用 TestClient 伪 E2E；前端 Playwright/vitest 未入 CI | Tessa B2/F7 |
| M3 | 测试 | CI Postgres 不可达时 conftest 静默 fallback SQLite → 假绿（H2 未消） | Tessa B3/F8/H2 |
| M4 | 测试 | users.py 写端点零覆盖（29%），create/update/delete/bulk 无测试 | Tessa B4/F9/H11 |
| M5 | 测试 | 限流测试模糊 `in [401,429]` 恒真 + clear_rate_limiter 使累积不可达 | Tessa B5/B8/F35 |
| M6 | 测试 | 缺黑名单/过期 token fixture | Tessa B9/F36 |
| M7 | 测试 | tests/integration/ 空置；import update 模式 0% 覆盖 | Tessa B10/B11/F37/F38 |
| M8 | 测试 | 覆盖率极不均（users 29%/terms 44%/i18n 0%/schemas/import 0%） | Tessa B12/F39 |
| M9 | 测试 | /products/stats 整套 skip（2 passed 实为 pass） | Tessa B13/F52 |
| M10 | 架构 | i18n 死模块（0 引用，json 不存在） | Archi B7/F45 |
| M11 | 架构 | 无 API 弃用/sunset 机制 | Archi B8 |
| M12 | 架构 | Refresh 7d 偏长；审计无保留策略 | Archi B9/F47/F46 |
| M13 | 架构 | 数据双加载契约（dictionary 走 bind-mount，规则走镜像内） | Archi B12/H5 |
| M14 | 文档 | PRD 7 处旧 data 路径（synonyms/consistency-rules） | Docu D3/H16 |
| M15 | 文档 | 配置矩阵缺失（6 compose + 3 .env 零说明）；P1-P2 报告过时称文档未实现 | Docu F43/F12 |

### 🟢 低（约 10 项，摘要）

Redis 宕机限流失效无测试（Cody 新#3）｜异常回文泄漏内部细节（Cody 新#4）｜CSRF 无 Origin 放行未文档化（新#5）｜refresh cookie path 过宽（新#6）｜裸 `except:`（new#7）｜根 .dockerignore 缺 .env.*（Archi 新#2）｜ADR-008 事实错误建议勘误（Archi 新#3）｜compose 注释与 depends_on 矛盾（Archi 新#6）｜prometheus.yml 挂载未 :ro（Rex 新#5）｜runbook 与 backup.sh 保留天数矛盾（Rex 新#6）｜api-reference 契约漂移残留 4 处（Docu F11）｜CHANGELOG 结构倒置+损坏文本（Docu D4/H17）｜api-reference 缺 /users/me（Docu N2/F40）｜monitoring-guide 残留 2024 日志（Docu N4/F55）｜README 死章节（Docu F68）｜user-manual 无截图（Docu F67）｜ADR-008~013 存在但未实施（Archi）。

---

## 四、本轮新发现高优先项（独立强调）

| # | 严重度 | 问题 | 建议修复 | 来源 |
|---|--------|------|---------|------|
| 新-1 | 🔴 | 根 .env 真实密钥被 compose 注入 prod（P0-2 同源） | 移除根 .env 真实值 / prod 显式 `:?` + 不自动读根 .env | Rex+Archi |
| 新-2 | 🔴 | alertmanager 邮件链路死配置（P0-3） | prod alertmanager 加 environment 段 + 用含 envsubst 的基底镜像 | Rex |
| 新-3 | 🔴 | test_terms.py 静默 0 测试（P0-8） | 修正缩进 + fixture；CI 加 `--co -q` 收集数断言 | Tessa |
| 新-4 | 🔴 | 覆盖率虚高跌破门槛（P0-9） | pyproject 去除粉饰排除项；CI 门槛对齐真实值或补测试 | Tessa |
| 新-5 | 🔴 | refresh cookie 只写不读（P0-5） | security.py 加读 refresh_token cookie 逻辑 + 缩短 TTL | Cody |
| 新-6 | 🟠 | login 无 commit → 审计丢失（H1） | auth.py 登录成功路径加 db.commit() | Cody |
| 新-7 | 🟠 | import_.py logger 未定义 NameError（H3） | 模块顶部 `logger = logging.getLogger(__name__)` | Cody |
| 新-8 | 🟠 | BOM 污染 + 门禁盲区（H2） | 脚本去 BOM；ci-content-gates 加 BOM 检测；门禁接入 CI | Rex |
| 新-9 | 🟠 | 导出审计早写错序（H6） | write_audit_log 移到 404 之后、流式生成之后 | Archi |

---

## 五、修复优先级排序（Priority = (Impact + Risk) × (6 - Effort)）

| 排名 | 修复项 | I | R | E | Priority | 紧急度 |
|------|--------|---|---|---|----------|--------|
| 1 | P0-2/P0-1 根 .env 密钥治理 + nginx 证书 | 5 | 5 | 2 | **40** | P0 |
| 2 | P0-5 refresh cookie 读取 + 缩短 TTL | 4 | 5 | 2 | **35** | P0 |
| 3 | P0-3 alertmanager 告警链路 | 4 | 5 | 2 | **35** | P0 |
| 4 | P0-6 /register 限流 + P0-7 强制改密拦截 | 4 | 4 | 2 | **32** | P0 |
| 5 | P0-4 备份调度（cron/ofelia） | 4 | 4 | 2 | **32** | P0 |
| 6 | P0-8 修正 terms 测试收集 | 4 | 4 | 1 | **36** | P0 |
| 7 | P0-9 覆盖率诚实化 | 3 | 4 | 1 | **30** | P0 |
| 8 | H1 login commit 审计 | 3 | 3 | 1 | **25** | P1 |
| 9 | H3 import logger NameError | 3 | 4 | 1 | **28** | P1 |
| 10 | H5/H6 导出双扫 + 审计错序 | 4 | 4 | 3 | **20** | P1 |
| 11 | H9 限流 fail-closed + 加锁 | 4 | 4 | 2 | **32** | P1 |
| 12 | H10 async 阻塞改线程池 | 3 | 3 | 2 | **24** | P1 |
| 13 | H4 生产密钥 fail-fast | 4 | 4 | 1 | **28** | P1 |
| 14 | H2 BOM 清理 + 门禁入 CI | 3 | 4 | 2 | **24** | P1 |
| 15 | M4 users.py 写路径补测 | 4 | 3 | 4 | **12** | P2 |

---

## 六、分阶段修复计划（下一轮）

### Sprint-Hotfix（≤2 天）— 恢复可部署 + 堵安全边界
1. **P0-1** certbot/预置证书放 `deploy/nginx/ssl/` + 部署前校验存在
2. **P0-2** 根 .env 真实密钥剥离；prod 改 `${SECRET_KEY:?}` 且 compose 禁止自动读根 .env；**轮换已暴露密钥**
3. **P0-3** prod alertmanager 加 SMTP environment + 换含 envsubst 基底镜像
4. **P0-5** security.py 加读 refresh_token cookie + TTL 缩短
5. **P0-6/7** /register 独立限流 + get_current_user 拦截 force_password_change
6. **P0-4** 备份调度（ofelia/systemd timer）
7. **P0-8/9** 修 test_terms.py 缩进 + pyproject 去粉饰排除项

### Sprint-A（第 1-2 周）— 安全加固 + 测试可信度
8. **H1/H3/H9/H10/H4** 登录 commit、import logger、限流 fail-closed+锁、async 线程池、生产密钥 fail-fast
9. **M1-M9** 合并 pytest 配置、Playwright 入 CI、conftest 严格 DB、users.py 补测、限流真 429、黑名单 fixture、import update 测试
10. **H2/H5/H6/H7/H8** BOM 清理+门禁入 CI、导出去双扫+审计错序、中间件收敛、import 审计、i18n 清理或接入
11. **H11-H32 文档面** .env.example 默认值、QUICKSTART/DEPLOY 围栏、PRD 旧路径、配置矩阵、P1-P2 报告、api-reference 缺 /users/me

### Sprint-B（第 3-5 周）— 结构性还债
12. **H12/H13/H14/H15/H16/H17/H18** exporter 补齐、指标聚合、synthetic 探测、单点评估、密钥全量显式化、依赖锁版本（passlib→bcrypt/argon2、python-jose→PyJWT、psycopg2-binary→psycopg）
13. **M10-M15** i18n 接入/删除、API 弃用机制、审计保留、数据单源、terms 覆盖补强
14. **低优长尾** 根残留文件清理、单迁移 `alembic check`、ADR-008 勘误、README 死章节

---

## ✅ 行动清单（按优先级排序）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 1 | **nginx TLS 证书就位** — 放 `deploy/nginx/ssl/` 并部署前校验 | DevOps | P0 | Hotfix |
| 2 | **根 .env 真实密钥治理** — 剥离真实值、prod `:?`、禁自动读根 .env、轮换已暴露密钥 | 后端+Ops | P0 | Hotfix |
| 3 | **alertmanager 告警链路修复** — SMTP environment + 含 envsubst 镜像 | 后端+Ops | P0 | Hotfix |
| 4 | **refresh token 改读 cookie** — 删 JSON body 返回、缩短 TTL | 全栈 | P0 | Hotfix |
| 5 | **/register 限流 + 强制改密服务端拦截** | 后端 | P0 | Hotfix |
| 6 | **备份调度落地**（ofelia/systemd timer） | Ops | P0 | Hotfix |
| 7 | **修正 test_terms.py 收集 + 覆盖率诚实化** | 测试 | P0 | Hotfix |
| 8 | **login 补 db.commit + import logger 定义** | 后端 | P1 | Sprint-A |
| 9 | **限流 fail-closed + 加锁；async 阻塞改线程池** | 后端 | P1 | Sprint-A |
| 10 | **导出去双扫 + 审计错序修复** | 后端 | P1 | Sprint-A |
| 11 | **BOM 清理 + ci-content-gates 接入 CI（含 BOM 检测）** | Ops | P1 | Sprint-A |
| 12 | **合并 pytest 配置 + Playwright 入 CI + users.py 补测** | 测试 | P2 | Sprint-B |
| 13 | **依赖锁版本 + psycopg2-binary→psycopg** | 后端 | P2 | Sprint-B |
| 14 | **prod exporter 补齐 + 指标多 worker 聚合** | Ops | P2 | Sprint-B |
| 15 | **文档止损（.env.example/QUICKSTART/PRD 旧路径/配置矩阵）** | 文档 | P1 | Sprint-A |

---

## ⚠️ 待完善 / 已知局限

- **本报告基于五成员实读代码 + 实跑 `docker compose config -q` / `pytest`**，非历史会话记忆；已纠正"R1–R4 全落地"的错误结论。
- **仓库无 git**，修复归属基于文件 mtime + 实测行为推断；部分"已修复"项（如 R4 refresh/限流）经双成员独立确认**未落地**，建议以本报告为准。
- **前端构建未深度审查**：Playwright/vitest 未入 CI，前端质量未量化。
- **性能/负载未跑基准**：同步 I/O、多 worker 指标分片的具体退化未量化。
- **BOM 影响面**：仅抽样确认 backup.sh 与部分 YAML 带 BOM，建议全仓扫一次。
- 严重度分布为去重合并后的估算（约 72 项），精确计数以各成员原始产出为准（见索引）。

---

## 📚 数据来源 & 成员产出索引

- **Cody（代码审查师）**：38 项代码开放项实测 + 7 新发现。RESOLVED 3（C-1、C-5*、F17）/ PARTIAL 4（C-2、N1/H3/F13、H18）/ OPEN 31。关键新发现：NEW-1 import logger NameError（🔴）、NEW-2 login 无 commit 审计丢失（🔴）、R4 refresh-cookie 读取未落地。
- **Archi（架构师）**：26 项架构项实测 + 7 新发现。RESOLVED 5（A-N1、A-N2、A-N3、B2/F17、B11）/ PARTIAL 1（B12）/ OPEN 12。关键：B3 双扫、B4 三层中间件、B5 import 无审计、ADR-008~013 存在但未实施、生产密钥分裂（🔴）、导出审计错序（🔴）。
- **Rex（SRE 工程师）**：运维全清单实测 + `docker compose config -q` 实跑 + 6 新发现。RESOLVED 10（R1/NEW-1、R2/NEW-2、R3/N23、N1/F1、N3/F3、N14、N16、N24、N26、H1）/ PARTIAL 8 / OPEN 10。关键新发现：BOM 污染（🔴）、alertmanager 邮件死配置（🔴）、ci-content-gates 未入 CI。
- **Tessa（测试专家）**：150 collected / 148 passed / 2 skip / 73%（名义）实跑 + 10 新发现。RESOLVED 2（R9、B15）/ PARTIAL 2（B3、B14）/ OPEN 13。关键新发现：test_terms.py 0 收集（🔴）、真实覆盖率 69%<70%（🔴）、conftest 无 StaticPool（纠正 R4 声称）。
- **Docu（技术文档师）**：18 项文档项实测 + 10 新发现。RESOLVED 5（R13、R14/N1、N3、F41、F56）/ PARTIAL 9 / OPEN 4。关键新发现：.env.example 默认 DATABASE_URL 破坏一键启动（🟠）、QUICKSTART 误导 frontend/grafana。

---

> 本报告由工程保障团队 AI 协作生成，关键决策请由人类工程负责人复核。
> 参与成员：Cody（代码审查师）· Archi（架构师）· Rex（SRE 工程师）· Tessa（测试专家）· Docu（技术文档师）
> 编排整合：甄宇航 · 工程督导
