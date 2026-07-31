# 日志配置指南

## 概述
本指南介绍如何为跨境产品资料中英对照系统配置和使用日志系统。

## 日志架构
系统支持两种日志格式：
1. **默认格式**: 传统的文本格式，适合开发环境
2. **结构化格式**: JSON格式，适合生产环境和日志聚合

## 日志配置

### 配置文件位置
`backend/logging_config.py`

### 日志格式

#### 默认格式（开发环境）
```
2026-07-23 14:30:22,123 - app.api.auth - INFO - 用户登录成功: admin
```

#### 结构化格式（生产环境）
```json
{
  "timestamp": "2026-07-23T14:30:22.123456Z",
  "level": "INFO",
  "logger": "app.api.auth",
  "message": "用户登录成功: admin",
  "module": "auth",
  "function": "login",
  "line": 42
}
```

### 日志级别
- **DEBUG**: 详细调试信息
- **INFO**: 一般信息（默认级别）
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误信息

## 使用方法

### 基本日志记录
```python
import logging

# 获取日志器
logger = logging.getLogger(__name__)

# 记录日志
logger.info("用户登录成功")
logger.warning("数据库连接池接近上限")
logger.error("文件上传失败")
```

### 结构化日志记录
```python
import logging
import json

logger = logging.getLogger("app")

# 添加额外数据
extra_data = {
    "user_id": 123,
    "action": "login",
    "ip_address": "192.168.1.100"
}

# 创建LogRecord并添加额外数据
record = logger.makeRecord(
    name="app.api.auth",
    level=logging.INFO,
    fn="auth.py",
    lno=42,
    msg="用户登录成功",
    args=None,
    exc_info=None
)
record.extra_data = extra_data

# 处理记录
logger.handle(record)
```

### 请求日志中间件
系统已配置请求日志中间件，自动记录：
- 请求路径
- 请求方法
- 响应状态码
- 处理时间

示例日志：
```
Path: /api/v1/auth/login Method: POST Status: 200 Duration: 0.1234s
```

## 生产环境配置

### 使用结构化日志
在生产环境中，建议使用结构化日志（JSON格式），便于日志聚合和分析。

### 日志聚合系统集成
结构化日志可以轻松集成到以下系统：
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Loki + Grafana**
- **Datadog**
- **Splunk**

### 日志轮转
建议配置日志轮转，避免日志文件过大：
```bash
# 使用logrotate配置
/var/log/bilingual-product-cms/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 app app
}
```

## 监控和告警

### 日志监控
可以设置日志监控规则：
- 错误日志数量超过阈值
- 特定错误模式出现
- 日志量异常波动

### 告警规则示例
```yaml
# Prometheus告警规则
groups:
  - name: app-logs
    rules:
      - alert: HighErrorRate
        expr: rate(app_log_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "应用错误率过高"
          description: "过去5分钟错误率超过10%"
```

## 故障排查

### 问题1: 日志不输出
**检查项**:
1. 日志级别是否正确设置
2. 日志处理器是否配置
3. 日志文件权限是否正确

### 问题2: 结构化日志格式错误
**检查项**:
1. StructuredFormatter是否正确导入
2. JSON序列化是否正常
3. 字符编码是否正确（使用ensure_ascii=False）

### 问题3: 日志文件过大
**解决方案**:
1. 配置日志轮转
2. 调整日志级别
3. 使用日志聚合系统

## 最佳实践

### 1. 日志内容
- 记录有意义的信息
- 包含相关上下文（用户ID、请求ID等）
- 避免记录敏感信息（密码、token等）

### 2. 日志级别
- 开发环境: DEBUG级别
- 测试环境: INFO级别
- 生产环境: INFO或WARNING级别

### 3. 性能考虑
- 避免在循环中记录大量日志
- 使用异步日志记录（如需要）
- 合理设置日志级别

### 4. 安全考虑
- 不要记录敏感信息
- 限制日志访问权限
- 定期清理旧日志

## 相关文档
- [监控配置指南](monitoring-setup.md)
- [部署检查清单](../deployment-checklist.md)
- [SRE运维评估报告](../../deliverables/gstack/sre-assessment.md)

---
**文档版本**: v1.0
**最后更新**: 2026-07-23
**维护者**: Rex (SRE Engineer)