# ADR-013: 审计日志全覆盖
**状态:** Accepted
**日期:** 2026-07-31

## 背景

审计日志是合规追溯和安全审计的基础设施。当前审计覆盖率不足：

| 模块 | 审计日志状态 | 问题 |
|------|-------------|------|
| `auth.py` (auth) | ✅ 已覆盖 | 登录、登出、密码修改均已记录 |
| `import_.py` (导入) | ❌ 零覆盖 | `write_audit_log` 调用次数 = 0 |
| `export.py` (导出) | ⚠️ 有缺陷 | 仅在**成功导出**后记录；失败时不记录 |
| `terms.py` (术语管理) | ❌ 未知 | 需检查 CRUD 操作的审计覆盖 |
| `products.py` (产品管理) | ❌ 未知 | 需检查 CRUD 操作的审计覆盖 |

### 导出审计的具体缺陷

`export.py` 第 59-68 行：

```python
# 审计日志在提交响应之前写入
write_audit_log(
    db=db, actor_id=current_user.id, action='export_csv',
    subject_type='product', subject_id=','.join(product_ids),
    after={"platform": platform, "product_count": len(products), "product_ids": product_ids},
)
db.commit()  # 第 68 行：审计已提交

# 但后续仍有失败可能（模板缺失等）
template = _templates.get(platform)
if not template:
    raise HTTPException(status_code=400, ...)  # 审计已写但请求失败！
```

这导致：失败导出在审计日志中记录为"成功"——因为审计在响应前已提交。

## 选项分析

### 选项 A: 在响应返回后异步写入审计
| 维度 | 评估 |
|------|------|
| 复杂度 | Medium — 需后台任务/队列 |
| 准确性 | 中 — 异步写入可能丢失（进程崩溃） |
| 性能 | 好 — 不阻塞响应 |

### 选项 B: 在响应成功返回前同步写入（事务内）
| 维度 | 评估 |
|------|------|
| 复杂度 | Low — 利用现有 `write_audit_log` |
| 准确性 | 高 — 审计与数据操作在同一事务中 |
| 性能 | 可接受 — 审计写入开销极小 |

### 选项 C: 两步审计（先写 pending，成功后标记 complete）
| 维度 | 评估 |
|------|------|
| 复杂度 | High — 需状态机管理 |
| 准确性 | 最高 — 精确区分进行中/成功/失败 |
| 存储 | 翻倍 — 每条操作两条记录 |

## 决策

选择**选项 B: 同步事务内写入，覆盖所有变更操作**。

### 理由
1. **事务一致性**：审计日志和数据变更在同一数据库事务中，保证原子性
2. **覆盖所有变更**：导入、导出、CRUD 操作的审计日志在 `db.commit()` 前写入
3. **修正导出时序**：审计日志写入移至响应生成成功之后、`StreamingResponse` 返回之前（或使用后台任务在确认成功后写入）
4. **简单可靠**：复用现有 `write_audit_log` 函数，不需要新基础设施

### 实施要点

#### 导入审计规范

```python
# import_.py execute_import 中
import hashlib

file_hash = hashlib.sha256(content).hexdigest()
# ... 执行导入 ...
db.flush()  # 先刷新数据变更

write_audit_log(
    db=db,
    actor_id=current_user.id,
    action='import_execute',
    subject_type='product',
    subject_id=file_hash,  # 使用文件哈希作为 subject_id
    after={
        "mode": mode,
        "file_id": file_id,
        "attempted": len(all_rows),
        "succeeded": success_count,
        "skipped": skip_count,
        "failed": error_count,
        "errors": errors[:50],  # 详细错误（最多50条）
    },
)
db.commit()  # 数据 + 审计一起提交
```

#### 导出审计修正

```python
# export.py — 审计移至 CSV 生成成功后
def export_csv(req, db, current_user):
    # ... 获取产品 + 一致性检查 ...
    
    # 审计不再提前写入
    csv_data = generate_csv(products, platform)  # 先生成 CSV
    
    # CSV 生成成功后写入审计
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action='export_csv',
        subject_type='product',
        subject_id=','.join(product_ids),
        after={
            "platform": platform,
            "product_count": len(products),
            "consistency_status": status,
        },
    )
    db.commit()  # 审计提交
    
    return StreamingResponse(csv_data, ...)
```

#### 审计日志字段规范

| 字段 | 导入 | 导出 | CRUD |
|------|------|------|------|
| `action` | `import_execute` | `export_csv` | `product_create/update/delete` |
| `subject_type` | `product` | `product` | `product/term/user` |
| `subject_id` | file_hash | product_ids 连接 | 单个 resource_id |
| `after` | 统计 + 错误详情 | 平台 + 产品数 | 变更后的字段值 |
| `before` | — | — | 变更前的字段值（update/delete） |

## 影响

### 变容易
- 合规审计：所有变更操作可追溯
- 问题定位：导入失败可追溯具体文件、行号和错误
- 用户行为分析：完整的操作历史

### 变困难
- 每条变更操作需要额外的一次数据库写入
- 审计日志表随系统使用增长，需要轮转策略

### 需要重新审视
- `import_.py` 的执行流程（添加审计写入点）
- `export.py` 的审计写入时序（移到响应生成后）
- `products.py` 和 `terms.py` 的 CRUD 操作审计覆盖
- 审计日志表的索引策略（按 `action`、`created_at`、`user_id` 查询）
- 审计日志保留和清理策略
