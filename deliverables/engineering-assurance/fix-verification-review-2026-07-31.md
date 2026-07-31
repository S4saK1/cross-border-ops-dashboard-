# 修复验证型全面工程审查报告 — 双语产品资料中英对照系统

**日期**：2026-07-31
**工作流**：工作流 1（全面代码审查）+ 工作流 5（技术债评估）混合 · 修复验证专项
**参与成员**：Cody（代码审查师）/ Archi（架构师）/ Rex（SRE）/ Tessa（测试专家）/ Docu（文档师）
**基线**：2026-07-30 综合审查（🟡 有条件通过，68 项开放债）
**验证对象**：用户申报的 12 项 P0 行动（K1-K10 / F-02 / F-05，其中 7 项声称代码已修、5 项归 Ops）

---

## 📌 TL;DR（执行摘要）

- **整体结论：🔴 不通过（当前状态不可部署）**。7 项代码修复中 4 项 VERIFIED、4 项 PARTIAL——修复方向正确、逐项实测功能可用，**但修复过程引入 2 个新 P0 回归**：生产 compose 被改成无效 YAML（无法 `up`）、backup.sh 被编码工具吞成单行注释（备份静默 no-op）。
- **本轮从容器侧新挖出 3 个 07-30 未掌握的深层 P0**：生产镜像内嵌开发密钥（.dockerignore 缺 .env）、redis 不在 requirements.txt（生产导入流 ~75% 间歇故障、限流×4 失效）、httpOnly Cookie 读取路径是死代码（K1 被架空）。
- **严重度分布（合并去重后开放项）**：🔴 严重 14 项 / 🟠 高 17 项 / 🟡 中 21 项 / 🟢 低 9 项，共 61 项（原列 H14 经字节级复核实为误报已撤回，原计入 🟠 高）。
- **阻塞项**：6 项硬阻断（NEW-1 / NEW-2+N23 / A-N1 / A-N2 / C-1 / N25），**全部是分钟级~小时级修复，总成本约 1 天**。
- 07-30 的开放债本轮**几乎全部未触及**（Cody 13/13、Archi 11 项 0 RESOLVED、Tessa 仅 B1 解决），且 6 项修复**零新增回归测试**——K6 场景下现有测试甚至反向掩盖故障。

> ⚠️ **勘误（2026-07-31 第三轮交叉核实）**：H14 原报 `runbooks/database-backup.md` 为"第 4 个换行损坏文件"，经字节级复核确认为**误报**，已撤回（详见 H14，中招文件维持 3 个）。CI 门禁方案已从"命令-注释粘连"指纹调整为 **R1-R4（行长异常思路）**，见行动项 #16。

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🔴 不通过（生产 compose 语法无效 + 备份-恢复路径归零，属硬阻断；但均为快速修复） |
| 阻塞项数量 | 6 项（NEW-1、NEW-2+N23、A-N1、A-N2、C-1、N25） |
| 关键行动项 | 20 条（P0×8 / P1×7 / P2×5） |
| 修复验证结果 | 12 项申报：**VERIFIED 4**（K2/K3/K4/K5）/ **PARTIAL 4**（K1/K6/F-02/F-05）/ Ops 4 项中**仅 K7 真就绪**，K9/K10 反而引入新 P0 |
| 测试守护 | 7 项修复中**6 项无回归测试锁定**；删规则文件后 145 测试依然全绿（结构性盲区） |
| 建议下一步 | 先做"1 天止血包"（见行动清单 P0 段），再补 Tessa 的 P0 守护测试，然后才可宣布修复稳定 |

---

## 一、12 项申报修复的逐项验证结果（五方交叉核实）

| # | 申报项 | 申报状态 | 验证结论 | 关键证据与缺口 | 验证人 |
|---|--------|---------|---------|---------------|--------|
| 1 | K1 登录会话 | ✅ 已修 | ⚠️ **PARTIAL** | `set_auth_cookies` 在 login/refresh 均调用 ✓，前端 `credentials:'include'` ✓；**但 `security.py:13` OAuth2PasswordBearer 未设 `auto_error=False`，无 Authorization 头时依赖解析阶段即 401，cookie 回退（:219-221）是死代码** → 系统实际仍 100% 依赖 header 传 token，前端刷新页面丢内存 token 即被踢回登录页 | Cody |
| 2 | K2 密码重置 | ✅ 已修 | ✅ **VERIFIED** | users.py:405 真实返回 `temporary_password`；force_password_change + revoke 全 token 齐备；**有高质量测试锁定**（实测 200 + 断言通过） | Cody+Tessa |
| 3 | K3 Alembic | ✅ 已修 | ✅ **VERIFIED**（零测试守护） | 迁移存在、entrypoint 走 `alembic upgrade head`、create_all 可跳过；但 CI 无 `alembic upgrade` 步骤，迁移零测试 | Cody+Tessa |
| 4 | K4 导出阻断 | ✅ 已修 | ✅ **VERIFIED**（宽容断言） | export.py:41-56 ERROR→409 实测生效；但唯一相关测试断言 `in (200,400,404,409)`，**回归成 200 也能绿**；且存在双重全表扫描 + ERROR 重复计数（C-3/B3） | Cody+Tessa |
| 5 | K5 导入全量 | ✅ 已修 | ✅ **VERIFIED**（Excel 分支隐患） | 实测 150 行 CSV 全量导入成功；但重解析仅支持 CSV，**Excel 上传时重解析异常会静默回落 100 行缓存**（截断在异常路径复现，无告警、无测试） | Cody+Tessa |
| 6 | K6 一致性路径 | 🔧 今天修 | ⚠️ **PARTIAL** | 路径修对：app/data 双文件 md5 与源一致、容器内 `/app/app/data` 解析正确（Archi 双场景实证）、232 条同义词实测加载 ✓、`./data:/app/data:ro` 挂载不构成覆盖 ✓。**三个缺口**：① 复制而非移动 → 根目录旧副本成死数据（B12 数据双源），PRD 7 处仍指旧路径，改旧文件不生效不报错；② 零启动自检，FileNotFoundError 静默返回空规则；③ **测试反向掩盖故障**——Tessa 独立复现：删掉两个 JSON 后 145 测试全绿 | Archi+Cody+Tessa+Docu |
| 7 | K7 TLS | ⏸️ Ops | ✅ **代码就绪**（4 项 Ops 中唯一） | nginx.conf 完整 TLS 配置 + compose 挂载就绪；仅差 Ops 放证书（`deploy/nginx/ssl/` 目录不存在，放之前 nginx 崩溃退出 → 整站白屏） | Rex |
| 8 | K8 Alertmanager | ⏸️ Ops | ❌ **代码层未就绪** | alertmanager.yml 用 `${SMTP_SMARTHOST}` 等占位符，**Alertmanager 原生不做环境变量替换** → 当字面量解析、config 校验失败、容器 crash-loop；webhook 仍指向不存在的 `alertmanager-webhook:5001` | Rex |
| 9 | K9 端口收敛 | ⏸️ Ops | ❌ **引入新 P0（NEW-1）** | 收敛方向正确，但注释端口后留下裸 `ports:` 空键（grafana ~L147、postgres ~L88）→ `docker compose config` 直接报错，**prod compose 当前是无效配置，生产无法启动**。修复 = 删 2 行 | Rex（实测复现） |
| 10 | K10 备份 | ⏸️ Ops | ❌ **引入新 P0（NEW-2）** | backup.sh 被编码修复脚本吞掉全部换行：**3258 字节全在一行，整个文件 = 一条注释，执行时不报错、零输出、exit 0**。deployment-checklist 的验收项恰是"executes successfully"——**永远通过**，静默成功型失效 | Rex+Docu（字节级实证） |
| 11 | F-02 JWT 脱敏 | ✅ 已修 | ⚠️ **PARTIAL** | exception_handler.py:36 redact Authorization ✓；**但 Cookie 头未脱敏**——K1 迁移后 token 就在 Cookie 里，未捕获异常仍把完整 JWT 写日志（C-2） | Cody |
| 12 | F-05 SECRET_KEY | 🔧 今天修 | ⚠️ **PARTIAL 且方向错误**（三方独立一致） | staging/test 确实改成 `${SECRET_KEY:-fallback}`，full.yml 升级 `:?` ✓；**但 fallback 是入库、公开可猜的固定字符串**——比原先"每次重启随机"是安全负收益（可离线伪造 staging admin JWT）。更严重：**四套 compose 守卫语义倒挂**——base 有 `:?`、**prod 却是裸 `${SECRET_KEY}` 空值静默通过**（N25），生产比开发宽松 | Rex+Cody+Archi |

---

## 二、🔍 本轮新发现（按严重度排序，合并去重）

### 🔴 严重（14 项）

| # | 类别 | 位置 | 问题 | 建议修复 | 来源 |
|---|------|------|------|---------|------|
| R1 | 部署 | docker-compose.prod.yml（grafana ~L147 / postgres ~L88） | **NEW-1：裸 `ports:` 空键使 prod compose 语法无效，生产不可部署**（`config` 实测报错） | 删 2 行裸 `ports:`，`docker compose config -q` 过门禁 | Rex |
| R2 | 备份 | scripts/backup.sh | **NEW-2：全文件被吞成单行注释，执行 = 静默 no-op exit 0**；checklist 验收项"executes successfully"恰被绕过 | 重写脚本（产物缺失/为空时显式 exit 1）；checklist 改为"产物存在+大小阈值+恢复演练留痕" | Rex+Docu |
| R3 | 备份 | docs/backup-strategy.md :92/:220/:251 三段 | **N23：恢复手册先 stop 再 exec，照抄必失败**；叠加 R2，**项目当前没有任何可用的备份-恢复路径** | 改 `docker compose cp`；重写恢复章节后做恢复演练 | Rex+Docu |
| R4 | 安全/密钥 | backend/.dockerignore + config.py:60-68 + prod.yml:44 | **A-N1：生产镜像内嵌开发密钥链**——.dockerignore 不含 `.env` → `COPY . .` 把真实 SECRET_KEY 烤进每个镜像；prod compose 无 `:?` 守卫；config.py 空值时回落读容器内 `/app/.env` ⇒ 生产可能无告警地用仓库内开发密钥签全部 JWT。gitleaks 扫不到（泄漏在 Docker 侧） | .dockerignore 加 `.env`/`.env.*`；prod 改 `:?`；production 禁用 .env 回落（共 4 行）；**轮换已暴露密钥** | Archi |
| R5 | 依赖 | backend/requirements.txt | **A-N2：redis 未声明依赖**——本地 venv 有所以看不出；生产镜像 `import redis` 失败被 `except ImportError: pass` 吞掉 ⇒ 4-worker 下导入三步流 ~75% 概率"文件已过期"、登录限流阈值×4、prod 的 redis 容器永远不被连接；CI 装同一份 requirements 永远发现不了 | 加 `redis>=5.0.0`；静默降级改 logger.error + prod fail-fast | Archi |
| R6 | 安全/认证 | security.py:13 | **C-1：httpOnly Cookie 读取是死代码**（auto_error=True）→ K1 名存实亡，前端刷新即 401 | `OAuth2PasswordBearer(tokenUrl=..., auto_error=False)` + fallback 后统一判空 | Cody |
| R7 | 安全/日志 | exception_handler.py:36 | **C-2：Cookie 头未脱敏**，未捕获异常泄漏完整 JWT 到日志 | redact 集合加 `cookie`、`x-csrf-token` | Cody |
| R8 | 安全/配置 | 4 套 compose | **N25：SECRET_KEY 守卫语义倒挂**（base `:?` / prod 裸变量 / staging-test 弱固定 fallback），生产最宽松 | 收敛决定（团队已对齐）：prod/staging 改 `:?`，test 保留 fallback | Rex+Archi+Cody |
| R9 | 测试 | tests/test_consistency.py | **K6 结构性盲区：删规则文件后 145 测试全绿**——现有断言全是"检不出问题"，规则全空时同样通过 | 补 3 条正向守护测试（数据已加载≥200 同义词 / 已知违规能检出 / 文件存在可解析）+ lifespan 启动自检约 20 行 | Tessa+Archi |
| R10 | 监控 | docker-compose.prod.yml prometheus volumes | **N1（沿袭未修）：prod 未挂载 alerts.yml**，13 条告警规则生产不生效，rule_files 指向不存在文件 | volumes 加一行挂载 + CI `promtool check rules` | Rex |
| R11 | 部署/TLS | deploy/nginx/ssl | **N2（沿袭，Ops）：证书目录不存在**，nginx 启动即崩、整站白屏 | Ops 按清单放证书 + 续期 cron（代码侧已就绪） | Rex |
| R12 | 迁移 | scripts/postgresql_migration.py:266 | **N3（沿袭未修）：`postgres_table` 未定义变量，迁移验证必然 NameError** | 改为 `table`（1 行）+ 迁移集成测试 | Rex |
| R13 | 文档/上手 | README.md:86-92 / DEPLOY.md | **D1：F-05 的 base `:?` 使"一键启动"必失败**，前置条件无 SECRET_KEY、无 `cp .env.example .env` | README/DEPLOY/QUICKSTART 补前置步骤（约 30 分钟） | Docu |
| R14 | 文档/API | docs/api-reference.md | **B11（沿袭一字未改）：3 个 /terms/{id} 幽灵端点 + 3 个已实现 users 端点误标"未实现"**；README 清单与代码完全一致，api-reference 是错的那份 | 以 README/代码为准回写；CI 加 /openapi.json 快照 diff 门禁 | Docu+Archi |

### 🟠 高（18 项，摘要）

| # | 问题 | 来源 |
|---|------|------|
| H1 | A-N3：`/health` 恒返回 200（DB 挂了只改 JSON 字符串），`curl -f` 健康检查失明 → 容器自愈链断裂 | Archi |
| H2 | B3 假修复：CI 加了 Postgres 服务但 conftest.py:32 硬编码 SQLite，CI 绿 ≠ PG 行为被验证 | Tessa |
| H3 | N1(Cody)：refresh token 仍走 JSON body、服务端从不读 refresh cookie，7d TTL 可被 XSS 窃取 | Cody |
| H4 | K8：alertmanager.yml 占位符不被展开 → crash-loop；需 envsubst entrypoint 方案 | Rex |
| H5 | B12：数据双源 split-brain——宿主挂载的规则文件成死数据、dictionary.json 却只能从挂载读，同类数据两套加载契约 | Archi |
| H6 | C-4：第三处死副本 data/templates/*.json（无人读取且 schema 已漂移）——"复制不删旧"是系统性模式 | Cody |
| H7 | N5/B3(Archi)：导出双重全表扫描恶化 + 阻断爆炸半径错误（导出 1 个干净产品被无关产品 409 阻断） | Cody+Archi |
| H8 | B4(Archi)：BaseHTTPMiddleware 异常处理——路由 HTTPException 到不了中间件，前端面对两套错误契约；包裹 StreamingResponse 抵消流式导出 | Archi |
| H9 | 限流 fail-open（redis.py `except: return True`）+ 内存回退死代码 + 计数 dict 非线程安全 | Cody+Tessa |
| H10 | force_password_change 服务端不拦截；/register 开放无限流 | Cody |
| H11 | users.py 覆盖率 29%，create/update/delete/bulk/reset 写路径零测试 | Tessa |
| H12 | K5 Excel 分支静默截断 + 导入零审计（import/terms 模块 write_audit_log = 0） | Tessa+Archi |
| H13 | 根 .env 把 ACCESS_TOKEN_EXPIRE_MINUTES 覆盖回 1440（24h），削弱 30min 默认值 | Cody |
| ~~H14~~ | ⚠️ **[已撤回]** 原报 "runbooks/database-backup.md :154-158 命令-注释粘连（第 4 个换行损坏文件）"——Rex 字节级复核实为干净文件（LF=204 / BS=0 / loneCR=0 / maxline=192），属本会话 Bash 工具吃换行造成的显示层误报，不计入开放债 | Rex |
| H15 | N24：monitoring-guide 让 Prometheus 抓需 admin 的 /metrics（两处 job 均 401 永久 DOWN）+ 查找替换事故乱码 | Rex+Docu |
| H16 | D3/N26：PRD 7 处指旧 data/ 路径；4 个 compose 的 ./data 挂载对规则文件已失效 | Docu+Rex |
| H17 | D4：CHANGELOG 未记录今日批次 + F-05/F-02 同号异义 ID 冲突 + 结构损坏（1.1.0 在 H1 之上） | Docu |
| H18 | passlib 1.7.4 + bcrypt>=4.0 兼容炸弹（允许装 4.1+ 直接硬失败）；requirements 全 `>=` 零锁定，构建不可复现 | Cody+Archi |

### 🟡 中（21 项，代表项）

一致性规则静默降级无日志（C-5）｜导入临时文件泄漏（N10）｜term.created_by 无 FK｜CSV sanitize 仍缺 `\n`｜/users/me 靠函数顺序保护且零测试（C-8）｜导出审计早提交（失败导出留成功记录，A-N5）｜SQLite 嵌套挂载于 :ro 卷（staging/test 漏修，A-N4）｜i18n 死模块（引用不存在的 json）｜async def 阻塞 I/O 2 处（change_password/upload_file，1 行/个）｜多 worker 指标分片｜prometheus scrape 死 target｜Docker 日志无轮转｜无 SLO/SLI｜部署清单指标名不符｜双 .env 密钥不同｜DEPLOY.md 围栏损坏+库名不一致｜配置矩阵缺失（6 compose 零说明）｜schemas/import_.py 与 i18n.py 覆盖率 0%｜products/stats skip 占位｜`__import__("time")` 反模式｜B13-B15 长尾。

### 🟢 低（9 项）：refresh 7d 偏长、镜像无 digest、根目录残留调试文件、README 空标题/缺步骤 1、monitoring-guide 2024 日期、备份日志、单一 Alembic 迁移无 `alembic check`、api-reference 更新清单自相矛盾、无 API 弃用机制。

---

## 三、🏗️ 评级矩阵变化（07-30 → 07-31）

| 维度 | 评估人 | 07-30 | 07-31 | 说明 |
|------|--------|-------|-------|------|
| 代码-安全 | Cody | B | **C+** ↓ | C-1 架空 cookie 迁移、C-2 新泄漏面、N1/N3/N4 未动 |
| 代码-性能 | Cody | B | **C** ↓ | N5 恶化（双扫+重复计数）、N6 未动 |
| 代码-正确性 | Cody | B+ | **B** ↓ | K2/K3/K5/K6 落地 vs C-1/C-7 功能缺陷 |
| 代码-可维护性 | Cody | B | **B-** ↓ | "复制不删旧"+静默 except 系统性模式 |
| 架构-认证 | Archi | A | **B+** ↓ | A-N1 密钥链（新查明既存问题） |
| 架构-API | Archi | B | **B-** ↓ | B11 一字未改、双错误契约、阻断爆炸半径 |
| 架构-可扩展性 | Archi | C | **C-** ↓ | A-N2 redis 缺失使跨 worker 状态全线失效 |
| 架构-可观测性 | Archi | A- | **B** ↓ | K6 fail-silent、/health 恒 200、三处静默 except |
| 运维-部署 | Rex | C- | **F** ↓↓ | prod compose 语法无效，当前不可部署 |
| 运维-事故响应 | Rex | D | **D-** ↓ | 告警发不出 + 备份 no-op + 恢复手册照抄即断，MTTR 不可估 |
| 运维-安全运维 | Rex | D+ | **C-** ↑ | 端口内网化/部分 `:?` 方向正确 |
| 测试健康度 | Tessa | C+ | **B-** ↑（"绿但脆弱"） | 145 全绿、9.6min→51s；但 6 项修复零守护、K6 反向掩盖、B3 假修复 |
| 文档健康度 | Docu | B- | **C+** ↓ | 旧债 0 清理 + 今日新增 6 缺口，"照着做就出错" |

> 多项下调**不代表代码变差**——是本轮拿到了容器侧证据（.dockerignore、requirements vs venv 分歧、healthcheck 语义、字节级扫描）后修正的判断。真正的新增回归只有 NEW-1、NEW-2、B12、N25 四处。

---

## 四、✅ 行动清单（按优先级排序）

### P0 —— "1 天止血包"（恢复可部署 + 堵住密钥/状态链，代码侧总成本 < 1 天）

| # | 行动 | 具体改动 | 负责角色 | 工作量 |
|---|------|---------|---------|--------|
| 1 | 修 prod compose 语法（NEW-1） | 删 grafana/postgres 两处裸 `ports:` 行；门禁 `docker compose -f prod config -q` | 后端/代码 | 2 分钟 |
| 2 | 封堵镜像密钥链（A-N1） | .dockerignore 加 `.env`+`.env.*`；prod.yml SECRET_KEY 改 `:?`；config.py production 禁 .env 回落；**轮换已暴露的两把密钥** | 后端 | 4 行 + 轮换 |
| 3 | 补 redis 依赖（A-N2） | requirements.txt 加 `redis>=5.0.0`；`except ImportError: pass` 改 error 日志 + prod fail-fast | 后端 | 1 行+ |
| 4 | 激活 cookie 认证（C-1） | `OAuth2PasswordBearer(auto_error=False)` + 判空 | 后端 | 1 行 |
| 5 | Cookie 头脱敏（C-2） | exception_handler redact 集合加 `cookie` | 后端 | 1 行 |
| 6 | SECRET_KEY 守卫收敛（N25/F-05 返工） | prod/staging 改 `:?`，test 保留 fallback | 后端 | 2 行 |
| 7 | 重写 backup.sh + 验收标准（NEW-2/R2） | 重写脚本（产物校验 + 失败 exit 1）；checklist 验收改"产物存在+大小阈值+恢复演练" | Rex 方案 → 代码执行 | 半天 |
| 8 | prod 挂载 alerts.yml（R10） | prometheus volumes 加 1 行；CI `promtool check rules` | 后端+Ops | 1 行 |

### P1 —— 本周内（守护测试 + K6 收尾 + 文档止损）

| # | 行动 | 负责角色 |
|---|------|---------|
| 9 | Tessa P0 补测 3+1：K6 正向守护 3 条、K4 强制 409、B3 真修复（conftest 读 DATABASE_URL）+ CI 镜像内数据布局验证 | 测试 |
| 10 | K6 清尾：删根目录 2 个 json（**保留 data/ 目录**——init_db 还读 dictionary.json、DB 卷挂其下）+ data/README 指针 + lifespan 启动自检 20 行 + /health 暴露加载计数 | 后端 |
| 11 | 重写 backup-strategy.md 恢复章节 + runbooks（stop→exec 改 `docker compose cp`），Rex 命令级复核，然后做一次恢复演练 | Docu+Rex |
| 12 | README/DEPLOY/QUICKSTART 补 SECRET_KEY 前置 + `cp .env.example .env`（D1）；修 PRD 7 处旧路径（D3） | Docu |
| 13 | api-reference 回写（删 3 幽灵端点、补 /users/me、清 3 处"未实现"误标、删 audit-logs 清单项） | Docu |
| 14 | K8 Alertmanager：改 envsubst entrypoint 模板方案；`amtool check-config` 验证 | 后端+Ops |
| 15 | 修 /health 状态码（DB 失败返回 503）+ 修迁移脚本 `postgres_table`（R12） | 后端 |

### P2 —— 两周内（防复发 + 长尾）

| # | 行动 | 负责角色 |
|---|------|---------|
| 16 | CI 门禁 R1-R4（双人独立验证、零误报）：R1 含 `0x08` / R2 孤立 `0x0D`（CR 后非 LF）/ R3 `.sh` 的 LF=0 且 >200B / R4 `.sh` 行长 >300 或 `.md` **代码围栏内**行长 >300 + /openapi.json 快照 diff —— 须二进制读（`open(path,'rb')`），可拦本轮 14 项发现中的 7 项 | Rex 认领 |
| 17 | refresh token 迁 httpOnly cookie 读取（N1-Cody）+ force_password_change 服务端拦截 + register 限流 | 后端 |
| 18 | ADR-008~013 落地（静态数据单一源/密钥信任边界/Redis 硬依赖/统一错误契约/导出阻断作用域/审计覆盖面）；修订 ADR-002/003/005/007 与现实的脱节 | Archi 方案 |
| 19 | users.py 写路径补测（29%→60%+）、K5 Excel 分支修复+测试、清理 data/templates 死副本 | 后端+测试 |
| 20 | Ops 清单执行（TLS 证书、备份 cron、日志轮转、密钥全量显式化）——按 Rex 的 8 步清单顺序，前置依赖 P0 完成 | Ops |

---

## ⚠️ 待完善 / 已知局限

- 仓库无 git，修复归属基于文件 mtime + 实测行为推断，无法用提交记录精确核对。
- Rex 对 NEW-1"启动失败"的判断已实测复现（`docker compose config` 报错），但完整 `up` 链路未在真实服务器验证。
- F-02 的实现落点 Cody（exception_handler.py:36）与 Tessa（全仓 grep 未见）结论不一致——已采信 Cody 的具体文件行证据；Tessa 侧反映的是"无测试可定位"，两者不矛盾但建议补测时先确认落点。
- 本报告的评级下调部分源于新证据（容器侧/字节级），而非代码回退，解读时请区分"新引入回归"（NEW-1/NEW-2/B12/N25）与"新查明既存问题"（A-N1/A-N2/C-1 等）。
- **取证信道 caveat（重要）**：本会话 Bash 工具输出层存在吃换行 / 插入 `bash.exe` 路径残渣的显示层故障，曾导致一条基于裸 stdout 的误报（H14，已撤回）。所有走 raw shell stdout 的结论均已用 Read 工具 / 字节读（`open(path,'rb')`）复核，仅 H14 一条错误——其余结论（含 NEW-1/NEW-2 字节级实证、A-N1/A-N2、C-1、B11 等）均经 Read 或字节读取证，**不受影响**。建议后续审查对所有"文件内容异常/格式损坏"类结论默认用 Read 或字节读复核（即 Rex 的"按取证信道分级重验"做法）。

---

## 📚 数据来源 & 成员产出索引

- **Cody（代码审查师）**：12 项修复验证表 + 13 项 07-30 开放项复核 + C-1~C-8 新发现 + K6 修订增补（VERIFIED→PARTIAL、C-4/C-8）
- **Archi（架构师）**：K6 容器双场景实证（md5/路径/挂载）+ A-N1 密钥链 / A-N2 redis / A-N3 health + B1-B11 复核 + B12 数据双源 + ADR-008~013 建议
- **Rex（SRE）**：NEW-1/NEW-2 实测复现 + N1-N26 运维债 + F-05/K7-K10 就绪度核实 + Ops 8 步执行清单 + CI 门禁认领
- **Tessa（测试专家）**：7 项修复实测探针（K2/K4/K5/K6 全部实际执行验证）+ 145 测试 51s 全绿 + 73% 覆盖率 + "删规则文件仍全绿"独立复现 + B3 假修复揭示 + P0/P1/P2 补测清单
- **Docu（文档师）**：10 项文档债复核（全 UNRESOLVED）+ D1-D6 新缺口 + 字节级损坏根因定案（\b/\r/\n 转义事故，最终确认 **3 个文件**：backup.sh / CHANGELOG.md / DEPLOY.md；第 4 个 database-backup.md 经复核实为误报已撤回）+ README vs api-reference 事实源判定
- 交叉验证：K6 PARTIAL（Archi↔Cody↔Tessa↔Docu 四方一致）、F-05 方向错误（Rex↔Cody↔Archi 三方一致）、backup.sh 静默失效（Rex↔Docu 字节级互证）

---

> 本报告由工程保障团队 AI 协作生成，关键决策请由人类工程负责人复核。评级下调主要反映新掌握的容器侧与字节级证据；6 项硬阻断均为分钟~小时级修复，建议按"1 天止血包"顺序执行后复检。
