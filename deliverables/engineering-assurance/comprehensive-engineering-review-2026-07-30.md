# 跨境产品资料中英对照系统 — 全面工程审查报告（合并视图）

**日期**：2026-07-30
**工作流**：工作流 1（全面代码审查）+ 工作流 5（技术债评估）综合
**参与成员**：Cody（代码审查师）、Archi（系统架构师）、Rex（SRE 工程师）、Tessa（测试专家）、Docu（技术文档师）
**说明**：本报告为 **2026-07-30 当天两次独立全面审查的交叉合并视图**。第一次（02:35，`full-engineering-review-2026-07-30.md`）由同一团队产出 9 项 CRITICAL；本次（03:45）由 5 位成员并行独立审查产出 5 项关键缺陷。两份合并去重后共 **12 项关键（🔴）缺陷**。下方每条均标注来源报告/成员。

---

## 📌 TL;DR（执行摘要）

- **整体结论**：🔴 **不通过**。系统不仅架构基础扎实（分层清晰、Postgres+连接池、RBAC 完整），且存在 **12 项发布阻塞级关键缺陷**，其中最致命的是「系统实际无法登录」与「密码重置会锁死用户」两项功能性阻断，外加「批量导入静默丢数据」「导出一致性引擎是死代码」「Alembic 零迁移」等正确性/架构致命项，以及运维侧「监控采不到指标 + 告警投不出去 + 生产端口暴露」结构性失效。
- **严重度分布（合并去重）**：🔴 严重 12 项 / 🟠 高 ~25 项 / 🟡 中 ~30 项 / 🟢 低 ~6 项。
- **历史 5 大关键项修复状态**：生产 SQLite→✅ 已修复；Token 存储→🔴 **回归/更糟**（早前审查发现普通登录不写 Cookie→无法登录）；默认凭证硬编码→🟡 部分修复（admin 随机化，但 SECRET_KEY 仍遗留工作树/compose 默认）；Prometheus 告警→🔴 **规则已写但全部不生效**；API 文档→🔴 **反转**：现文档虚构 11 端点（已删 7，残留 4）。
- **阻塞 / 非阻塞**：12 项关键缺陷全部为发布阻塞（No-Go）。

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🔴 不通过（12 项发布阻塞级关键缺陷） |
| 阻塞项数量 | 12 |
| 关键行动项 | 12 条 P0（见行动清单） |
| 建议下一步 | 立即进入 **P0 止血 Sprint**：先修「无法登录 / 密码重置锁死 / 导入丢数据 / 导出一致性死代码 / Alembic 空壳」，再修「TLS+暴露面收敛 / 可观测性闭环 / 文档事实源」 |

---

## 🔴 关键缺陷（合并 12 项 — 全部发布阻塞）

| # | 严重度 | 维度 | 文件:行 | 问题描述 | 建议修复 | 来源 |
|---|--------|------|---------|----------|----------|------|
| K1 | 🔴严重 | 认证/功能性 | `backend/app/api/auth.py:95-102`；`frontend/src/app/login/page.tsx:19`；`frontend/src/lib/api.ts:6,8-18` | **系统实际无法登录**：普通登录把 token 放回 JSON body 但不写 httpOnly Cookie，前端登录后既不 `setToken` 也不依赖 Cookie，后续请求无凭证→401→守卫跳回 /login 死循环 | 普通登录分支也必须 `set_auth_cookies(...)`；前端登录成功 `setToken` 或统一改 `/auth/me` 探活；移除 `getToken()` 守卫依赖 | 早前审查 F-01 |
| K2 | 🔴严重 | 正确性/功能性 | `backend/app/api/users.py:344-405`（`reset_user_password` 无 `return`）；`:519-524` 死代码 | **密码重置锁死用户**：函数体无 `return`（FastAPI 返回 null），用户被置 `force_password_change=True` 但拿不到临时密码，永久锁死 | 函数末尾 `return {"temporary_password": ...}`；删除 519-524 死代码 | 早前审查 F-02 |
| K3 | 🔴严重 | 架构/迁移 | `backend/alembic/versions`（空）；`backend/app/main.py:24`；`init_db.py:32`；`docker-entrypoint.sh` | **Alembic 零迁移**：已配置但 0 个迁移版本，表结构仍由 `create_all` 全权负责；`--skip-create-tables` 是死参数（`init_db.py` 无参数解析）。ADR-006 机制层未落地 | 生成初始 Alembic 迁移；启动改 `alembic upgrade head` 并移除 `create_all`；实现 `--skip-create-tables` 语义 | 早前审查 F-03 |
| K4 | 🔴严重 | 核心功能 | `backend/app/api/export.py`（未调用引擎）；`core/consistency.py:10` | **导出一致性引擎是死代码**：`ConsistencyEngine` 不被调用，export 直接导出，产品 `consistency_status/issues` 从未计算（历史 CRITICAL 回归） | export 入口调用 `ConsistencyEngine` 跑 L1-L3，ERROR 级阻断并返回问题清单；写入/定时也更新状态 | 早前审查 F-10 + 本次 Archi D2 |
| K5 | 🔴严重 | 正确性/数据丢失 | `backend/app/api/import_.py:405,507` | **批量导入静默截断到前 100 行**（`rows[:100]` 缓存），>100 行文件其余数据静默丢弃，响应不提示丢失 | 缓存全部行或 `execute_import` 重新解析 `file_path`；预览基于全量做校验 | 本次 Cody F-01（早前未覆盖） |
| K6 | 🔴严重 | 架构/核心功能 | `backend/app/core/consistency.py:19,27` | **一致性引擎 L2/L3 在生产镜像中静默失效**：规则文件在仓库根 `data/` 而代码读 `backend/data/`（镜像构建上下文为 backend，该目录不存在），`FileNotFoundError` 被吞 → 同义词/拼写规则为空，仅 L1（DB）生效 | 规则文件移入 `app/data/` 或修正路径；补"引擎真实加载规则"的集成测试 | 本次 Archi D1 |
| K7 | 🔴严重 | 架构/生产可用性 | `docker-compose.prod.yml` + `backend/app/config.py` + `deploy/nginx/nginx.conf:2` | **生产无 TLS + COOKIE_SECURE 冲突**：prod 编排/nginx 无 TLS 终止（仅 listen 80），后端未强制安全头，但 `ENVIRONMENT=production` 时强制安全 Cookie → 无外部 HTTPS 则登录后鉴权 Cookie 不随请求发送，循环失败 | prod 增 nginx/Traefik 做 TLS 终止+安全头，或文档固化外部 LB；FastAPI 加安全头中间件兜底 | 本次 Archi D3 / 早前 F-22 |
| K8 | 🔴严重 | 运维/可观测性 | `monitoring/alertmanager.yml`；`docker-compose.prod.yml:128-150` | **告警永远投不出去**：Alertmanager 在 prod 未部署（仅 prometheus/grafana），且 webhook 指向不存在的 `alertmanager-webhook` 服务；SMTP 变量声明却无 email receiver | prod compose 加 alertmanager 服务并挂载 `alertmanager.yml`；receiver 指向真实可达地址（邮件/Slack/已部署 Webhook） | 本次 Rex R1 / 早前 F-07 |
| K9 | 🔴严重 | 运维/可观测性 | `monitoring/prometheus.yml:20`；`backend/app/main.py:166-174`；`deploy/monitoring` 独立网络 | **监控采不到指标**：Prometheus 抓 `/metrics`（JSON+admin 鉴权）而非 `/metrics/prometheus`，且无凭据→401/解析失败，`up{job="backend"}` 恒为 0；独立监控栈与业务栈网络隔离也导致 scrape 不可达 | 新建无鉴权 `/metrics` 暴露 Prometheus 文本；或 Prometheus 加 bearer；`metrics_path` 改 `/metrics/prometheus`；Prometheus 与 backend 同网络 | 本次 Rex R2 / 早前 F-06 |
| K10 | 🔴严重 | 暴露面/认证 | `docker-compose.prod.yml:89,109,132,142,144` | **生产端口全暴露 + 弱口令**：postgres/redis/prometheus/grafana 全部映射宿主机；Prometheus 9090 无认证；Grafana `${GRAFANA_PASSWORD:-admin}` 默认口令 | 数据库/缓存仅内网互通（不映射宿主机）；监控面加反代+认证；移除 `:-admin` 回退强制 `GRAFANA_PASSWORD` | 早前审查 F-08 |
| K11 | 🔴严重 | 文档/契约 | `docs/api-reference.md`（11 虚构端点）；本次核查残留 4 个 | **API 文档虚构 11 个不存在端点**（products restore/batch-delete/check-consistency/stats、terms GET/PUT/DELETE/{id}/categories/suggest、export/preview、audit-logs/{log_id}），消费方调用必 404；v1.1.0 声称删 11 实删 7，残留 4 且 CHANGELOG 误称已全删 | 以 OpenAPI/FastAPI 自动生成或实测路由为唯一事实源重写；删除未实现端点；修正 CHANGELOG | 早前 F-04 / 本次 Docu |
| K12 | 🔴严重 | 运维/数据 | `scripts/backup.py`(全文)；`scripts/backup.sh` | **备份无加密/远程/调度**：`backup.sh` 硬编码 SQLite 路径→不备份生产 PG 库；无 cron/systemd/CI 触发；`backup.py` 未串联恢复校验 | `pg_dump`+加密(age/GPG)+远端(S3)+定时；统一 `backup.py` 为唯一入口并校验恢复 | 早前 F-21 / 本次 Rex R5 |

---

## 🟠 高（High，~25 项摘要）

> 以下为合并后代表性 HIGH 项；完整逐条（含文件:行）见两份源报告。

- **安全/泄露**：异常处理器把完整请求头（含 `Authorization`/`Cookie`）写入日志 → JWT 可被日志盗用（本次 Cody F-02）；access token 24h 不可撤销（本次 Cody F-03）；`_cache_delete` 无限递归致导入后 500（本次 Cody F-04）；工作树 `.env` 含真实 SECRET_KEY + compose 默认弱密钥（本次 Cody F-05 / 早前 F-34）；`/register` 完全开放可枚举（本次 Cody F-06）；重置密码明文回显响应（本次 Cody F-07）；限流 fail-open+每进程内存（本次 Cody F-12）；无 CSRF 仅靠 SameSite（本次 Cody F-10）；缺安全响应头（本次 Cody F-11）。
- **正确性/性能**：导出 N+1 + 全表加载（本次 Cody F-08）；搜索前导通配 `LIKE` 全表扫描（本次 Cody F-09）；导入 upload 用进程内字典缓存，4 worker 下 preview/execute 路由到不同 worker→404（早前 F-11）；导入逐行查库 N+1（早前 F-36）；CSV 转义不全（currency/stock/weight 未转义）（早前 F-31）。
- **架构/部署**：写入不触发一致性检测（本次 Archi D2）；JSON 字段用 `sqlite.JSON` 方言类型迁 PG 不映射 jsonb（早前 F-14）；配置-代码耦合（SECRET_KEY 生成临时 key fallback、WORKERS 硬编码）（本次 Archi D4）；V2 数据模型缺口（本次 Archi D5）；审计覆盖不全+两套实现并存（早前 F-13）；导入缓存进程内字典多 worker 失效（本次 Cody/Archi）。
- **运维**：prod Prometheus 未挂载 `alerts.yml` → 规则加载失败（本次 Rex R3）；ApplicationRestart 告警逻辑错误常驻误报（本次 Rex R4）；nginx 反代被 PowerShell 插值破坏，`nginx -t` 不通过（本次 Rex R12）；指标为进程内计数器多副本不聚合（本次 Rex R10 / 早前 F-19）；告警规则引用不存在指标 `probe_success`/node-exporter 未部署（早前 F-20）；监控镜像 `:latest` 未固定（本次 Rex R13 / 早前 F-23）；`stop_grace_period` 默认 10s 短于排空 30s（早前 F-23）。
- **测试/CI**：`ci-cd.yml` YAML 缩进错误致流水线失败（本次 Tessa D2）；双 CI 工作流冲突、覆盖率门禁失效（本次 Tessa D1/D3）；覆盖率实测仅 45.75%/分支 0%（本次 Tessa）；Playwright E2E 从未在 CI 运行、前端单测近零（本次 Tessa D4/D5）；核心逻辑单测缺失（consistency/csv_utils/import 均 <20%）（本次 Tessa D8）；用户/权限矩阵+token 负路径缺失（本次 Tessa D9）；`/products/stats` 测试用 skip 掩盖零覆盖（早前 F-09）；令牌吊销/禁用用户路径无测试（早前 F-26/F-27）；126 用例中 23 个未打 marker 被静默排除（早前 F-25）。
- **文档**：README 导出/导入 4 条路径全错（本次 Docu D2）；已实现 users 端点误标"未实现"（本次 Docu D3 / 早前 F-30）；缺认证/RBAC 权限矩阵文档（本次 Docu D4）；incident-response runbook 假设 PostgreSQL 与默认 SQLite 冲突（本次 Docu D5 / 早前 F-17）；多 `.env` 互相冲突且加载机制未文档化（早前 F-15）；限流说明与实现不符（本次 Docu D6）；备份文档 DB 名/账号不一致（本次 Docu D8 / 早前 F-48/F-49）；ADR-006 编号错乱（本次 Docu D7 / 早前 F-51）。

## 🟡 中（Medium，~30 项摘要）

- 安全：CSV 注入防护覆盖不全（早前 F-31）、登录限流进程内字典多 worker 失效（早前 F-33）、生产 .env 可猜测占位密钥（早前 F-34）、`.env.production` REDIS_URL 不展开致黑名单 fail-open（早前 F-35）、CORS 容错退化为逗号拆分有误配 `*` 风险（早前 F-65）。
- 架构：清理过期黑名单条目从未调用（早前 F-39）、`extra_fields` 无 Schema 校验（早前 F-40）、导出模板字段硬编码（早前 F-41）、后端无 i18n 抽象（早前 F-42）、`validate_secret_key` 导入期向 .env 写文件可能重置密钥（早前 F-43）、单 PG 无副本（本次 Archi D8）、API/PRD 契约偏差（本次 Archi D9）。
- 运维：staging 仍 SQLite+弱密钥+DEBUG（早前 F-44）、指标手动拼接无 histogram 无法算 P95（早前 F-45）、CI/CD 发布仅 echo 占位（早前 F-46）、健康检查 dev 仍 `python -c`（早前 F-63）、密钥校验失败写回 .env（早前 F-64）。
- 测试：CI 用本地 sqlite 而非 postgres、redis 未测（早前 F-58）、测试金字塔倒挂（早前 F-59）、游离调试脚本污染（早前 F-60）、未开分支覆盖（本次 Tessa D7）、无 API 契约测试（本次 Tessa D10）、Alembic 无测试（本次 Tessa D12）、`utils/i18n.py` 无测试（本次 Tessa D14）、源文件编码疑似 GBK/UTF-8 混用（本次 Tessa D15）。
- 文档：示例日期 2024（早前 F-52）、user-manual 无截图（早前 F-53）、CHANGELOG 未记录 07-29 用户管理变更（早前 F-55）、README 重复部署小节（早前 F-57）、无文档漂移防护（本次 Docu D9）。

## 🟢 低（Low，~6 项摘要）

- 两套审计实现/提交语义不一致（早前 F-61）；魔法数字/重复配置（早前 F-62）；pytest 配置重复（pytest.ini + pyproject.toml）（本次 Tessa D66）；仓库根遗留 `_patch_auth.py` 补丁碎片（本次 Cody F-19）；限流仅覆盖 `/auth/login`（本次 Cody F-20）；`/metrics/prometheus` 无鉴权（可接受）（本次 Cody F-21）。

---

## 🏗️ 架构影响评估（Archi）

- **整体健康度**：🟡 黄。分层清晰、RBAC 完整、Postgres+连接池已落地、Redis 承担分布式状态。但 **迁移机制名存实亡**（K3/F-03：Alembic 0 迁移、JSON 用 SQLite 方言、FK/约束残缺）使 ADR-006 生产化路径结构性不成立。
- **核心功能风险**：一致性引擎在「生产路径错误」（本次 K6/D1）与「export 完全不调用」（早前 K4/F-10）两个层面同时失效，产品核心价值受损。
- **ADR 落地**：ADR-004/005/007 已落地；ADR-002/003 未真正落地（两套审计、ConsistencyEngine 死代码）；ADR-006 部分落地且有关键缺口。建议新增 ADR-008（迁移单一真相源）、ADR-009（审计标准化）、ADR-010（配置/密钥与分布式限流）。

## 🧪 测试覆盖评估（Tessa）

- **实测覆盖率**：语句 **45.75%**、分支 **0%**（来自 `backend/coverage.xml`，基线可能不完整）。早前审查基于 126 用例（125 passed/1 skipped）估 ~40% 行覆盖。
- **最大缺口**：CI 无覆盖率门禁、安全错误路径（令牌吊销/禁用用户/500）基本未测或空壳、`/products/stats` 假覆盖（skip 掩盖）。低覆盖模块：`core/redis.py` 0%、`schemas/import_.py` 0%、`core/consistency.py` 15.9%、`api/import_.py` 18.6%、`api/users.py` 15.9%。
- **CI 状态**：lint/type/bandit/safety/gitleaks 配置层都有，但 `ci-cd.yml` YAML 缩进错误致流水线可能失败；双工作流冲突；前端/E2E 实际未被任何门禁覆盖。
- **策略**：先修 CI 与门禁 → 核心逻辑单测 → 权限矩阵+token 负路径 → Postgres 通道+分支覆盖 → 真实 E2E。分阶段：1 月 ≥65% 语句/≥50% 分支，3 月 ≥80%/≥70%。

## 📚 文档完整性评估（Docu）

- **历史"缺 11 端点"复核**：实为"文档虚构 11 个后端不存在端点"；v1.1.0 声称删 11，实测仅删 7，**4 个仍残留**（terms/{id}×3、audit/{log_id}）且 CHANGELOG 误称已全删（K11）。
- **真实缺口**：4 幻影 + 2 未覆盖（GET /、users/me）+ 3 误标（users delete/reset-password/bulk 已实现却标未实现）+ README 4 条导出/导入路径错误。
- **缺失文档**：认证/RBAC 权限矩阵（D4）；无 OpenAPI→doc 同步或 CI 路径比对门禁（D9，漂移已发生 2 次）。ADR 体系、Runbook 5 篇、CONTRIBUTING、部署文档齐全——问题集中在"准确性/与代码一致"。

## ⚙️ 运维就绪度评估（Rex）

- **可观测性链路结构性失效**：K9（抓取路径+鉴权双错，指标采不到）+ K8（Alertmanager 未部署）+ 早前 F-20（规则引用不存在指标）→ 告警"规则已写、实际不触发或误触发、且触发后投不出去"。
- **暴露面与传输安全**：K10（端口全暴露+Grafana 弱口令）+ K7（无 TLS）在生产是重大攻击面。
- **备份（K12）**：脚本能力充分但无加密/远程/调度，且 `backup.sh` 硬编码 SQLite 路径不备份生产 PG。
- **部署前检查清单**：已生成 Go/No-Go 维度（A 阻断 6 项 / B 重要 6 项 / C 观察 7 项），见源报告。

---

## 📊 技术债清单与优先级（工作流 5）

优先级公式：**Priority = (Impact + Risk) × (6 − Effort)**（分值越高越优先）

| 债务项 | 来源 | Impact | Risk | Effort | **Priority** |
|--------|------|:--:|:--:|:--:|:--:|
| 系统无法登录（K1） | 早前 F-01 | 5 | 5 | 2 | **40** |
| 密码重置锁死用户（K2） | 早前 F-02 | 5 | 5 | 1 | **45** |
| 导入静默丢数据（K5） | 本次 Cody | 5 | 5 | 2 | **40** |
| 一致性引擎生产失效（K6/D1） | 本次 Archi | 5 | 5 | 2 | **40** |
| 导出一致性死代码（K4） | 早前 F-10 | 5 | 5 | 2 | **40** |
| 生产无 TLS+安全 Cookie（K7） | 本次/早前 | 5 | 5 | 2 | **40** |
| 告警不可达/未部署（K8） | 本次/早前 | 5 | 5 | 2 | **40** |
| 监控采不到指标（K9） | 本次/早前 | 5 | 4 | 3 | **27** |
| 端口暴露+弱口令（K10） | 早前 F-08 | 5 | 5 | 2 | **40** |
| 文档虚构端点（K11） | 早前/本次 | 5 | 5 | 1 | **50** |
| 备份无闭环（K12） | 早前/本次 | 4 | 4 | 2 | **24** |
| Alembic 零迁移（K3） | 早前 F-03 | 5 | 4 | 3 | **30** |
| 异常日志泄露 JWT（F-02） | 本次 Cody | 4 | 5 | 1 | **45** |
| 工作树 SECRET_KEY（F-05） | 本次 Cody | 4 | 4 | 1 | **40** |
| 缓存递归致导入 500（F-04） | 本次 Cody | 4 | 4 | 1 | **40** |
| README 导出/导入路径错误（D2） | 本次 Docu | 4 | 4 | 1 | **40** |
| 覆盖率门禁失效+双 CI（D1/D2/D3） | 本次 Tessa | 5 | 5 | 2 | **40** |
| 硬编码密钥 compose（R7） | 本次 Rex | 4 | 3 | 1 | **35** |
| nginx 配置破坏（R12） | 本次 Rex | 4 | 3 | 1 | **35** |
| access token 24h 不可撤销（F-03） | 本次 Cody | 4 | 4 | 2 | **32** |

### 分阶段修复计划

- **Sprint A — P0 止血（建议 1 周内）**：K1 登录、K2 密码重置、K5 导入截断、K4/K6 一致性引擎、K3 Alembic、K7 TLS+安全头、K8/K9 可观测性闭环、K10 暴露面收敛、K11 文档事实源、K12 备份闭环。
- **Sprint B — P1 质量门禁与正确性（2–4 周）**：F-02 日志脱敏、F-04 缓存递归、F-03 token 吊销、F-05/F-34 密钥清理、CSRF/安全头、导出/审计覆盖补全、CI 合并+覆盖率门禁+Postgres 通道、核心逻辑单测+权限矩阵。
- **Sprint C — P2 质量提升（持续）**：性能（N+1/全表扫描/CSV 转义）、V2 模型（ADR-008/009/010）、文档漂移防护、前端/E2E 接入、备份自动化、staging 对齐 prod。

---

## ✅ 行动清单（按优先级排序，P0 阻塞项）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 1 | **修复登录会话断裂**：普通登录写 `set_auth_cookies` + 前端 `setToken`/改 `/auth/me` 探活，移除 `getToken()` 守卫依赖 | Cody + 前端 | P0 | 2 天内 |
| 2 | **修复密码重置死代码**：`reset_user_password` 补 `return` 临时密码，删 519-524 不可达代码 | Cody | P0 | 当天 |
| 3 | **修复批量导入静默截断**（import_.py:405/507），避免 >100 行数据丢失 | Cody | P0 | Sprint A |
| 4 | **导出/写入调用 ConsistencyEngine** 跑 L1-L3 并落库状态；修正规则路径（consistency.py:19/27 读 backend/data） | Cody/Archi | P0 | Sprint A |
| 5 | **打通 Alembic 迁移**：生成初始迁移、移除 `create_all`、实现 `--skip-create-tables`、JSON 改 `sqlalchemy.JSON`、补 FK | Archi/Cody | P0 | 3 天内 |
| 6 | **生产 TLS + 安全头**：nginx 443 + 证书、`COOKIE_SECURE=true`、强制 HTTPS 跳转 | Archi/Rex | P0 | Sprint A |
| 7 | **可观测性闭环**：新建无鉴权 `/metrics`、prod 部署 Alertmanager、修正 scrape 路径与告警规则（去 `probe_success`/补 node-exporter）、真实 receiver 验证触达 | Rex | P0 | 3 天内 |
| 8 | **收敛暴露面**：数据库/缓存不映射宿主机、Grafana 强口令去 `:-admin`、监控面加反代+认证 | Rex | P0 | Sprint A |
| 9 | **文档事实源对齐**：删 11 虚构端点（残留 4）+ 修正 3 误标 + 修正 README 导出/导入路径 + 同步 CHANGELOG | Docu | P0 | 3 天内 |
| 10 | **备份闭环**：`pg_dump`+加密+远端+定时；统一 `backup.py` 为唯一入口并校验恢复 | Rex | P0 | Sprint A |
| 11 | **异常日志脱敏 JWT**（exception_handler.py:36）+ 清理工作树 SECRET_KEY 并轮换 | Cody | P0 | Sprint A |
| 12 | **CI 合并+门禁**：修 `ci-cd.yml` YAML、合并双工作流、`--cov-fail-under=70`、gitleaks 扫描、测试连 Postgres/Redis | Tessa/Rex | P0 | Sprint A |

---

## ⚠️ 待完善 / 已知局限

- **两份审查结论存在差异**：本次 5 位成员并行独立审查未将「无法登录(K1)/密码重置锁死(K2)/Alembic 空壳(K3)/导出一致性死代码(K4)/端口暴露(K10)」列为最关键项，而 02:35 的 `full-engineering-review-2026-07-30.md` 已明确指出。两者均有效，合并后关键缺陷为 12 项；建议以**合并视图**为准并优先验证 K1/K2/K3/K4。
- **未做动态验证**：两轮均为静态代码/配置审查，未实际启动服务跑登录/导出/告警链路做端到端验证；K1/K2 功能性结论基于代码路径分析，修复后须补集成测试固化。
- **仓库非 git 状态**：无法用 git 历史确认 `.env` 是否入库、密钥是否泄露，仅能依据 `.gitignore` 推断。
- **前端覆盖极低**：前端仅 1 组件单测 + 1 e2e spec，本轮前端审查以代码路径为主。
- **覆盖率数字来源**：基于仓库内 `coverage.xml` 最近一次本地运行，CI 未设门禁故不阻断合并，且基线可能不完整（csv_utils 22 测试仅 16.67%）。

---

## 📚 数据来源 & 成员产出索引

- **本报告为两份同源审查的合并视图**：
  - 报告 A（02:35）：`deliverables/engineering-assurance/full-engineering-review-2026-07-30.md` —— 9 项 CRITICAL / 21 HIGH / 30 MED / 6 LOW，含 K1/K2/K3/K4/K7/K8/K9/K10/K11/K12 等。
  - 报告 B（03:45，本次 5 成员并行）：产出 K5/K6 两项新增关键缺陷及大量 HIGH/MED 项，并对 K7/K8/K9/K11/K12 提供补充证据。
- **Cody（代码审查师）**：本次后端+前端 token 审查 22 项（1🔴/8🟠/9🟡/4🟢）+ 早前 18 项含 K1/K2/K3/K4 等。
- **Archi（架构师）**：本次架构债 10 项（含 K6/D1、K7/D3、D2）+ 早前 12 项含 K3/K4。
- **Rex（SRE）**：本次运维核查 15 项风险（含 K8/R1、K9/R2、R3、R12、R5≈K12）+ 早前 16 项含 K8/K9/K10/K12。
- **Tessa（测试专家）**：本次测试债 15 项（含覆盖率 45.75%、CI YAML 错误、E2E 未跑）+ 早前 13 项。
- **Docu（文档师）**：本次文档债 10 项（含 K11 残留 4 幻影、README 路径错误）+ 早前 18 项含 K11。

---

> 本报告由工程保障团队 AI 协作生成，关键决策请由人类工程负责人复核。
> 两份源报告均保留在 `deliverables/engineering-assurance/` 下，建议结合阅读以获取逐条文件:行证据。
