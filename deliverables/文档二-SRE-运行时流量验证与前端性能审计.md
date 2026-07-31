# 文档二（节选）· 三验证分析说明 —— 运行时流量验证 + 前端性能审计

> 编制：SRE 工程师（Rex / 雷克斯）　|　系统：跨境产品资料中英对照系统（bilingual-product-cms）
> 背景：上一轮综合审计将以下两项列为「已知限制 / 尚未执行」。本文基于**实际文件核查**给出就绪状态、缺失条件与可执行路径。
> 核查涉及文件：`docker-compose.yml` / `docker-compose.prod.yml` / `docker-compose.full.yml` / `docker-compose.test.yml` / `deploy/nginx/nginx.conf` / `frontend/Dockerfile` / `frontend/next.config.js` / `backend/docker-entrypoint.sh` / `backend/app/monitoring.py` / `monitoring/*.yml` / `deploy/monitoring/*` / `docs/monitoring-guide.md`。

---

## 一、TOPIC A —— 运行时流量验证（Runtime Traffic Verification）

### A.1 目标（Objective）
在贴近生产的流量下验证 API 行为，以达成三件事：
1. **捕获回归（Catch regressions）**：新版本上线前，确认既有接口在真实请求组合下未出现性能或行为退化。
2. **在类生产负载下验证 30 个端点**：后端 `backend/app` 下共 **30 个** 路由装饰器（实测计数，与上一轮「30 endpoints」一致；其中 `main.py` 含 `/`、`/health`、`/metrics`、`/metrics/prometheus`、`/shutdown-status` 等基础路由，其余为业务路由）。需要在生产近似负载下逐一验证。
3. **确认 404 修复未破坏其他流程**：上一轮审计指出的 404 修复（具体路由见审计记录）必须纳入场景，断言这些路径现返回 200/预期状态，同时其余路径仍保持原有状态，无副作用。

### A.2 执行前提与实际操作环境要求
- **流量录制（Recording）**可选方法：
  - 代理式：mitmproxy 注入请求路径做透明抓取；
  - 网络层抓包回放：GoReplay（`goreplay`）从镜像/生产环境旁路捕获真实流量；
  - 内核层：tcpcopy；
  - 日志导出：从 API 网关或 Nginx access log 导出请求。
- **回放目标（Replay）**：必须把录制流量打向一个**具备 parity 的 STAGING 环境**（相同 DB schema、已种子化/脱敏的数据），而非生产。
- **安全要求**：① 绝不向 prod 回放；② 对 PII 做脱敏/匿名化；③ 设置速率限制（rate limiting），避免压垮依赖。

### A.3 当前环境就绪状态（实测证据）
| 子能力 | 状态 | 证据 |
|---|---|---|
| 后端生产部署 | ✅ 就绪 | `backend/docker-entrypoint.sh`：生产模式下 `uvicorn app.main:app --workers 4`；`docker-compose.prod.yml` 设 `WORKERS=4` |
| 后端指标可观测性 | ✅ 就绪 | `backend/app/main.py:166` 暴露 `/metrics`、`/metrics/prometheus`；`backend/app/monitoring.py` 输出 `app_requests_total`、`app_errors_total`、`app_response_time_seconds`、`app_uptime_seconds`、`system_cpu_percent`、`system_memory_percent`、`system_disk_percent` |
| 流量录制机制 | ❌ 缺失 | 仓库内**无** mitmproxy / GoReplay / tcpcopy 配置；**无 API 网关**组件（compose 中仅有 Nginx 反向代理 + FastAPI） |
| Nginx 访问日志 | ❌ 缺失 | `deploy/nginx/nginx.conf` **完全没有 `access_log` / `log_format` 指令**（已 grep 确认），无法从日志导出流量 |
| Staging 环境（parity 回放靶机） | ❌ 缺失 | 仅存在 `docker-compose.yml`(dev)、`docker-compose.prod.yml`、`docker-compose.full.yml`、`docker-compose.test.yml`；**无专用 staging profile/compose** |
| DB parity（克隆/种子/脱敏） | ❌ 缺失 | prod 用 Postgres（`DATABASE_URL=postgresql://...`，见 `.env.production`），dev/test 用 SQLite；**无脱敏脚本**；`scripts/backup.py` 仅做 `pg_dump` 备份，非脱敏/种子化 |
| 安全控制（脱敏/限流/禁打 prod） | ⚠️ 部分 | Nginx 未配 `limit_req`（无限流）；无 PII 脱敏工具；需以流程约束保证不回放 prod |

> 说明：已发现监控配置缺陷（与本次验证强相关）——`monitoring/prometheus.yml`（被 `docker-compose.prod.yml` 与 `deploy/monitoring/docker-compose.monitoring.yml` 挂载）的 `job_name: 'backend'`，而 `monitoring/alerts.yml` 的 `ServiceDown`/`DatabaseConnectionFailed` 规则引用 `up{job="bilingual-product-cms-backend"}`（且 `DatabaseConnectionFailed` 还用了未部署的 `probe_success`）。结果：**这两条告警实际永远不会触发**。另有本地副本 `deploy/monitoring/prometheus.yml` 用了正确 job 名但并未被任何 compose 挂载（孤儿配置）。加载测试期间即便服务宕机，ServiceDown 告警也静默，只能靠直接查 `/metrics` 与 Grafana 看板观测。

### A.4 缺失条件清单
1. 任意一种**流量录制通道**（推荐 GoReplay 旁路抓包，或先补 Nginx `access_log` 再日志导出）。
2. 一个**独立 staging compose**（含独立 Postgres 卷、独立 redis、独立前端/后端服务名，避免与生产串扰）。
3. **DB 克隆 + 脱敏 + 种子化**流水线（可基于现有 `postgresql_migration.py` + `init-postgres.sh` 扩展，增加匿名化步骤）。
4. Nginx `access_log` + `log_format` 配置（若走日志导出路线）。
5. 速率限制与「禁止回放 prod」的流程闸门。

### A.5 环境搭建 / 替代方案建议
回放式验证成本高（需录制通道 + staging parity + 脱敏）。**最快达成「30 端点 + 404 修复在类生产负载下验证」目标的替代方案是合成负载测试（synthetic load testing）**，无需录制真实流量：

- 工具：**k6** 或 **Artillery**，打向 staging（或 prod-like 的 `docker-compose.prod.yml` 副本）。
- 优势：可直接枚举 30 个路由构造场景；用阈值断言（p95 延迟、错误率、状态码分布）验证 404 修复前后无回归；配合后端 `/metrics` 实时观测。
- 草拟步骤：
  1. 复制 `docker-compose.prod.yml` 为 `docker-compose.staging.yml`，改服务名/端口/卷名，挂独立 Postgres 卷；
  2. 用 `init-postgres.sh` + `postgresql_migration.py` 初始化 schema，灌入脱敏后的种子数据；
  3. 编写 k6 脚本：`/health` 探活 + 30 个业务端点场景（含被 404 修复影响的路径，断言返回 200 且其余路径保持原状态码）+ 阶梯 VU 加压；
  4. 观测：Prometheus(`/metrics`) + Grafana；关注 `app_response_time_seconds`、`app_errors_total`；
  5. 出报告：p95/p99 延迟、错误率、是否触发 `HighErrorRate`/`CriticalResponseTime` 等（注意告警 job 名缺陷需先修，否则依赖告警会静默）。

### A.6 推荐执行路径
**优先采用 k6 合成负载测试**（成本最低、最快闭环）→ 若后续确有「回放真实流量」诉求，再补 GoReplay + staging parity + 脱敏。无论哪条路，**先修监控告警 job 名不匹配**（`monitoring/prometheus.yml` 的 `backend` → `bilingual-product-cms-backend`，或反之统一 `alerts.yml`），否则验证期间的可用性告警全部失效。

---

## 二、TOPIC B —— 前端性能审计（Frontend Performance Audit）

### B.1 目标（Objective）
度量 Core Web Vitals、定位性能瓶颈，并验证上一轮审计涉及的**6 个新增页面**（当前前端 App Router 实际共 **10 个**路由：`/`、`/login`、`/products`、`/products/new`、`/products/import`、`/products/[id]`、`/terms`、`/audit`、`/export`、`/settings/users`）在上线后**不产生性能回退**。

### B.2 审计指标（Metrics）
- **LCP**（最大内容绘制）、**FID / INP**（首次输入延迟 / 交互到下一帧）、**CLS**（累计布局偏移）；
- **TTFB**（首字节时间）、**FCP**（首次内容绘制）；
- **Bundle 体积**、**TBT**（Total Blocking Time，总阻塞时间）。

### B.3 测试工具（Tools）
- **Lighthouse CI**（门禁式性能卡点）、**WebPageTest**（多地域/多设备）、**Chrome DevTools Protocol**（脚本化采集）；
- **RUM**（真实用户监控）：前端注入 `web-vitals.js` 上报字段数据；
- **Next.js 内置分析 / Vercel Analytics**（注意：本系统为自托管 Docker 部署，**Vercel Analytics 不直接适用**，需自建 RUM 上报端点）。

### B.4 当前环境就绪状态（实测证据）—— 重要纠正
> ⚠️ **纠正上一轮假设**：任务提示称「前端 `Dockerfile` 运行 `next dev`、从不构建生产包，导致性能审计无法进行」。但**实际 `frontend/Dockerfile` 第 10、14 行执行为 `RUN npm run build` + `CMD ["npx","next","start",...]`**，即**确实构建并运行生产包**（`package.json` 中 `build=next build`、`start=next start`）。因此「前端无法做有效性能审计」的前提**不成立**——只要经由 Docker 部署或本地 `next build && next start`，即可得到真实生产产物用于审计。

| 子能力 | 状态 | 证据 |
|---|---|---|
| 生产构建产物（next build） | ✅ 就绪 | `frontend/Dockerfile` 执行 `npm run build` + `next start`（非 dev） |
| 本地 prod 替代路径（`next build && next start` + Lighthouse） | ✅ 可行 | 因上述 Dockerfile 已生产构建，本地亦可直接复现 |
| `next.config.js` 性能调优 | ⚠️ 部分 | 仅配置 `/api` rewrite（`next.config.js`）；**无**静态资源缓存、压缩、`images` 优化、header 策略；`deploy/nginx/nginx.conf` 也未加缓存/压缩头 |
| 稳定 Staging / Preview URL | ❌ 缺失 | 无部署环境或预览 URL（同 Topic A，无 staging） |
| Lighthouse CI 集成 | ❌ 缺失 | 前端依赖中无 `@lhci/cli`，CI 流程无性能门禁步骤 |
| RUM 字段数据（web-vitals.js） | ❌ 缺失 | `frontend/package.json` **无 `web-vitals` 依赖**，无上报端点 |
| Bundle 体积分析 | ❌ 缺失 | 无 `@next/bundle-analyzer`，无法在 CI 出包体积趋势 |
| 监控栈对前端的覆盖 | ❌ 缺失 | Prometheus 仅抓后端 `/metrics`；**无前端 RUM 指标管线**，前端性能只能靠 Lighthouse/手动，无法持续 |

### B.5 缺失条件清单
1. 一个可访问的 **staging/preview URL**（或至少本地 `next build && next start` 的标准化入口）。
2. **Lighthouse CI** 接入流水线（`@lhci/cli` + 断言阈值，作为合并门禁）。
3. **RUM  instrumentation**：引入 `web-vitals.js` 并把指标上报到自建端点（可用现有后端加一个 `/metrics/rum` 或独立收集器）。
4. **Bundle 分析**：接入 `@next/bundle-analyzer`，在 CI 出体积报告，监控 6 个新页面引入的包增量。
5. **`next.config.js` / Nginx 性能调优**：静态资源长缓存、`Cache-Control`、`compress`、图片优化；在 `deploy/nginx/nginx.conf` 补缓存/压缩头。

### B.6 替代方案（无 Staging URL 时）
无需等待部署环境：**本地直接 `npm run build && npm run start`（或经 `frontend/Dockerfile` 起容器），对 `http://localhost:3000` 跑 Lighthouse**，覆盖全部 10 个路由（重点对比 6 个新增页面）。流程：
1. `cd frontend && npm ci && npm run build && npm run start`；
2. 用 Lighthouse（CLI/CI）对每个路由采集 LCP/INP/CLS/TBT/TTFB/FCP，记录基线；
3. 引入 `@next/bundle-analyzer` 看包体积，定位大依赖；
4. 在 `next.config.js` 与 Nginx 加缓存/压缩头后复测，对比改善；
5. 后续将 Lighthouse CI 固化进 PR 门禁，防止回退。

---

## 三、环境就绪状态总表（Readiness Summary）

### TOPIC A —— 运行时流量验证
| 条件 | 状态 | 证据 | 建议 |
|---|---|---|---|
| 后端生产部署（uvicorn workers=4） | ✅ 就绪 | `backend/docker-entrypoint.sh` | 直接可用 |
| 后端指标 `/metrics` | ✅ 就绪 | `backend/app/monitoring.py` | 加载测试期间观测 |
| 流量录制通道（mitmproxy/GoReplay/tcpcopy/网关） | ❌ 缺失 | 仓库无任何此类配置/组件 | 优先 GoReplay 或转合成测试 |
| Nginx 访问日志 | ❌ 缺失 | `deploy/nginx/nginx.conf` 无 `access_log` | 若走日志路线需补 |
| Staging 回放靶机（parity） | ❌ 缺失 | 无 staging compose | 复制 prod compose 改名/卷 |
| DB 克隆+脱敏+种子 | ❌ 缺失 | 无脱敏脚本；prod=Postgres, dev/test=SQLite | 基于 migration 脚本扩展匿名化 |
| 限流 / 禁打 prod 闸门 | ⚠️ 部分 | Nginx 无 `limit_req`；无脱敏；需流程约束 | 加 `limit_req` + 流程卡点 |
| 监控告警可用（验证期可用性） | ⚠️ 缺陷 | job 名 `backend`≠`bilingual-product-cms-backend`，ServiceDown 静默 | 先修 prometheus/alerts 一致性 |

### TOPIC B —— 前端性能审计
| 条件 | 状态 | 证据 | 建议 |
|---|---|---|---|
| 生产构建产物 | ✅ 就绪 | `frontend/Dockerfile`（build+start，非 dev）【纠正旧假设】 | 直接可用 |
| 本地 prod 替代路径（build+start+Lighthouse） | ✅ 可行 | 同上 | 无 staging 时即采用 |
| 稳定 Staging/Preview URL | ❌ 缺失 | 无部署/预览环境 | 建 staging 或本地标准化入口 |
| Lighthouse CI 门禁 | ❌ 缺失 | 无 `@lhci/cli` | 接入 PR 门禁 |
| RUM（web-vitals.js 字段数据） | ❌ 缺失 | 无 `web-vitals` 依赖/上报端点 | 自建 RUM 上报 |
| Bundle 体积分析 | ❌ 缺失 | 无 `@next/bundle-analyzer` | 接入 CI 体积趋势 |
| `next.config`/Nginx 性能调优 | ⚠️ 部分 | 仅 rewrite；无缓存/压缩/图片优化 | 补缓存与压缩头 |
| 监控栈前端覆盖 | ❌ 缺失 | Prometheus 仅抓后端 | 建前端 RUM 管线 |

### 跨两项的关键阻断项（建议优先处理）
1. **无 staging 环境** —— 同时阻塞 A（回放靶机）与 B（稳定审计 URL）。建 `docker-compose.staging.yml` 是两项共同前置。
2. **监控告警 job 名不匹配**（`monitoring/prometheus.yml` 的 `backend` vs `alerts.yml` 的 `bilingual-product-cms-backend`，且 `deploy/monitoring/prometheus.yml` 正确副本未被挂载）——会导致验证/运营期间 ServiceDown 静默，须先修。
3. **无 PII 脱敏 + 限流** —— 回放/录制前必须满足，否则有合规与压垮风险。

---

## 四、给协作方的交接提示
- **给架构师（architect）**：前端的「生产构建」质疑已被澄清——Dockerfile 实为生产构建，旧审计关于「前端永不构建 prod」的判断需更新；但 `next.config.js` 缺乏性能相关配置仍是真实优化点。
- **给 Cody（code-reviewer）**：监控告警 `job_name` 不一致属于配置缺陷，建议在数据库迁移/配置整改中一并修复；`backend/venv` 似被纳入仓库（grep 污染来源），建议确认 `.gitignore` 是否遗漏虚拟环境目录。
