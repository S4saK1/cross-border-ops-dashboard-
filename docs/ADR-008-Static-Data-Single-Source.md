# ADR-008: 静态数据单一来源
**状态:** Accepted
**日期:** 2026-07-31

## 背景

一致性检测规则和同义词数据存在**两处位置**，形成"分裂脑"问题：

| 位置 | 内容 | 状态 |
|------|------|------|
| `data/` (仓库根目录) | `dictionary.json` (旧版词典) | **死数据** — 不再被任何代码引用 |
| `backend/app/data/` (后端源码目录) | `consistency-rules.json`, `synonyms.json`, `export_templates.json`, `extra_fields_schema.json` | **活跃使用** — 被 `consistency.py`、`main.py`、`export.py` 引用 |

### Docker 卷挂载加剧问题

Docker Compose 配置 (`docker-compose.yml`, `docker-compose.prod.yml`, `docker-compose.staging.yml`) 均包含：

```yaml
volumes:
  - ./data:/app/data:ro              # 挂载仓库根目录 data/ 到容器 /app/data/
  - cms-data:/app/data/runtime       # 运行时数据卷
```

同时，`ConsistencyEngine` 使用 `__file__` 相对路径加载数据：

```python
# backend/app/core/consistency.py
rules_path = os.path.join(os.path.dirname(__file__), "..", "data", "consistency-rules.json")
# 解析为 /app/app/data/consistency-rules.json
```

这导致：
- 应用从 `/app/app/data/` (镜像内 COPY 的数据) 读取一致性规则
- 卷挂载到 `/app/data/` (仓库根目录 `data/`) 完全未被一致性检测器使用
- 两个 `data/` 目录内容不同步，运维人员可能误修改错误的位置

此问题导致了 B12 号 Bug：修改 `data/` 下文件后一致性检测行为未变化。

## 选项分析

### 选项 A: 统一到仓库根目录 `data/`
| 维度 | 评估 |
|------|------|
| 复杂度 | Low — 修改加载路径和 Docker 挂载 |
| 成本 | 低 — 仅需移动文件并调整路径 |
| 可维护性 | 中 — Docker 卷方便运维修改，但容器内路径不一致 |

### 选项 B: 统一到 `backend/app/data/`（源码内）
| 维度 | 评估 |
|------|------|
| 复杂度 | Low — 移除 Docker 卷挂载即可 |
| 成本 | 低 — 数据随代码版本管理 |
| 可维护性 | 高 — 数据与代码同源，版本一致 |

### 选项 C: 数据库存储
| 维度 | 评估 |
|------|------|
| 复杂度 | High — 需要新的 CRUD API 和管理界面 |
| 成本 | 高 — 需要数据库迁移、管理界面开发 |
| 可维护性 | 高 — 运行时动态更新，但失去版本控制 |

## 决策

选择**选项 B: 统一到 `backend/app/data/`**。

### 理由
1. **版本控制一致性**：静态配置数据与代码一起版本管理，不会出现数据与代码不匹配
2. **消除分裂脑**：移除 `data/` 目录的 Docker 卷挂载（`./data:/app/data:ro`），删除仓库根目录 `data/` 下的死数据
3. **部署简化**：不需要额外卷挂载，`COPY . .` 自动包含所有数据文件
4. **`__file__` 相对路径稳定性**：无论容器内工作目录如何变化，路径始终正确

### 实施要点
1. 删除仓库根目录 `data/dictionary.json`（死数据）
2. Docker Compose 卷配置中移除 `./data:/app/data:ro` 挂载
3. 保留 `cms-data:/app/data/runtime` 用于运行时 SQLite 数据库存储
4. 所有静态数据加载使用 `os.path.join(os.path.dirname(__file__), "..", "data", ...)` 模式

## 影响

### 变容易
- 数据与代码版本同步，消除配置漂移
- 部署时无需额外卷挂载配置
- 数据更新通过代码审查流程，有变更记录

### 变困难
- 运维人员不能直接修改数据文件（需走代码变更流程）
- 数据文件变更需要重新构建镜像

### 需要重新审视
- Docker Compose 卷挂载配置（所有环境）
- `data/` 目录的用途定义：**仅用于运行时数据库存储（SQLite）**
