# ADR-012: 导出阻断范围 — 按产品而非按批次
**状态:** Accepted
**日期:** 2026-07-31

## 背景

当前导出 API (`backend/app/api/export.py`) 在遇到一致性错误时，**阻断整个导出批次**：

```python
# export.py 第 40-56 行
all_issues = engine.check_products_batch(products)   # 检查请求的所有产品
cross_issues = engine.check_all_products()            # 检查数据库中 ALL 产品
all_issues.extend(cross_issues)

if get_consistency_status(all_issues) == 'error':
    raise HTTPException(status_code=409, detail={...})  # 整个批次 409
```

### 问题分析

1. **跨产品检查范围过大**：`check_all_products()` 检查**数据库中所有产品**（不仅是请求导出的产品）。如果数据库中任意两个产品有跨产品不一致（如不同 SKU 的"颜色"翻译不同），即使当前批次导出的产品完全干净，导出仍被阻断

2. **一个坏产品阻塞全部**：如果请求导出 10 个产品，其中 1 个有 ERROR 级别问题，其余 9 个干净产品也无法导出

3. **不可恢复**：409 响应没有部分成功机制，用户只能修复所有问题后重新发起完整导出

## 选项分析

### 选项 A: 保持批次级阻断（现状）
| 维度 | 评估 |
|------|------|
| 复杂度 | Low — 已实现 |
| 用户体验 | 差 — 一个产品阻塞整批 |
| 数据安全 | 最高 — 绝不导出有问题的产品 |

### 选项 B: 按产品阻断，问题产品跳过
| 维度 | 评估 |
|------|------|
| 复杂度 | Medium — 需重构检查逻辑 |
| 用户体验 | 好 — 干净产品不被牵连 |
| 数据安全 | 高 — 问题产品被跳过并记录 |

### 选项 C: 按产品阻断 + 强制选项
| 维度 | 评估 |
|------|------|
| 复杂度 | High — 需 `force` 参数 |
| 用户体验 | 最好 — 灵活选择 |
| 数据安全 | 中 — force 模式可导出问题数据 |

## 决策

选择**选项 B: 按产品阻断，问题产品跳过**。

### 理由
1. **精确阻断**：每个产品独立检查，ERROR 产品被跳过，WARNING/INFO 产品正常导出
2. **导出元数据**：响应中包含 `skipped_products` 列表，标明哪些产品因何原因被跳过
3. **跨产品检查收窄**：`check_all_products()` 仅在必要时检查，或改为仅检查请求批次内的跨产品一致性
4. **409 仅用于全部失败**：仅当批次中所有产品都有 ERROR 时返回 409
5. **部分成功语义**：HTTP 200 + 元数据描述哪些成功、哪些跳过

### 实施要点

```python
# 伪代码：按产品检查 + 跳过
clean_products = []
skipped_products = []

for product in products:
    issues = engine.check_product(product)
    if get_consistency_status(issues) == 'error':
        skipped_products.append({
            "sku": product.sku,
            "id": product.id,
            "reason": "consistency_errors",
            "issues": [i for i in issues if i['severity'] == 'ERROR']
        })
    else:
        clean_products.append(product)

if not clean_products:
    raise HTTPException(status_code=409, detail={
        "message": "All products in batch have consistency errors",
        "skipped_products": skipped_products
    })

# 生成 CSV（仅干净产品）
csv_data = generate_csv(clean_products, platform)

return {
    "exported_count": len(clean_products),
    "skipped_count": len(skipped_products),
    "skipped_products": skipped_products,
    "csv_data": csv_data,
}
```

### 跨产品检查策略

`check_all_products()` 行为调整：
- **默认**：仅检查当前批次内产品之间的跨产品一致性
- **全库检查**：通过可选参数 `include_all=true` 触发

## 影响

### 变容易
- 用户导出体验：不会因无关产品的数据问题受阻
- 问题定位：明确知道哪些产品有问题及其原因
- 增量导出：可先导出干净产品，再修复问题产品

### 变困难
- 实施复杂度：需重构检查流程为按产品粒度
- 审计追踪：部分成功导出需要更详细的审计日志

### 需要重新审视
- 导出 API 响应格式（从纯 CSV 变为 JSON + CSV）
- 前端导出流程的错误处理和用户提示
- `check_all_products()` 的性能影响和调用范围
