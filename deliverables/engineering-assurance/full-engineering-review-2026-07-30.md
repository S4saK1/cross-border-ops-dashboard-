# 全面工程审查报告 — 跨境产品资料中英对照系统

**日期**：2026-07-30
**工作流**：工作流 1（全面代码审查）+ 工作流 5（技术债评估）合并执行
**参与成员**：Cody（代码审查师）/ Archi（系统架构师）/ Tessa（测试专家）/ Rex（SRE 工程师）/ Docu（技术文档师）
**审查范围**：后端 `backend/app/`（FastAPI+SQLAlchemy）、前端 `frontend/`、部署与监控（`docker-compose*.yml`/`monitoring/`/`deploy/`）、文档（`docs/`/`README`/`.env*`）、CI（`.github/workflows/`）

---

## 📌 TL;DR（执行摘要）

- **整体结论**：🔴 **不通过**。本轮发现 **9 项 CRITICAL、21 项 HIGH、30 项 MEDIUM、6 项 LOW**。最致命的是系统**当前实际无法登录**（Token 存储迁移断裂）、密码重置会**锁死用户**，且**可观测性链路结构性失效**（Prometheus 采不到指标、Alertmanager 没部署、告警投不出去）。
- **历史 77 项对照**：ADR 系列代码多已落地，但**多处是"空壳/回归"**——Alembic 零迁移、导出一致性阻断未实现、审计覆盖不全、CSV 转义不全、生产端口全暴露、无 TLS、备份断裂等历史高危**并未真正闭环**。
- **严重度分布**：🔴严重 9 项 / 🟠高 21 项 / 🟡中 30 项 / 🟢低 6 项
- **阻塞 / 非阻塞**：9 项 CRITICAL 全部为合并阻塞；HIGH 中除少数可 waiver 外，安全/可观测性相关须优先闭环。

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🔴 不通过 |
| 阻塞项数量 | 9（CRITICAL） |
| 关键行动项 | 10 条（P0×6 / P1×3 / P2×1，见行动清单） |
| 建议下一步 | 立即执行 **P0 止血 Sprint**：登录会话、密码重置死代码、Alembic 迁移、可观测性闭环、暴露面收敛+TLS、文档事实源对齐；随后 P1 补导出一致性/审计/CI 门禁/安全测试 |

---

## 🔍 审查发现总表（去重合并，按严重度排序）

> 合并说明：跨成员重复项已合并（如 Alembic 空壳、导出一致性、审计覆盖、FK 缺失、CSV 转义、COOKIE_SECURE、覆盖率门禁、redis 0% 等），统一编号 F-xxx。

### 🔴 CRITICAL（9 项，全部合并阻塞）

| # | 维度 | 文件:行 | 问题描述 | 建议修复 | 来源 |
|---|------|---------|---------|---------|------|
| F-01 | 安全/正确性 | `backend/app/api/auth.py:95-102`；`frontend/src/app/login/page.tsx:19`；`frontend/src/lib/api.ts:6,8-18` | **认证会话断裂**：普通登录把 token 放回 JSON body 但不写 httpOnly Cookie，前端登录后既不 `setToken` 也不依赖 Cookie，后续请求无凭证→401→前端守卫跳回 /login，形成死循环，**系统实际无法登录**。 | 普通登录分支也必须 `set_auth_cookies(...)`；前端登录成功调用 `setToken` 或统一改 Cookie 探活（`/auth/me`）；删除对 `getToken()` 的登录守卫依赖 | Cody |
| F-02 | 正确性 | `backend/app/api/users.py:344-405`（无 return）；`:519-524` 不可达死代码 | **密码重置锁死用户**：`reset_user_password` 函数体无 `return`（FastAPI 返回 null），用户被置 `force_password_change=True` 但拿不到临时密码，被永久锁死。 | 函数末尾 `return {"temporary_password": ...}`；删除 520-524 死代码；修复 bulk/reset 结构 | Cody |
| F-03 | 架构/迁移 | `backend/alembic/versions`（空）+ `backend/app/main.py:24` + `backend/init_db.py:32` + `docker-entrypoint.sh` | **迁移空壳**：Alembic 已配置但 0 个迁移版本，表结构仍由 `create_all` 全权负责；entrypoint 的 `--skip-create-tables` 是死参数（`init_db.py` 无参数解析，永远 `create_all`）。ADR-006 在"机制"层面未落地。 | 生成初始 Alembic 迁移；启动改 `alembic upgrade head` 并移除 `create_all`；实现 `--skip-create-tables` 语义 | Archi, Cody |
| F-04 | API 文档 | `docs/api-reference.md:458,489,519,560,677,709,745,769,798,990,1086` | **文档虚构 11 个不存在端点**（products 的 restore/batch-delete/check-consistency/stats 共 4、terms 的 GET/PUT/DELETE/{id}/categories/suggest 共 5、export/preview 1、audit-logs/{log_id} 1）。消费方按文档调用必 404。 | 以 OpenAPI/FastAPI 自动生成或实测路由为唯一事实源重写；删除未实现端点 | Docu |
| F-05 | 文档一致性 | `README.md:28,116,271` | **技术栈自相矛盾**：:28 称"数据库：PostgreSQL"，:116 称"SQLite 存储在 cms-data volume"，:271 写"如需迁移到PostgreSQL"。实际默认 `sqlite:///./bilingual_cms.db`。 | 统一表述：默认 SQLite、生产可切 PostgreSQL；去掉"技术栈=PostgreSQL"误导 | Docu |
| F-06 | 监控 | `monitoring/prometheus.yml:20`；`backend/app/main.py:166-168,171-174` | **Prometheus 采不到后端指标**：抓取 `metrics_path: '/metrics'` 但该端点返回 JSON 且 `require_admin` 鉴权；真正 Prometheus 格式在 `/metrics/prometheus`（同样要 admin 鉴权）。Prometheus 无凭据→401/解析失败→`up{job="backend"}` 恒为 0，错误率/延迟/重启全采不到。 | 新建无鉴权 `/metrics` 暴露 Prometheus 文本；或 Prometheus 加 bearer_token；`metrics_path` 改 `/metrics/prometheus` | Rex |
| F-07 | 告警 | `docker-compose.prod.yml:128-150`；`monitoring/alertmanager.yml:17`；`monitoring/prometheus.yml:14` | **Alertmanager 未部署**：prod compose 仅 prometheus/grafana，无 alertmanager 服务；`prometheus.yml` 指向 `alertmanager:9093`、webhook 指向 `alertmanager-webhook:5001` 均不存在→告警无法投递。 | prod compose 加 alertmanager 服务并挂载 `alertmanager.yml`；receiver 指向真实可达地址 | Rex |
| F-08 | 暴露面/认证 | `docker-compose.prod.yml:89,109,132,142,144` | **端口全暴露 + 弱凭据**：postgres(5432)/redis(6379)/prometheus(9090)/grafana(3001) 全部映射宿主机；Prometheus 9090 无认证；Grafana `${GRAFANA_PASSWORD:-admin}` 默认口令。 | 数据库/缓存仅内网互通（不映射宿主机端口）；监控面加反向代理+认证；移除 `:-admin` 回退强制 `GRAFANA_PASSWORD` | Rex |
| F-09 | 测试 | `backend/tests/test_products_stats.py:42`；`app/api/products.py`（无该路由） | **虚假覆盖信号**：`/products/stats` 测试在 endpoint 返回非 200 时 `pytest.skip("...not implemented")` 自跳过，且该端点根本不存在。掩盖了"端点零覆盖"。 | 明确端点是否实现；实现则断言 200+字段，放弃则删除测试与端点声明，勿用 skip 掩盖 | Tessa |

### 🟠 HIGH（21 项，关键项）

| # | 维度 | 文件:行 | 问题描述 | 建议修复 | 来源 |
|---|------|---------|---------|---------|------|
| F-10 | 安全/正确性 | `backend/app/api/export.py`（全文件未调用 consistency）；`core/consistency.py:10` | **导出一致性阻断未落地**（历史 CRITICAL 回归）：`ConsistencyEngine` 为死代码，export 直接导出，产品 `consistency_status/issues` 从未计算。 | 导出入口调用 `ConsistencyEngine` 跑 L1-L3，ERROR 级阻断并返回问题清单；定时/写入时更新状态 | Cody, Archi |
| F-11 | 正确性/部署 | `backend/app/api/import_.py:100-103`；`docker-entrypoint.sh:9`(`--workers 4`) | 导入 upload 用进程内字典缓存解析结果，4 worker 下 upload 落 A、preview/execute 被路由到 B→缓存未命中 404，导入大概率失败。 | 缓存改 Redis 或落盘按 `file_id` 重读；至少单 worker/粘性路由 | Cody |
| F-12 | 安全 | `docker-compose.prod.yml:42-56`；`config.py:20`；`security.py:175,184,193` | 生产未开 `COOKIE_SECURE`，httpOnly Cookie 可被 MITM 获取。 | prod compose 显式 `COOKIE_SECURE=true`；反向代理强制 HTTPS | Cody |
| F-13 | 安全/可审计 | `write_audit_log` 调用点（auth.py:225、users.py、products.py 内联）；export/import/auth 登录登出无审计 | **审计覆盖不全**（历史部分修复）：登录成功/失败、登出、导出、导入均无审计；且两套实现并存（`products._write_audit` 自 commit vs `core/audit.write_audit_log`）。 | 登录/登出/export/import.execute 补审计（actor/action/subject/ip）；统一为单一审计服务 | Cody, Archi |
| F-14 | 可移植性 | `backend/app/models/product.py:4`、`audit.py:4`、`term.py:4` | JSON 字段用 `sqlalchemy.dialects.sqlite.JSON`，迁 PG 时不映射原生 json/jsonb。 | 统一改用 `sqlalchemy.JSON`（方言自适应） | Archi |
| F-15 | 配置 | `.env` / `.env.example` / `.env.production`（DB 名、admin 邮箱、加载机制互不一致） | 三个 .env 互相冲突且加载机制未文档化。 | 统一 DB 名与 admin 邮箱；README/DEPLOY 显式说明各环境用哪个 .env 及 compose 自动加载 | Docu |
| F-16 | 部署一致性 | `docker-compose.yml:13,29-31`；`README.md:87-113`；`DEPLOY.md:16-49` | compose 依赖 postgres 但默认 DATABASE_URL 为 SQLite，文档未解释矛盾、未说明如何切 PG。 | 文档说明默认走 SQLite、postgres 可选；或移除强依赖 | Docu |
| F-17 | Runbook | `docs/runbooks/incident-response.md:422,434,263,150,193,425` | 引用不存在的 `/health/db`、`scripts/restore.py`；全程假定 PostgreSQL（与默认 SQLite 不符）；`log.user_email` 但模型仅 `user_id`。 | 修正端点/脚本引用；诊断示例改 SQLite 兼容；移除硬性 PG 假设 | Docu, Rex |
| F-18 | 文档 | `docs/monitoring-guide.md:15,141-144` | 架构图写 SQLite，但 Prometheus 配置引用 `postgres-exporter`，内部不一致。 | 统一数据库表述；仅保留实际暴露指标或标"规划中" | Docu |
| F-19 | 指标质量 | `backend/app/monitoring.py:13-20`；`docker-entrypoint.sh:9` | 指标为模块级单进程字典，`--workers 4` 下 Prometheus 仅 scrape 单端口→只命中 1 个 worker，计数约为真实 1/4 不可聚合。 | 改 prometheus_client 多进程模式或集中式指标；或按 worker 聚合 | Rex |
| F-20 | 告警规则 | `monitoring/alerts.yml:61`；`prometheus.yml:23-28` | `probe_success{job="backend"}` 是 blackbox 指标（backend 为普通 scrape，不存在）→DatabaseConnectionFailed 永不触发；node-exporter/cadvisor 未在 prod 部署→两 job `up` 恒 0。 | 改 `up{job="backend"}`；补部署 node-exporter/cadvisor 或移除对应 scrape | Rex |
| F-21 | 备份 | `scripts/backup.py`(全文)、`scripts/backup.sh:2,12` | 备份无加密/远程/调度；`backup.sh` 硬编码 SQLite 路径→不备份生产 PG 库；无 cron/systemd/CI 触发。 | `pg_dump`+加密(age/GPG)+远端(S3)+定时；统一 `backup.py` 为唯一入口并校验恢复 | Rex |
| F-22 | 传输安全 | `deploy/nginx/nginx.conf:2`；`config.py:20`；`docker-compose.prod.yml:10,38` | **无 TLS**：Nginx 仅 `listen 80`；`COOKIE_SECURE=False`；prod 无 TLS 服务，前后端端口直连。 | 反向代理启用 443+证书；`COOKIE_SECURE=True`；强制 HTTPS 跳转 | Rex |
| F-23 | 部署/回滚 | `docker-compose.prod.yml:129,139`（镜像 `:latest`）；无 `stop_grace_period`；`main.py:51` | 监控镜像 `:latest` 无法回滚；优雅停机排空 30s 但 Docker 默认 `stop_grace_period` 10s→在途请求被截断。 | 监控镜像固定版本；compose 加 `stop_grace_period: 40s` 与 lifespan 对齐 | Rex |
| F-24 | CI 门禁 | `.github/workflows/ci.yml:58-59,73`；`ci-cd.yml:56` | **无覆盖率门禁**（`flake8` 第二阶段 `exit-zero`、coverage 无 `--cov-fail-under`）；**无密钥扫描(gitleaks)**。 | 加 `pytest --cov-fail-under=70` 与 gitleaks/trufflehog 作为必过门禁 | Tessa, Rex |
| F-25 | 测试 | `backend/tests/test_audit.py:6`、`test_auth_missing.py:5`、`test_exception_handler.py:8` | 126 用例中 23 个（18.3%）未打 marker，`run_tests.py --type`/`pytest -m` 会静默排除（含审计/异常/缺失端点等关键测试）。 | 为这 3 文件补 `@pytest.mark.integration/.security`；或收集脚本默认含 unmarked | Tessa |
| F-26 | 安全测试 | `core/security.py:50`、`core/redis.py` | 令牌吊销**请求级拒绝路径无集成测试**；Redis 版 `TokenBlacklist` 覆盖率 0%。 | 增加 `blacklisted_token`/`expired_token` fixture，测 logout-all 后旧 token 被拒、吊销用户被拒 | Tessa |
| F-27 | 安全测试 | `core/security.py:237`、`api/auth.py:76/118` | 强制 `is_active` 校验（禁用用户拒绝），但**无任何测试**覆盖"禁用用户被拒"路径。 | 增加 `disabled_user` fixture 与"禁用用户登录 401/访问 403"用例 | Tessa |
| F-28 | 测试 | `test_exception_handler.py:42-53` | `test_500_internal_error_is_caught` 空壳（`with patch: pass` 后仅断言正常 200/401），全局异常处理器"吞栈不泄露"核心行为从未验证。 | 用 monkeypatch 注入真实异常，断言返回 500 标准格式且响应体无 traceback | Tessa |
| F-29 | 测试 | `tests/conftest.py:81-141`、`api/export.py:24` | 应用有 `Role.REVIEWER` 且 `/export` 用 `require_reviewer`，但 conftest 缺 reviewer fixture；reviewer/editor 权限边界从未验证。 | 增加 `reviewer_user`/`reviewer_token` fixture，补 reviewer 可导出、editor 不可导出用例 | Tessa |
| F-30 | 文档 | `docs/api-reference.md:1273-1298,1301-1323,1325-1340,1509-1512` | 已实现用户端点（DELETE /users/{id}、reset-password、bulk）被误标"未实现/规划中"，底部又称 bulk 已实现，自相矛盾。 | 改为"已实现"并核对 reset-password 真实响应体（见 F-02 死代码） | Docu |

### 🟡 MEDIUM（30 项，摘要）

| # | 维度 | 关键问题 | 文件:行 | 来源 |
|---|------|----------|---------|------|
| F-31 | 安全 | CSV 注入防护覆盖不全（currency/stock/weight/weight_unit 未转义，sanitize 仅首字符） | `export.py:53-88`、`csv_utils.py:21` | Cody |
| F-32 | 性能 | 导出非真流式（全量入内存），`product_ids` 无上限 | `export.py:39-100` | Cody |
| F-33 | 安全/部署 | 登录限流进程内字典，多 worker 失效 | `main.py:31,85-109` + `entrypoint --workers 4` | Cody, Archi |
| F-34 | 安全/部署 | 生产 .env 模板含可猜测占位密钥 | `.env.production:7,14,37,41` | Cody |
| F-35 | 正确性/部署 | `.env.production` 的 `REDIS_URL=${REDIS_PASSWORD}` 脱离 compose 不展开→Redis 异常、黑名单 fail-open | `.env.production:38` + config | Cody |
| F-36 | 性能 | 导入逐行查库 N+1（大文件上万次 SELECT） | `import_.py:455-507` | Cody |
| F-37 | 可审计 | 批量导入无审计汇总 | `import_.py:433-527` | Cody |
| F-38 | 数据完整性 | 审计表/黑名单表 `user_id` 无 FK（Product.created_by 已有 FK） | `audit.py:12`、`token_blacklist.py:17` | Cody, Archi |
| F-39 | 数据增长 | `cleanup_expired_blacklist_entries` 定义后从未调用，DB 兜底表膨胀 | `security.py:158` | Archi |
| F-40 | 数据校验 | `extra_fields`/`consistency_issues` 无 Schema 校验，可写任意结构 | `product.py:36,38` + `schemas/product.py` | Archi |
| F-41 | 扩展性 | 导出模板字段硬编码，跨平台扩展需改代码重部署 | `export.py:45-88` | Archi |
| F-42 | 国际化 | 后端无 i18n 抽象，错误信息中英混合 | `products.py:94`、`auth.py:75` 等 | Archi |
| F-43 | 配置/安全 | `validate_secret_key` 在导入期向 .env 写文件（含生成新密钥），可能重置 SECRET_KEY 使 token 失效 | `config.py:53-92` | Archi, Cody |
| F-44 | 环境一致性 | staging 仍 SQLite + 弱 SECRET_KEY + DEBUG=true，无资源限制/健康检查 | `docker-compose.staging.yml:17,18,22,23` | Rex |
| F-45 | 指标实现 | 指标手动 f-string 拼接，延迟仅平均 gauge 无 histogram→无法算 P95/P99 SLO | `monitoring.py:128-157` | Rex |
| F-46 | CI/CD | deploy-test/deploy-production 仅 `echo` 占位，无真实部署/冒烟/回滚 | `ci-cd.yml:144-162,175-191` | Rex |
| F-47 | 文档 | api-reference 限流声明（60/600/10MB）与实际（仅 login 5次/60s）不符 | `api-reference.md:1470-1475` | Docu |
| F-48 | 备份文档 | backup-strategy / DEPLOY 的 DB 名与 compose 默认 `bilingual_product_cms` 不一致 | `backup-strategy.md:119,235`、`DEPLOY.md:104` | Docu |
| F-49 | Runbook | database-backup 恢复示例用 `username` 登录，接口要 `email` | `database-backup.md:87` | Docu |
| F-50 | 报告 | P1_P2_Issue_Report.md 日期写 2024（项目 2026） | `P1_P2_Issue_Report.md:4` | Docu |
| F-51 | ADR | ADR-006 文件名与正文标题/编号错乱（正文称 ADR-001） | `ADR-006-PostgreSQL-Migration.md:1-4` | Docu |
| F-52 | 示例 | api-reference 示例日期全为 2024 | `api-reference.md:39-40` 等 | Docu |
| F-53 | 用户手册 | user-manual 全篇无截图引导 | `user-manual.md` | Docu |
| F-54 | 部署文档 | DEPLOY 迁移示例 DB 名不一致 | `DEPLOY.md:104` | Docu |
| F-55 | CHANGELOG | 未记录 07-29 用户管理 API 重大变更 | `CHANGELOG.md:8-21` | Docu |
| F-56 | 文档 | api-reference "差异已解决"声明与事实相反（11 虚构端点） | `api-reference.md:1521-1525` | Docu |
| F-57 | 结构 | README 出现两段重复"部署"小节 | `README.md:40-44,53-56` | Docu |
| F-58 | CI/环境 | CI 用本地 sqlite 而非 postgres、redis 未测（redis.py 0%、方言缺陷从未跑） | `ci.yml:13-36`、`conftest.py:19` | Tessa |
| F-59 | 测试金字塔 | 仍倒挂：integration 47.6% > unit 23% > e2e 1.6% | 收集计数 | Tessa |
| F-60 | 代码卫生 | 源码树内调试脚本（security_test.py/test_path_traversal_fix.py）污染、游离脚本、DB 文件被提交 | `app/api/*`、`test_password_validation.py`、`*.db` | Tessa |

### 🟢 LOW（6 项，摘要）

| # | 维度 | 关键问题 | 文件:行 | 来源 |
|---|------|----------|---------|------|
| F-61 | 可维护性 | 两套审计实现/提交语义不一致 | `core/audit.py:9-37` vs `products.py:26-43` | Cody |
| F-62 | 可维护性 | 魔法数字/重复配置（page_size le=100、10MB、'/api/v1/auth' 硬编码） | `products.py:49` 等 | Cody |
| F-63 | 健康检查 | dev compose 健康检查仍 `python -c`（prod 已改 curl） | `docker-compose.yml:25` | Rex |
| F-64 | 密钥 | SECRET_KEY 校验失败写回 .env；当前目录非 git 仓库无法确认 .env 未入库 | `config.py:53-92` | Rex |
| F-65 | CORS | origins 解析容错在格式错误时退化为逗号拆分，有误配 `*` 风险 | `config.py:23,97-101` | Rex |
| F-66 | 配置 | pytest 配置重复（pytest.ini + pyproject.toml） | `pytest.ini:7-13`、`pyproject.toml:7-14` | Tessa |

---

## 🏗️ 架构影响评估（Archi）

- 模块分层健康：`api → core → models/schemas` 无环，问题集中在**数据层**与少量横切关注点。
- **最高优先级架构风险 = 迁移机制名存实亡**（F-03/F-14）：Alembic 脚手架在但 0 迁移、JSON 用 SQLite 方言类型、外键/约束残缺，ADR-006 生产化路径结构性不成立。
- ADR 落地：ADR-004（CSV 注入）、ADR-005（Redis 黑名单）、ADR-007（Token Cookie）**已落地**；ADR-002（审计中间件）、ADR-003（导出一致性）**未真正落地**（两套审计并存、ConsistencyEngine 死代码）；ADR-006 **部分落地且有关键缺口**。
- 建议新增 ADR-008（迁移单一真相源）、ADR-009（审计标准化）、ADR-010（配置/密钥与分布式限流）。

## 💻 代码与安全评估（Cody）

- **阻断级功能缺陷**：F-01 登录会话断裂、F-02 密码重置死代码——系统当前不可用、且会锁死用户，须 P0 修复。
- SQL 注入维度**已确认无风险**（全 ORM 参数化，唯一 `text("SELECT 1")` 静态）；RBAC 角色比对正确、无越权枚举。
- 安全回归/空壳：导出一致性阻断（F-10）、Alembic 空壳（F-03）、CSV 转义不全（F-31）、审计覆盖不全（F-13）、COOKIE_SECURE 未开（F-12）。
- 已修复确认：全局异常处理器（屏蔽栈）、默认凭证运行时随机化、密钥未入库。

## 🧪 测试覆盖评估（Tessa）

- **实质性改善**：pytest markers 已落地、9 个历史零覆盖端点 8 个已补、**全套 126 用例可跑通（125 passed / 1 skipped）**。
- **最大缺口**：整体行覆盖率仅 **~40%**、**CI 无覆盖率门禁**、安全错误路径（令牌吊销/禁用用户/500）基本未测或空壳、`/products/stats` 假覆盖（F-09）。
- 低覆盖模块：`core/redis.py` 0%、`schemas/import_.py` 0%、`core/consistency.py` 15.9%、`api/import_.py` 17.5%、`core/security.py` 18.7%、`api/auth.py` 25.5%。
- 测试金字塔仍倒挂（integration 主导），e2e 几乎缺失。

## 🚨 可运维性/可观测性评估（Rex）

- **可观测性链路结构性失效**：F-06（抓取路径+鉴权双错，指标采不到）+ F-07（Alertmanager 未部署）+ F-20（规则引用不存在指标）→ 告警"规则已写、实际不触发或误触发、且触发后投不出去"。
- **暴露面与传输安全**：F-08（端口全暴露+Grafana 弱口令）+ F-22（无 TLS）在生产是重大攻击面。
- 历史已修复：生产切 PostgreSQL、补 Runbook/SEV、应用镜像固定版本、资源限制、健康检查改 curl、CORS 列表校验、.env 被 gitignore。
- 仍空白：SLO/SLI 全仓库无定义、备份闭环断裂（F-21）、CI/CD 发布仅 echo 占位（F-46）。

## 📚 文档债评估（Docu）

- **最突出文档债**：`api-reference.md` 记录了 11 个代码中不存在的端点（F-04），且把 3 个已实现用户端点误标"未实现"（F-30）；README 对 SQLite/PostgreSQL 自相矛盾（F-05）。文档整体可信度低。
- 已修复：backup-strategy 去 systemctl、README 目录名/LICENS/CHANGELOG 链接、incident-response Runbook 已存在、多 .env 部分收敛。
- 仍残留：多 .env 冲突（F-15）、user-manual 无截图（F-53）、示例日期 2024（F-52）、P1_P2 报告日期过时（F-50）、ADR-006 编号错乱（F-51）。

---

## 🔁 历史高危项复核（2026-07-24 的 77 项 → 当前）

| 历史高危项 | 本轮结论 | 证据 |
|------------|----------|------|
| 默认管理员凭证硬编码 | ✅ 已修复（运行时随机化+强制改密） | `init_db.py:16-26`；但 `.env.production` 含可猜测占位（F-34） |
| Token 存 localStorage | 🔴 **回归/更糟**：ADR-007 代码在但断裂，普通登录不写 Cookie、前端不存 token→无法登录（F-01） | `auth.py:95-102`、`login/page.tsx:19`、`api.ts:6,8-18` |
| 无审计日志写入 | 🟠 部分修复：products/users/change_password 已记录，登录/登出/导出/导入缺失，两套实现并存（F-13） | `core/audit.py`、`products.py:26` |
| 导出前缺一致性阻断 | 🔴 **回归/未修复**：ConsistencyEngine 死代码，export 直接导出（F-10） | `export.py`、`core/consistency.py:10` |
| 生产用 SQLite | 🟢 已修复（prod 用 PG + 生产禁 SQLite 校验）；staging 仍 SQLite（F-44） | `config.py:46-50` |
| 数据模型缺外键 | 🟡 部分修复：Product.created_by 有 FK；AuditLog/Blacklist 的 user_id 仍无 FK（F-38） | `audit.py:12`、`token_blacklist.py:17` |
| 无全局异常处理器 | ✅ 已修复（屏蔽栈追踪） | `middleware/exception_handler.py` |
| CSV 注入防护不全 | 🟡 部分修复：sanitize 存在但 currency/stock/weight 未覆盖（F-31） | `export.py:53-88` |
| 无 Alembic 迁移工具 | 🔴 **未修复（空壳）**：0 迁移、--skip-create-tables 死参数、仍靠 create_all（F-03） | `alembic/versions`(空)、`init_db.py:32` |
| 密钥可能入库 | ✅ 已修复（.gitignore 忽略 .env）；导入期写 .env 副作用待清（F-43/F-64） | `.gitignore` |
| API 文档缺 11 端点 | 🔴 **反转**：现 api-reference 反而多 11 个虚构端点 + 3 个误标未实现（F-04/F-30） | `api-reference.md` |
| Prometheus 告警规则缺失/失效 | 🟠 规则已写但**全部不生效**（F-06/F-07/F-20） | `prometheus.yml`、`alertmanager.yml` |
| 无 TLS/HTTPS | 🔴 仍存在（F-22） | `nginx.conf:2`、`config.py:20` |
| 无 Runbook/事故响应 | ✅ 已修复（含 SEV）；Runbook 引用失效（F-17） | `incident-response.md` |
| 生产端口暴露/弱口令 | 🔴 仍存在（F-08） | `docker-compose.prod.yml:89,109,132,142,144` |
| 备份无调度/远程/加密 | 🔴 仍存在（F-21） | `backup.py`/`backup.sh` |
| 监控指标手动拼接无直方图 | 🟡 仍存在（F-45） | `monitoring.py:128-157` |
| Docker 镜像全 :latest | 🟡 部分修复（应用固定；监控仍 :latest，F-23） | `ci-cd.yml:107-111`、`prod:129,139` |

---

## ✅ 行动清单（按优先级排序）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|----------|--------|----------|
| 1 | **修复登录会话断裂**：普通登录写 `set_auth_cookies` + 前端 `setToken`/改 `/auth/me` 探活，移除 `getToken()` 守卫依赖 | Cody + 前端 | P0 | 2 天内 |
| 2 | **修复密码重置死代码**：`reset_user_password` 补 `return` 临时密码，删 519-524 不可达代码 | Cody | P0 | 当天 |
| 3 | **打通 Alembic 迁移**：生成初始迁移、移除 `create_all`、实现 `--skip-create-tables`、JSON 改 `sqlalchemy.JSON`、补 FK `ondelete` | Archi + Cody | P0 | 3 天内 |
| 4 | **修复可观测性闭环**：新建无鉴权 `/metrics`、prod 部署 Alertmanager、修正 scrape 路径与告警规则（去 `probe_success`/补 node-exporter） | Rex | P0 | 3 天内 |
| 5 | **收敛暴露面 + TLS**：数据库/缓存不映射宿主机、Grafana 强口令去 `:-admin`、Nginx 443 + `COOKIE_SECURE=true` | Rex + Cody | P0 | 3 天内 |
| 6 | **文档事实源对齐**：以代码为唯一事实源重写 api-reference（删 11 虚构端点、修正 3 误标）、统一 README/多 .env/DB 名表述 | Docu | P0 | 3 天内 |
| 7 | **落地导出一致性阻断 + 补审计覆盖**：export 前调 ConsistencyEngine 阻断 ERROR；登录/登出/导出/导入写审计，统一审计服务 | Cody + Archi | P1 | 1 周内 |
| 8 | **CI 加门禁**：`--cov-fail-under=70` + gitleaks 密钥扫描；让测试连 postgres/redis（解决 redis.py 0%） | Tessa + Rex | P1 | 1 周内 |
| 9 | **补齐安全测试**：令牌吊销/禁用用户/500 处理/reviewer fixture（F-25~F-29） | Tessa | P1 | 1 周内 |
| 10 | **备份闭环 + 其它 P2**：pg_dump+加密+远端+调度；staging 对齐 prod；指标 histogram；CSV 转义补全；导入缓存改 Redis/落盘；N+1 改 IN | Rex + Cody + Archi | P2 | 2 周内 |

---

## ⚠️ 待完善 / 已知局限

- **未做动态验证**：本轮为静态代码/配置审查，未实际启动服务跑登录/导出/告警链路做端到端验证；F-01/F-02 的功能性结论基于代码路径分析，建议修复后补集成测试固化。
- **仓库非 git 状态**：`git ls-files` 报 "not a git repository"，故 .env 是否入库、密钥是否泄露只能依据 `.gitignore` 推断，无法用 git 历史二次确认（F-64）。
- **前端覆盖极低**：前端仅 1 组件单测 + 1 e2e spec，权限渲染/导入交互基本无测试（F-58 类），本轮前端审查以代码路径为主。
- **覆盖率数字来源**：Tessa 报告的整体 ~40% 行覆盖基于仓库内 `coverage.xml` 最近一次本地运行；CI 未设门禁故该数字不阻断合并。

---

## 📚 数据来源 & 成员产出索引

- **Cody（代码审查师）** 原始产出：安全/性能/正确性/可维护性审查，18 条发现 + 历史高危 10 项复核（含 F-01/F-02/F-03/F-10~F-13/F-31~F-38/F-43/F-61/F-62）。
- **Archi（系统架构师）** 原始产出：架构维度审查，12 条发现 + ADR 落地复核（含 F-03/F-10/F-13/F-14/F-39~F-43）。
- **Tessa（测试专家）** 原始产出：测试维度审查，13 条发现 + 历史测试缺陷复核 + 覆盖率数据（含 F-09/F-24/F-25~F-29/F-58~F-60/F-66）。
- **Rex（SRE 工程师）** 原始产出：可运维性/可靠性审查，16 条发现 + 历史运维缺陷复核 + SLO/告警现状（含 F-06~F-08/F-15/F-17~F-23/F-44~F-46/F-63~F-65）。
- **Docu（技术文档师）** 原始产出：文档债审查，18 条发现 + 历史文档缺陷复核（含 F-04/F-05/F-15~F-18/F-30/F-47~F-57）。

---

> 本报告由工程保障团队 AI 协作生成，关键决策请由人类工程负责人复核。
> 完整原始成员产出可于团队会话中回溯；本报告为去重合并后的统一视图。
