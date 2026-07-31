# 监控配置指南

## 概述
本指南介绍如何为跨境产品资料中英对照系统设置和使用监控。

## 监控架构
系统使用 Prometheus + Grafana 进行监控：
- **Prometheus**: 收集和存储指标数据
- **Grafana**: 可视化监控数据和仪表板

## 快速启动

### 1. 启动监控服务
```bash
# 进入监控配置目录
cd deploy/monitoring

# 启动Prometheus和Grafana
docker compose -f docker-compose.monitoring.yml up -d
```

### 2. 访问监控界面
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001
  - 默认用户名: admin
  - 默认密码: admin

### 3. 配置Grafana数据源
1. 登录Grafana
2. 进入 Configuration → Data Sources
3. 添加Prometheus数据源
4. URL: http://prometheus:9090

## 可用指标

### 应用指标
系统提供以下基本指标（通过 `/metrics` 端点）：
- `app_uptime_seconds`: 应用运行时间（秒）
- `app_name`: 应用名称
- `app_version`: 应用版本
- `timestamp`: 当前时间戳

### 健康检查指标
通过 `/health` 端点提供：
- `status`: 应用状态（healthy/unhealthy）
- `database`: 数据库连接状态
- `timestamp`: 检查时间戳

## 监控配置

### Prometheus配置
文件位置: `deploy/monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'bilingual-product-cms-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Grafana仪表板
建议创建以下仪表板：
1. **应用健康状态**: 显示健康检查结果
2. **应用运行时间**: 显示应用运行时间趋势
3. **请求监控**: 显示API请求统计（需要集成prometheus-fastapi-instrumentator）

## 扩展监控

### 添加更多指标
如需更详细的监控，建议集成 `prometheus-fastapi-instrumentator`：

```bash
pip install prometheus-fastapi-instrumentator
```

在 `main.py` 中添加：
```python
from prometheus_fastapi_instrumentator import Instrumentator

# 在app定义后添加
Instrumentator().instrument(app).expose(app)
```

### 自定义仪表板
在Grafana中可以创建自定义仪表板，监控：
- 请求响应时间
- 错误率
- 数据库连接状态
- 内存使用情况

## 故障排查

### 问题1: Prometheus无法抓取指标
**症状**: Prometheus targets页面显示backend为down
**解决**:
1. 检查后端服务是否运行: `docker compose ps`
2. 检查网络连通性: `docker compose exec prometheus wget -qO- http://backend:8000/metrics`
3. 检查Prometheus配置是否正确

### 问题2: Grafana无法显示数据
**症状**: Grafana仪表板无数据
**解决**:
1. 检查Prometheus数据源配置
2. 确认Prometheus正在抓取指标
3. 检查Grafana查询语法

## 备份和恢复

### 监控数据备份
Prometheus数据存储在Docker卷中，可以通过以下命令备份：
```bash
docker compose -f docker-compose.monitoring.yml exec prometheus tar -czf /tmp/prometheus-data.tar.gz /prometheus
docker compose -f docker-compose.monitoring.yml cp prometheus:/tmp/prometheus-data.tar.gz ./prometheus-backup.tar.gz
```

### 监控配置备份
监控配置文件已版本控制，无需额外备份。

## 安全注意事项

1. **Grafana默认密码**: 生产环境必须修改默认密码
2. **网络访问**: 限制监控端口的外部访问
3. **数据保留**: 配置适当的数据保留策略

## 相关文档
- [部署检查清单](../deployment-checklist.md)
- [数据库备份](database-backup.md)
- [SRE运维评估报告](../../deliverables/gstack/sre-assessment.md)

---
**文档版本**: v1.0
**最后更新**: 2026-07-23
**维护者**: Rex (SRE Engineer)