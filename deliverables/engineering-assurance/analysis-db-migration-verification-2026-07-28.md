
# 文档三：数据库迁移状态验证分析说明

**日期**：2026-07-28
**工作流**：综合工程审查（后续专项分析 · 文档三）
**参与成员**：Cody（代码审查师）
**关联审计**：comprehensive-audit-404-route-security-2026-07-28.md

---

## 📌 TL;DR（执行摘要）

- **数据库迁移当前处于"不可信的半启用状态"**：`alembic.ini`、`alembic/env.py`、`alembic/versions/001_initial_migration.py` 均存在，但（1）运行时 `docker-entrypoint.sh` 走 `init_db.py` 的 `Base.metadata.create_all`，**从未执行 `alembic upgrade`**；（2）现存 `001` 迁移与当前 ORM 模型**表名/主键类型/字段全面脱节**；（3）DB 无 `alembic_version` 表。
- 这比"完全没有 Alembic"更危险——会让人误以为有版本化迁移。
- **验证结论直接判定 FAIL**。必须二选一落地单一真相源（推荐：以模型为基准重生迁移并接入 entrypoint）。

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🔴 不通过（迁移不可信） |
| Alembic 配置 | ✅ ini/env.py/versions 均在 |
| 运行时接管 | ❌ 从未 `alembic upgrade`，走 `create_all` |
| 迁移与模型一致性 | ❌ 严重脱节（幽灵迁移） |
| 关键行动项 | 4 条（单一真相源 + 重生迁移 + 接入 entrypoint + 验证） |
| 建议下一步 | 方案 A：删旧迁移 → autogenerate 重生 → 接 entrypoint → staging 验证 |

---

## 1. 验证目的与 Alembic 核心依赖

**目的**：确认"代码中的 ORM 模型定义"与"数据库中实际落地的表结构"完全一致，且存在可追溯、可回滚、可重复的版本化迁移机制——避免"上线后某张表/某列不存在导致 500"。

Alembic 正常工作依赖 **四个要素同时成立**：
1. `alembic.ini`（配置入口，含 `script_location`）
2. `alembic/` 目录下的 `env.py`（建立 engine 连接、提供 `target_metadata`）
3. `alembic/versions/` 下的迁移脚本（含 `upgrade()`/`downgrade()`）
4. 数据库中的 `alembic_version` 表（记录当前已应用 revision）

---

## 2. 当前仓库真实状态（已据实核对）

| 要素 | 实际状态 | 证据 |
|---|---|---|
| `alembic.ini` | ✅ 存在 | `backend/alembic.ini` |
| `alembic/env.py` | ✅ 存在 | 已正确挂载 `app.database.Base` 与模型 |
| `alembic/versions/001_initial_migration.py` | ✅ 存在 | 内含初始迁移 |
| `alembic_version` 表（DB） | ❌ 不存在 | 运行时只跑 `python init_db.py`（create_all），从未 `alembic upgrade` |
| 运行时 schema 来源 | ✅ create_all | `init_db.py:32` `Base.metadata.create_all(bind=engine)`；`docker-entrypoint.sh` |

### 更严重的问题——迁移脚本与模型严重不一致（核心发现）

把 `versions/001_initial_migration.py` 与 `backend/app/models/*.py` 逐一比对：

| 维度 | 迁移 `001` 定义 | 当前 ORM 模型 | 后果 |
|---|---|---|---|
| 用户表名 | `user_profiles` | `users`（`user.py:__tablename__="users"`） | 表名对不上 |
| 术语表名 | `terms` | `term_dictionary`（`term.py:__tablename__="term_dictionary"`） | 表名对不上 |
| 主键类型 | `sa.Integer()` 自增整型 | `String(36)` UUID | 整型 PK vs UUID 字符串 PK，不兼容 |
| 外键 `created_by` | `sa.Integer()` | `String(36)` FK→`users.id` | 类型不匹配 |
| 缺失表 | 无 | `refresh_token_blacklist`（token_blacklist.py） | 迁移不建该表 |
| 用户表缺列 | 无 `force_password_change` | 有 `force_password_change`（`user.py:16`） | 缺列 |
| 产品表缺列 | 仅有子集 | 缺 `extra_fields`(JSON)、`consistency_status`、`consistency_issues`(JSON)、`is_deleted`、`deleted_at`、`color_*`、`material_*`、`size`、`weight*`、`dimension_*`、`origin`、`model_number` 等多列 | 大量缺列；`price` 迁移 `Float` vs 模型 `Numeric(12,2)`，`currency` 长度 `10` vs `3` |
| 术语表列名 | `term_zh`/`term_en`/`description` | `zh`/`en`/`category`/`note`/`synonyms`(JSON)/`platform_*`/`is_builtin` | 列名结构全错 |
| 审计表 | 有 `user_agent` | 无 `user_agent`（`audit.py`） | 迁移多出列 |

**结论**：`001` 迁移是**陈旧的、与现状脱节的"幽灵迁移"**——既不等于当前模型，也不等于 `create_all` 实际产出的库。若误执行 `alembic upgrade head`，会建出应用根本不认的表结构，造成数据层断裂。

**附加风险（需验证）**：`init_db.py:9` 仅 `from app.models import UserProfile, Product, TermDictionary, AuditLog`，未导入 `RefreshTokenBlacklist`；`app/models/__init__.py` 也未导出它。`create_all` 只建"已加载到内存的模型类"对应的表——若令牌黑名单模型未在这条代码路径上被间接导入，则新库的 `refresh_token_blacklist` 表可能缺失，令牌撤销逻辑会运行时报错。

---

## 3. 迁移版本与 DB schema 一致性校验方法

1. **版本一致性（DB head vs code head）**：
   - `alembic current` → 读 DB 的 `alembic_version`，得"已应用 revision"。
   - `alembic heads` → 读 `versions/`，得"代码最新 revision"。
   - 两者相等 ⇒ 版本一致。
2. **结构一致性（模型 DDL vs DB DDL）**：
   - `alembic check`（Alembic 1.x 起支持）或 `alembic autogenerate -m "diff"` → 对比 `target_metadata`（模型）与数据库实际 schema。
   - `alembic revision --autogenerate --sql` 看生成增量 DDL 是否为空。
3. **模型 DDL 与库对拍**：用 `scripts/postgresql_migration.py` 的 `_verify_migration`（按表 count 校验）思路做结构对拍。
4. **注意陷阱**：因 DB 当前由 `create_all` 建立、无 `alembic_version`，`alembic current` 会直接报错（"找不到 alembic_version 表"），这本身就是"Alembic 从未接管"的有力证据。

---

## 4. 执行所需环境要素

- 数据库连接串：`DATABASE_URL`（见 `docker-compose.yml:13`，默认 `sqlite:///./data/runtime/bilingual_cms.db`，生产用 PostgreSQL）。
- `alembic.ini`：✅ 存在。
- 迁移目录 `alembic/`（env.py + versions/）：✅ 存在（但内容 stale）。
- `alembic_version` 表：❌ 不存在（需先 `alembic upgrade` 才会建）。
- Python 环境：✅ `backend/venv/` 已装 SQLAlchemy + Alembic。
- 网络：首次 `pip install`/拉镜像需联网。

---

## 5. 当前缺失项与搭建步骤

**缺失项**：① DB 中没有 `alembic_version`（Alembic 未接管）；② 现有 `001` 迁移与模型严重不一致，不可信；③ 运行时未接入 `alembic upgrade`。

**推荐搭建路径（二选一，关键是"单一真相源"，不要混用）**：

> **方案 A（推荐：正式采用 Alembic 作为唯一 schema 管理器）**
> 1. 备份现有数据库。
> 2. 删除或重命名错误的 `versions/001_initial_migration.py`（避免污染）。
> 3. 从**当前模型**重新生成初始迁移：`cd backend && set DATABASE_URL=<真实库> && alembic revision --autogenerate -m "init_from_models"`（`env.py` 已正确读取 `DATABASE_URL` 并挂载 `Base.metadata`）。
> 4. 人工核对生成的 `upgrade()` 是否与 `users`/`products`/`term_dictionary`/`audit_logs`/`refresh_token_blacklist` 五张表及全部列一致（特别核对 UUID 主键、JSON 列、FK 类型）。
> 5. 让 `docker-entrypoint.sh` 用 `alembic upgrade head` 替代 `init_db.py` 中的 `create_all`（保留字典导入等数据初始化逻辑，但**表结构交给 Alembic**）。
> 6. 在 staging 跑通后，再对生产库 `alembic upgrade head`。

> **方案 B（若坚持用 create_all，则彻底移除 Alembic 以避免误导）**
> 1. 删除 `backend/alembic/` 目录与 `backend/alembic.ini`。
> 2. 从 `requirements.txt` 移除 `alembic`（或保留但明确不用于迁移）。
> 3. 在 `init_db.py` 显式 `import app.models.token_blacklist` 确保所有表被 `create_all` 覆盖（修复黑名单表可能缺失的风险）。
> 4. 接受"无版本化迁移"的代价：未来 schema 变更只能手工 ALTER 或重建。

---

## 6. 验证通过 / 失败标准

- **PASS（方案 A）**：`alembic current` == `alembic heads`，且 `alembic check`/`autogenerate` 产出**零差异**；应用能正常读写全部五张表；`refresh_token_blacklist` 存在。
- **FAIL（任一即判失败）**：
  - `alembic current` 报错（无 `alembic_version`）或版本落后 `heads`；
  - `autogenerate` 显示缺表/缺列/类型不符/表名不符（`user_profiles` vs `users`、`terms` vs `term_dictionary`、整型 PK vs UUID 等）；
  - 应用运行时报 `relation "users"/"term_dictionary"/"refresh_token_blacklist" does not exist`。
- **当前状态直接判定：FAIL**——Alembic 未接管 + 现存迁移与模型不一致 + 运行时走 create_all。

---

## 7. 异常处理预案（出现版本漂移 / 差异时）

1. **先备份**：任何 `alembic upgrade` / `autogenerate` 前，`pg_dump`（PostgreSQL）或拷贝 `.db`（SQLite）做全量备份，保留可回滚快照。
2. **不要盲升生产**：永远先在 staging 用 `alembic upgrade head` 验证，确认零数据丢失、应用读写正常后再动生产。
3. **漂移修复**：若 `autogenerate` 显示差异，先判断"模型领先 DB"还是"DB 领先模型"。前者生成迁移并评审；后者先搞清楚 DB 为何领先（是否手改），再补迁移或回退。
4. **数据型变更谨慎**：重命名列/改类型（如本例 `Integer`→`String(36)` 主键、`Float`→`Numeric`）属破坏性变更，`autogenerate` 常"先删后建"导致数据丢失——必须手写迁移用 `ALTER` + 数据回填，禁止自动生成的破坏性 DDL 直接上生产。
5. **回滚**：保留每版 `downgrade()`；出问题时 `alembic downgrade -1` 回退，并立刻从备份恢复核对。
6. **权限与审计**：迁移执行账号最小化；执行动作写入 `audit_logs`（本系统已有审计模型），满足合规追溯。

---

## 8. 结论

数据库迁移当前处于**不可信的半启用状态**：配置文件与目录都在，但（1）运行时根本没用 Alembic，而是 `create_all`；（2）现存 `001` 迁移与真实模型表名/主键/字段全面脱节；（3）DB 无 `alembic_version`。这比"完全没有 Alembic"更危险，因为它会让人误以为有版本化迁移。**必须二选一落地单一真相源**（推荐方案 A：以模型为基准重生迁移并接入 entrypoint），在此之前，凡是涉及 schema 的发布都应视为高风险。

---

## ✅ 行动清单（按优先级排序）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 1 | 删除/重命名错误的 `versions/001_initial_migration.py` | 后端 | P0 | 0.5d |
| 2 | 从当前模型 `alembic revision --autogenerate` 重生初始迁移并人工核对 | 后端 | P0 | 1d |
| 3 | `docker-entrypoint.sh` 用 `alembic upgrade head` 替代 `create_all`（保留数据初始化） | 后端/SRE | P0 | 0.5d |
| 4 | 显式导入 `token_blacklist` 模型确保 `refresh_token_blacklist` 表被覆盖 | 后端 | P1 | 0.5d |
| 5 | staging 跑通 `alembic upgrade head` + 应用读写验证后再动生产 | SRE | P1 | 1d |

---

## ⚠️ 待完善 / 已知局限

- 本次为状态核查与方案分析，未实际执行 `alembic` 命令（避免在未备份的生产库上操作）。
- `refresh_token_blacklist` 在 `init_db.py` 导入链上是否真正被加载，需运行时验证（见第 2 节附加风险）。
- 方案 A 重生迁移时，`autogenerate` 对 JSON 列、UUID 主键的识别需人工核对，可能存在需手调的 DDL。

---

## 📚 数据来源 & 成员产出索引

- Cody（代码审查师）原始产出：数据库迁移状态验证分析（Alembic 四要素核查、001 迁移与模型脱节比对表、一致性校验方法、方案 A/B 搭建步骤、通过/失败标准、异常处理预案）。基于对 `backend/alembic.ini`、`backend/alembic/env.py`、`backend/alembic/versions/001_initial_migration.py`、`backend/init_db.py`、`backend/app/models/*.py`、`docker-compose.yml` 的逐文件核查。

---

> 本文档由工程保障团队 AI 协作生成（甄宇航·工程督导 汇编），关键决策请由人类工程负责人复核。
