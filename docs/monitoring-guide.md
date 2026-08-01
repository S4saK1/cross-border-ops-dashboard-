# 性能监控和指标收集指南

## 概述

本指南详细说明跨境产品资料中英对照系统的性能监控和指标收集方案。系统采用多层次监控策略，包括应用性能监控、系统资源监控和业务指标监控。

## 监控架构

```
┌─────────────────────────────────────────────────────────────┐
│                     监控数据流                              │
├─────────────────────────────────────────────────────────────┤
│  应用层  │  中间件  │  数据库  │  系统层  │  业务层        │
├──────────┼──────────┼──────────┼──────────┼─────────────────┤
│  FastAPI │  Nginx   │ SQLite   │  Linux   │  产品数据       │
│  监控    │  监控    │  监控    │  监控    │  业务指标       │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
         │              │              │              │
         └──────────────┼──────────────┼──────────────┘
                        ▼              ▼              ▼
               ┌─────────────────────────────────────────────┐
               │              Prometheus                    │
               │         (指标收集和存储)                   │
               └─────────────────────────────────────────────┘
                        │              │              │
                        ▼              ▼              ▼
               ┌─────────────────────────────────────────────┐
               │              Grafana                       │
               │         (可视化仪表板)                    │
               └─────────────────────────────────────────────┘
```

## 监控指标

### 1. 应用性能指标

#### HTTP请求指标
- `http_requests_total`: HTTP请求总数
- `http_request_duration_seconds`: HTTP请求响应时间
- `http_request_size_bytes`: HTTP请求大小
- `http_response_size_bytes`: HTTP响应大小
- `http_requests_in_progress`: 当前进行中的请求数

#### 业务指标
- `product_operations_total`: 产品操作总数
- `term_operations_total`: 术语操作总数
- `import_operations_total`: 导入操作总数
- `export_operations_total`: 导出操作总数
- `consistency_checks_total`: 一致性检测总数

#### 错误指标
- `http_requests_errors_total`: HTTP错误请求总数
- `application_errors_total`: 应用错误总数
- `database_errors_total`: 数据库错误总数

### 2. 系统资源指标

#### CPU指标
- `system_cpu_usage_percent`: CPU使用率
- `system_cpu_load_average_1m`: 1分钟CPU负载
- `system_cpu_load_average_5m`: 5分钟CPU负载
- `system_cpu_load_average_15m`: 15分钟CPU负载

#### 内存指标
- `system_memory_total_bytes`: 总内存
- `system_memory_used_bytes`: 已用内存
- `system_memory_available_bytes`: 可用内存
- `system_memory_usage_percent`: 内存使用率

#### 磁盘指标
- `system_disk_total_bytes`: 磁盘总容量
- `system_disk_used_bytes`: 磁盘已用容量
- `system_disk_available_bytes`: 磁盘可用容量
- `system_disk_usage_percent`: 磁盘使用率
- `system_disk_io_read_bytes`: 磁盘读取字节数
- `system_disk_io_written_bytes`: 磁盘写入字节数

#### 网络指标
- `system_network_receive_bytes`: 网络接收字节数
- `system_network_transmit_bytes`: 网络发送字节数

### 3. 数据库指标

#### 连接指标
- `db_connections_active`: 活跃数据库连接数
- `db_connections_idle`: 空闲数据库连接数
- `db_connections_total`: 总数据库连接数

#### 查询指标
- `db_query_duration_seconds`: 数据库查询响应时间
- `db_queries_total`: 数据库查询总数
- `db_slow_queries_total`: 慢查询总数

#### 事务指标
- `db_transactions_total`: 数据库事务总数
- `db_transactions_duration_seconds`: 事务执行时间
- `db_transactions_errors_total`: 事务错误总数

### 4. 缓存指标

#### 内存缓存指标
- `cache_memory_hits_total`: 内存缓存命中次数
- `cache_memory_misses_total`: 内存缓存未命中次数
- `cache_memory_hit_ratio`: 内存缓存命中率
- `cache_memory_size_bytes`: 内存缓存大小
- `cache_memory_entries`: 内存缓存条目数

#### 文件缓存指标
- `cache_file_hits_total`: 文件缓存命中次数
- `cache_file_misses_total`: 文件缓存未命中次数
- `cache_file_hit_ratio`: 文件缓存命中率

## 监控配置

### Prometheus配置

```yaml
# prometheus.yml（与 monitoring/prometheus.yml 同步）
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# 告警规则文件
rule_files:
  - "alerts.yml"

# 告警管理器配置
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics/prometheus'
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
      
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

### Grafana仪表板

#### 应用性能仪表板
- HTTP请求速率和响应时间
- 错误率和错误分布
- 业务操作统计
- 实时请求监控

#### 系统资源仪表板
- CPU、内存、磁盘使用率
- 网络流量监控
- 系统负载趋势
- 资源使用预测

#### 数据库性能仪表板
- 数据库连接状态
- 查询性能分析
- 事务执行统计
- 慢查询分析

#### 业务指标仪表板
- 产品管理操作统计
- 术语管理操作统计
- 导入导出操作统计
- 一致性检测统计

## 告警配置

### 告警规则

#### 严重告警（立即响应）
- HTTP错误率 > 5%
- 应用响应时间 > 5秒
- 数据库连接数 > 80%
- 内存使用率 > 90%
- 磁盘使用率 > 90%

#### 警告告警（需要关注）
- HTTP错误率 > 1%
- 应用响应时间 > 2秒
- 数据库连接数 > 60%
- 内存使用率 > 70%
- 磁盘使用率 > 70%

#### 信息告警（记录监控）
- 应用重启
- 数据库备份完成
- 配置变更
- 用户异常登录

### 告警通知

#### 通知渠道
- 邮件通知：发送到运维团队邮箱
- Slack通知：发送到运维频道
- 企业微信通知：发送到运维群
- 短信通知：紧急情况短信通知

#### 通知策略
- 严重告警：立即通知，5分钟内响应
- 警告告警：30分钟内通知，2小时内响应
- 信息告警：汇总通知，每日处理

## 日志监控

### 应用日志

#### 日志级别
- DEBUG: 调试信息
- INFO: 一般信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

#### 日志格式
```json
{
  "timestamp": "2024-01-01T00:00:00.000Z",
  "level": "INFO",
  "message": "User login successful",
  "context": {
    "user_id": "user-123",
    "ip_address": "127.0.0.1",
    "user_agent": "Mozilla/5.0..."
  },
  "service": "bilingual-product-cms-backend"
}
```

### 访问日志

#### 日志格式
```
127.0.0.1 - - [01/Jan/2024:00:00:00 +0000] "POST /api/v1/auth/login HTTP/1.1" 200 1234 "-" "Mozilla/5.0..."
```

#### 日志字段
- 客户端IP
- 用户标识
- 时间戳
- 请求方法
- 请求路径
- HTTP状态码
- 响应大小
- 用户代理

### 错误日志

#### 错误分类
1. 应用错误：代码异常、业务逻辑错误
2. 数据库错误：连接失败、查询错误
3. 网络错误：连接超时、DNS解析失败
4. 系统错误：内存不足、磁盘空间不足

## 性能优化建议

### 数据库优化
1. 添加适当的索引
2. 使用连接池
3. 优化查询语句
4. 定期分析慢查询

### 应用优化
1. 使用缓存减少数据库查询
2. 异步处理耗时操作
3. 优化序列化/反序列化
4. 使用批处理减少网络往返

### 系统优化
1. 调整系统参数
2. 优化网络配置
3. 使用CDN加速静态资源
4. 配置负载均衡

## 监控最佳实践

### 1. 监控覆盖率
- 确保所有关键组件都有监控
- 覆盖所有业务场景
- 包括正常和异常情况

### 2. 告警有效性
- 设置合理的告警阈值
- 避免告警疲劳
- 定期 review 告警规则

### 3. 数据保留
- 应用指标：保留30天
- 系统指标：保留90天
- 业务指标：保留1年
- 日志数据：保留6个月

### 4. 定期检查
- 每日检查监控系统状态
- 每周分析性能趋势
- 每月优化监控配置
- 每季度评估监控效果
