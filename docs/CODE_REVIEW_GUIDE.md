# 代码审查标准与流程（Code Review Standard & Process）

> 跨境产品资料中英对照系统 · 工程规范
> 版本：v1.0 · 生效日期：2026-07-30
> 适用范围：所有合入 `main` / `develop` 分支的 Pull Request

---

## 1. 目的与适用范围

本规范用于建立**可重复、可度量、与 CI 联动**的代码审查机制，把"质量参差不齐"变成"每次合并都有基线保障"。

制定本标准的直接动因，是 2026-07-24 综合工程审查暴露出的 **77 项问题（17 CRITICAL / 22 HIGH / 25 MEDIUM / 13 LOW）**。其中大量问题本应在审查环节被拦截：

- 默认管理员凭证硬编码、Token 存 localStorage、CSV 注入防护不完整 —— **安全类**
- 生产环境用 SQLite、无数据库迁移工具、数据模型缺外键 —— **架构类**
- 9 个 API 端点零测试、集成测试目录空置、pytest markers 失效 —— **测试类**
- API 文档缺 11 端点、无全局异常处理器 —— **文档/健壮性类**

本标准的价值：**让同样的问题不再二次发生**。每一条审查清单都对应一类已知缺陷。

**适用范围**：后端（Python/FastAPI/SQLAlchemy）、前端（React/TypeScript）、部署与监控配置（Docker/CI/monitoring）、以及影响 API 契约或安全模型的任何变更。纯文档类 PR 走轻量通道（见 §6 步骤 1）。

---

## 2. 角色与职责

| 角色 | 职责 | 谁来担任 |
|------|------|----------|
| **Author（提交者）** | 保证 PR 自测通过、填写模板、响应评审意见、修复后重新请求审查 | 任何贡献者 |
| **Reviewer（审查者）** | 按本清单逐条审查，给出明确结论（批准/要求修改/驳回），对正确性负同行责任 | 至少 1 名，安全敏感路径需 2 名（见 §10） |
| **Maintainer（维护者）** | 最终裁决争议、确认合并条件达成、执行 squash 合并 | 仓库 owner / 技术负责人 |
| **Security Reviewer（安全审查者）** | 对 `auth`、`security`、`export`、`db` 等敏感路径做专项安全评审 | 指定的安全负责人 |

**审查者分配**：默认由 CODEOWNERS 自动路由（见 §10）；若无人响应，Author 可在团队群@对应负责人，最长不超过 SLA（§6）。

---

## 3. 严重级别定义

审查意见一律使用以下四级标记，与既有审查体系（🔴 CRITICAL / 🟠 HIGH / 🟡 MEDIUM / 🟢 LOW）对齐：

| 标记 | 名称 | 含义 | 合并影响 |
|------|------|------|----------|
| 🔴 | **Blocker / CRITICAL** | 安全漏洞、数据丢失/损坏风险、破坏 API 契约、缺关键错误处理的路径、硬编码密钥/凭证 | **必须修复，禁止合并** |
| 🟠 | **Major / HIGH** | 缺输入校验、逻辑含糊易错、重要行为缺测试、性能 N+1、明显重复代码应抽取 | **应当修复；除非有书面 waiver，否则阻塞合并** |
| 🟡 | **Minor / MEDIUM** | 命名不佳、注释缺失、可选方案、边界场景未覆盖 | 建议修复；可开 issue 跟踪，**不阻塞合并** |
| 🟢 | **Nit / LOW** | 风格细节、无关紧要的优化 | 可选；鼓励顺手修 |

> **waiver 机制**：仅 Major 级可在 Reviewer + Maintainer 双签下推迟，须登记 issue 并标注 `tech-debt` 标签与 fix 期限。Blocker 不可 waiver。

---

## 4. 合并准入门槛（Definition of Done / Merge Gate）

一个 PR 在满足**全部**以下条件前不得合并：

1. ✅ **CI 全绿**：`test-backend` / `test-frontend` / `security-check` / `docker-build` 全部通过（见 §9）。
2. ✅ **无未解决的 🔴 Blocker**；🟠 Major 全部处理或已 waiver。
3. ✅ **覆盖率不下降**：新增代码行覆盖率 ≥ 80%；PR 不得使整体覆盖率下滑超过 1%（门禁由 CI 强制，见 §9.2）。
4. ✅ **至少 1 个 Approval**；安全敏感路径（§10）需 2 个 Approval（含 1 名 Security Reviewer）。
5. ✅ **Author 已完成自检清单**（PR 模板中勾选）。
6. ✅ **API 契约变更须同步文档**：新增/修改/删除端点必须更新 OpenAPI 文档与 `docs/api-reference.md`。
7. ✅ **PR 体积可控**：单 PR 建议 ≤ 400 行变更（不含生成代码/lockfile）；超大体量必须拆分为多 PR。
8. ✅ **关联 Issue**：修复类 PR 标题或正文 `Closes #xxx`。

---

## 5. 审查流程（7 步）

```
① Author 自测 → ② 开 PR 填模板 → ③ 自动路由 Reviewer
        ↓                                        ↓
⑦ 合并+关 issue                         ④ Reviewer 评审(≤SLA)
        ↓                                        ↓
⑥ Maintainer 合并                   ⑤ Author 修复→重请审查(迭代)
```

| 步骤 | 动作 | 产出 / 门槛 |
|------|------|------|
| **1. 自测** | Author 本地跑 lint / type / test / secret-scan，完成 PR 模板自检清单 | 本地无 🔴；无 `print`/调试断点；无密钥 |
| **2. 开 PR** | 基于 `feature/*` 或 `fix/*` 分支，填模板，关联 issue | 描述清晰、含测试证据、标注变更类型 |
| **3. 路由** | CODEOWNERS 自动指派 Reviewer；安全路径追加 Security Reviewer | 1~2 名 Reviewer 到位 |
| **4. 评审** | Reviewer 按 §7 清单逐条检查，写明结论与级别 | 结论：APPROVED / APPROVED_WITH_NITS / CHANGES_REQUESTED / REJECTED |
| **5. 迭代** | Author 处理意见，回答疑问，修复后 `@reviewer` 重新请求审查 | 每次 push 自动触发 CI；对话线程收敛 |
| **6. 合并** | Maintainer 确认 §4 全部满足，squash 合并，commit message 遵循 Conventional Commits | 历史线性、可追溯到 issue |
| **7. 收尾** | 关闭关联 issue，更新 CHANGELOG（如适用），删除预览分支 | issue 状态一致 |

**SLA（审查响应时间）**

| PR 类型 | 首次评审响应 | 合并前终审 |
|---------|--------------|------------|
| 紧急修复（hotfix/security） | 4 小时 | 24 小时 |
| 常规功能 / 缺陷 | 1 个工作日 | 3 个工作日 |
| 文档 / 配置 | 2 个工作日 | 5 个工作日 |

> 超时未响应由 Maintainer 介入改派，避免 PR 积压。

---

## 6. 审查清单（核心）

Reviewer 必须逐维度核对。带 ★ 的为本项目历史专项（源自 77 项审查），优先级更高。

### 6.1 正确性（Correctness）
- [ ] 逻辑是否符合需求/Issue 描述？边界条件（空、超大、负数、特殊字符）是否处理？
- [ ] 是否有未捕获的异常路径会导致请求 500？是否有全局异常处理器兜底（§7.6）？
- [ ] 并发 / 竞态：共享状态（计数器、缓存）是否线程安全？
- [ ] 分页、过滤、排序是否与文档一致？分页是否有上限保护（防 `limit=9999999`）？
- [ ] 时区、编码、JSON 序列化是否一致（中英文混排场景）？

### 6.2 安全性（Security）★ 重点
- [ ] ★ **认证/授权**：受保护端点是否都有鉴权装饰器？RBAC 角色（admin/editor/reviewer/viewer）校验是否正确？无越权（如 A 用户改 B 用户数据）？
- [ ] ★ **Token 存储**：前端**禁止**将 Token 存 `localStorage`（ADR-007），须用 `httpOnly` + `Secure` + `SameSite` Cookie。
- [ ] ★ **Token 生命周期**：Access Token 短效（15–30min）+ Redis 黑名单可即时撤销（ADR-005）；Refresh Token 不得出现在 URL query（防日志泄露）。
- [ ] ★ **SQL / 注入**：后端一律用 SQLAlchemy ORM 或参数化查询，**禁止**字符串拼接 SQL；前端无拼接进 `innerHTML`（防 XSS）。
- [ ] ★ **CSV 注入**：导出单元格必须对 `= + - @` 前缀及换行做转义（ADR-004 的 `sanitize_csv_cell`）。
- [ ] ★ **密钥/凭证**：无硬编码密码、API Key、SECRET_KEY；一律走环境变量 / 密钥管理；`.env` 不入库（已在 `.gitignore`）。
- [ ] ★ **输入校验**：所有外部输入经 Pydantic 模型校验；文件上传校验类型/大小；无 `eval`/`exec` 执行外部输入。
- [ ] 速率限制：登录、导出、导入等敏感接口是否有速率限制？
- [ ] CORS：是否校验来源白名单，而非 `*`？
- [ ] 依赖安全：`safety` / `npm audit` 无新增高危漏洞。

### 6.3 性能（Performance）
- [ ] 是否存在 N+1 查询？ORM 关联是否用 `joinedload` / `selectinload`？
- [ ] 大数据集是否分页 / 流式处理？导出大文件是否后台任务化？
- [ ] 是否有不必要的同步阻塞 I/O 卡在 async 路径？
- [ ] 缓存使用是否合理（命中率、失效策略、Redis 黑名单一致性）？

### 6.4 可维护性（Maintainability）
- [ ] 命名是否表意？函数/模块是否单一职责、可测试？
- [ ] 是否有明显重复代码应抽取（如多处相同的 CSV 转义、审计写入）？
- [ ] 是否有魔法数字 / 硬编码配置应提升到配置层？
- [ ] 错误处理是否清晰（无裸 `except:`、无吞异常）？日志级别与结构化是否合理？
- [ ] ★ **迁移**：数据库结构变更是否走 Alembic 迁移（**禁止**依赖 `create_all` 自动建表）？迁移脚本是否有 up/down、可在 CI 跑通？

### 6.5 测试（Testing）
- [ ] 新增逻辑是否有单元测试？断言具体、独立、可重复？
- [ ] 重要行为（鉴权、导出阻断、一致性检测、导入 update 模式）是否有覆盖？
- [ ] 错误路径是否测试（过期 token、黑名单 token、禁用用户、500）？
- [ ] 测试是否带正确 pytest marker（`unit`/`integration`/`security`），CI 过滤有效？
- [ ] 是否新增了"零覆盖端点"的测试（参考 77 项审查清单：/health、/metrics、/auth/logout-all、/users/* 等）？

### 6.6 API 与文档契约（Contract）
- [ ] ★ **API 文档同步**：端点增删改必须更新 OpenAPI（FastAPI 自动）与 `docs/api-reference.md`，不得再出现"缺 11 端点"的情况。
- [ ] 是否有 API 版本策略？破坏性变更是否向后兼容或走 `/v2`？
- [ ] 错误消息是否经 i18n 抽象层？后端不直接混排中英文裸串（除非内部错误）。

### 6.7 本项目历史坑位专项（源自 77 项审查）★
以下任一项回归即判 🔴 Blocker：

| 历史问题（原编号） | 现在必须做到的 |
|--------------------|----------------|
| 默认管理员凭证硬编码（#1） | 凭证从环境变量注入，首次登录强制改密 |
| Token 存 localStorage（#5） | httpOnly Secure Cookie（ADR-007） |
| 无审计日志写入（#6） | 关键 CRUD 经中间件/装饰器写审计日志（ADR-002） |
| 导出缺一致性阻断（#7） | 导出前跑一致性检测，ERROR 级阻断（ADR-003） |
| 生产用 SQLite（#8） | 生产用 PostgreSQL（ADR-006），不回退 SQLite |
| Access Token 不可撤销（#10） | Redis 黑名单 + 短效 token（ADR-005） |
| 数据模型缺外键（#14） | 外键 + `ondelete` 行为 |
| 无全局异常处理器（#31） | 统一异常拦截，不泄露栈 |
| CSV 注入防护不全（#18） | `sanitize_csv_cell` 覆盖 `\n` 等全部危险字符 |
| 无数据库迁移工具（#22） | Alembic 迁移，禁止 `create_all` 增量变更 |

---

## 7. 评论规范（如何写评审意见）

1. **标注级别**：每条意见以 `🔴/🟠/🟡/🟢` 开头，并说明是否阻塞（`[blocking]` / `[non-blocking]`）。
2. **具体 + 解释原因 + 给建议**（而非命令）：
   - ✅ "🔴 [blocking] 安全：第 42 行用户 `name` 直接拼进 SQL。攻击者可用 `' OR 1=1 --` 绕过。建议改用 ORM 参数化：`session.query(User).filter(User.name == name)`。"
   - ❌ "这里有安全问题，改一下。"
3. **区分阻塞与非阻塞**：非阻塞的意见不要挡合并，可标注 `[non-blocking]` 并建议后续 issue。
4. **先肯定后建议**：对巧妙的实现、干净的抽象主动点赞（"💚 这个分页上限保护写得好"），建设性反馈更易被接受。
5. **疑问用提问**：意图不明时先问"这里用 query 传 token 是有意为之吗？ADR-005 建议放 body。"，避免误判。
6. **结论明确**：评审结束时给出总评——`APPROVED` / `APPROVED_WITH_NITS` / `CHANGES_REQUESTED` / `REJECTED`，并简述理由。

---

## 8. 与 CI 流水线的衔接

当前 `.github/workflows/ci.yml` 已含 `flake8` / `mypy` / `pytest+cov` / `eslint` / `typecheck` / `safety` / `npm audit` / `docker build`。审查门禁与 CI 的映射：

| 审查维度 | CI 对应 Job | 失败即阻断合并 |
|----------|-------------|----------------|
| 风格（PEP8/ESLint） | `flake8` / `npm run lint` | 是 |
| 类型安全 | `mypy` / `npm run typecheck` | 是 |
| 正确性 / 测试 | `pytest` / `npm run test` | 是 |
| 依赖漏洞 | `safety` / `npm audit` | 是（新增高危） |
| 可构建性 | `docker-build` | 是 |

### 8.1 建议新增的 CI 门禁（补齐 SAST 与覆盖率）
为把 §6.2 / §6.5 的专项在合并前自动卡住，建议在 CI 增加：

```yaml
  sast-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install bandit
      - run: cd backend && bandit -r app/ -ll -ii   # 扫 SQLi/XSS/硬编码密钥

  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2          # 防密钥/凭证入库

  coverage-gate:
    # 在 test-backend / test-frontend 之后
    - run: |
        # 断言覆盖率不下降；新代码行覆盖 >= 80%
        diff-cover coverage.xml --fail-under=80
```

> 引入 `pyproject.toml`（或 `pytest.ini`）统一配置 pytest markers 与覆盖率阈值，解决 77 项审查中 #9 / #50（markers 缺失、无配置文件）的问题。

---

## 9. 评审路由（CODEOWNERS）

已新增 `.github/CODEOWNERS`：按目录自动指派 Reviewer，安全敏感路径（auth/security/export/db）标注需双审批（1 名普通 Reviewer + 1 名 Security Reviewer）。Reviewer 长期空缺时由 Maintainer 兜底。

路由原则：
- `backend/app/auth/**`、`backend/app/security/**`、`backend/app/db/**` → 安全/后端负责人（双审批）
- `backend/app/export/**`、`backend/app/import/**` → 后端负责人（CSV 注入专项）
- `frontend/**` → 前端负责人
- `docs/**` → 文档负责人
- `*.yml`、`deploy/**`、`monitoring/**`、`docker-compose*.yml` → DevOps 负责人

---

## 10. 渐进推行路线

不要一次性全量强推，按团队节奏落地：

| 阶段 | 内容 | 周期 | 退出标准 |
|------|------|------|----------|
| **P1 立规** | 发布本指南 + 新 PR 模板 + CODEOWNERS；团队宣贯 | 本周 | 新 PR 100% 走模板与路由 |
| **P2 加门禁** | CI 接入 `bandit` + `gitleaks` + 覆盖率门禁；补 `pyproject.toml` | 1–2 周 | SAST 全绿、覆盖率门禁生效 |
| **P3 双审批** | 安全敏感路径强制执行 2-Approval | 2–3 周 | 安全 PR 均有 Security Reviewer 签字 |
| **P4 提质** | 覆盖率门槛提升至新代码 ≥ 85%；月度审查效能复盘（时长/返工率） | 持续 | 月度复盘机制运转 |

---

## 11. 附录：评审意见范例

**范例 A（🔴 Blocker，安全）**
```
🔴 [blocking] 安全 / SQL 注入风险 — backend/app/products/service.py:88
User 输入 `keyword` 通过 f-string 拼进 raw SQL。攻击者可注入 `'); DROP TABLE products;--`。
建议：改用 ORM 参数化
  products = db.query(Product).filter(Product.name.ilike(f"%{keyword}%")).all()
```

**范例 B（🟠 Major，测试）**
```
🟠 [blocking] 测试 / 重要行为未覆盖 — backend/app/export/router.py
新增的"ERROR 级一致性问题阻断导出"逻辑（ADR-003）没有任何测试。建议补一个用例：
构造一条 ERROR 级不一致记录，断言导出返回 422 且未生成文件。
```

**范例 C（🟢 Nit，风格）**
```
🟢 [non-blocking] 可维护性
函数 `build_template` 中 `col_count = 12` 是魔法数字，建议提取为常量 `MAX_COLUMNS` 便于后续扩平台。
```

**范例 D（💚 肯定）**
```
💚 这个导出单元格转义函数 `sanitize_csv_cell` 对 `= + - @` 和换行的覆盖很完整，
正好落实了 ADR-004，点个赞。
```

---

> 本规范与 `CONTRIBUTING.md`、`docs/api-reference.md`、各 ADR 配套使用。任何修订须经 Maintainer 评审后生效，并在文首更新版本与日期。
