# ADR-010: Redis 硬依赖
**状态:** Accepted
**日期:** 2026-07-31

## 背景

在早期版本中，`redis` 包**不在 `requirements.txt` 中**。代码通过 `try/except ImportError` 静默处理（使用 `pass`），导致以下问题：

- **生产镜像无 Redis 客户端**：`COPY . .` 构建的镜像缺少 `redis` 包
- **频率限制全局禁用**：`RateLimiter.check()` 的 `ImportError` 被 `pass` 吞掉，所有 Worker 的频率限制全部失效，无任何告警
- **跨 Worker 缓存断裂**：上传缓存回退到进程内存，多 Worker 部署时无法共享缓存
- **指标聚合失效**：`MetricsAggregator` 导入失败后指标仅在单 Worker 内存中累积

### 当前状态

- `requirements.txt` 第 11 行：`redis>=5.0.0` — **已添加**
- `monitoring.py` 第 13-16 行：`ImportError` 记录 `logging.error("Redis not available, metrics aggregation disabled")`
- `import_.py` 第 104-107 行：`ImportError` 记录 `logging.error("Redis not available, upload cache disabled")`

虽然日志级别已提升为 ERROR，但代码仍然**静默降级**而非**快速失败**。生产环境缺少 Redis 时，应用仍然启动，只是功能残缺（无频率限制、无跨 Worker 缓存）。

## 选项分析

### 选项 A: 保持现状（ERROR 日志 + 静默降级）
| 维度 | 评估 |
|------|------|
| 复杂度 | Low — 已完成 |
| 可靠性 | 低 — 降级不告警，运维难以察觉 |
| 开发体验 | 好 — 开发环境可不用 Redis |

### 选项 B: 生产环境启动时强制检查 Redis
| 维度 | 评估 |
|------|------|
| 复杂度 | Medium — 需在 lifespan 中添加检查 |
| 可靠性 | 高 — 启动即发现配置问题 |
| 开发体验 | 好 — 开发环境跳过检查 |

### 选项 C: Redis 完全可选
| 维度 | 评估 |
|------|------|
| 复杂度 | High — 所有 Redis 功能需要完整降级路径 |
| 可靠性 | 中 — 降级行为更复杂，测试矩阵更大 |
| 开发体验 | 最好 |

## 决策

选择**选项 B: 生产环境启动时强制检查 Redis**。

### 理由
1. **功能完整性**：频率限制是安全关键功能（防暴力破解），跨 Worker 缓存是正确性保证（多 Worker 导入不丢失）
2. **快速失败原则**：生产环境缺少依赖时应启动失败，而非静默运行残缺功能
3. **可观测性**：`ImportError` 记录 ERROR 日志 + 生产环境启动失败 = 运维人员立即发现问题
4. **开发友好**：`ENVIRONMENT=development` 时跳过 Redis 强制检查，保持零依赖开发体验
5. **依赖明确化**：`requirements.txt` 包含 `redis>=5.0.0`，Docker 构建自动安装

### 实施要点

```python
# lifespan 中添加
if settings.ENVIRONMENT == "production":
    try:
        from app.core.redis import RateLimiter
        RateLimiter.ping()  # 验证 Redis 连接可用
    except Exception as e:
        logger.critical(f"Redis is required in production but unavailable: {e}")
        raise RuntimeError("Redis unavailable in production") from e
```

各模块中的 Redis 降级逻辑保留，但仅用于开发环境优雅降级。

## 影响

### 变容易
- 生产问题定位：Redis 不可用时立即发现
- 安全保证：频率限制在所有部署中都生效
- 运维监控：ERROR 日志 + 启动失败双重保障

### 变困难
- 短暂 Redis 故障时容器会重启（依赖健康检查和 restart policy）
- 开发环境需要 `ENVIRONMENT=development` 明确设置

### 需要重新审视
- Docker Compose 中 Redis 服务的健康检查依赖
- `docker-compose.prod.yml` 中 backend 的 `depends_on: redis (condition: service_healthy)`
- 生产环境的 Redis 高可用方案（sentinel/cluster）
