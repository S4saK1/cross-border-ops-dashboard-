# 事故响应Runbook

## 概述

本Runbook为跨境产品资料中英对照系统提供事故响应指南，包括SEV分级标准、响应流程、升级矩阵和常见问题处理指南。

## SEV分级标准

### SEV1 - 紧急（Critical）
- **定义**：系统完全不可用，影响所有用户
- **示例**：
  - 生产环境数据库完全不可用
  - 所有API端点返回500错误
  - 用户无法登录或访问系统
  - 数据丢失或损坏
- **响应时间**：15分钟内
- **解决时间**：4小时内

### SEV2 - 高优先级（High）
- **定义**：系统核心功能受影响，影响大部分用户
- **示例**：
  - 主要API端点不可用
  - 性能严重下降（响应时间>10秒）
  - 部分用户无法访问
  - 安全漏洞被利用
- **响应时间**：30分钟内
- **解决时间**：8小时内

### SEV3 - 中优先级（Medium）
- **定义**：系统部分功能受影响，影响部分用户
- **示例**：
  - 非核心功能不可用
  - 性能下降但可用
  - 单个用户或小范围用户受影响
  - 非关键安全漏洞
- **响应时间**：2小时内
- **解决时间**：24小时内

### SEV4 - 低优先级（Low）
- **定义**：系统轻微问题，不影响主要功能
- **示例**：
  - 非关键功能异常
  - 轻微性能问题
  - 用户界面问题
  - 文档错误
- **响应时间**：24小时内
- **解决时间**：72小时内

## 响应流程

### 1. 事故发现
- **监控告警**：Prometheus/Grafana告警
- **用户报告**：用户反馈或支持工单
- **系统日志**：异常日志或错误报告
- **健康检查**：定期健康检查失败

### 2. 初步评估（5分钟内）
1. **确认事故**：验证问题是否真实存在
2. **评估影响**：确定影响范围和严重程度
3. **分配SEV等级**：根据影响程度分配SEV等级
4. **通知相关人员**：根据SEV等级通知相应团队

### 3. 响应团队（15分钟内）
#### SEV1/SEV2响应团队
- **事故指挥官**：负责整体协调
- **技术负责人**：负责技术问题诊断
- **SRE工程师**：负责系统恢复
- **开发工程师**：负责代码修复
- **QA工程师**：负责验证修复

#### SEV3/SEV4响应团队
- **值班工程师**：负责初步诊断和修复
- **技术负责人**：提供技术支持

### 4. 问题诊断（30分钟内）
1. **收集信息**：
   - 系统日志和错误日志
   - 监控指标和图表
   - 用户报告和反馈
   - 最近变更记录

2. **分析问题**：
   - 确定问题根本原因
   - 评估影响范围
   - 制定修复方案

3. **制定计划**：
   - 短期修复方案
   - 长期改进计划
   - 风险评估和回滚计划

### 5. 问题修复（根据SEV等级）
#### 短期修复（热修复）
- 配置调整
- 服务重启
- 流量切换
- 功能降级

#### 长期修复（代码修复）
- 代码修复
- 数据修复
- 架构调整
- 流程改进

### 6. 验证和恢复（修复后）
1. **功能验证**：验证修复是否有效
2. **性能测试**：验证性能是否恢复正常
3. **用户验证**：确认用户可以正常使用
4. **监控观察**：持续监控系统状态

### 7. 事故复盘（24小时内）
1. **事故报告**：编写详细事故报告
2. **根本原因分析**：深入分析问题根本原因
3. **改进措施**：制定改进措施和预防方案
4. **知识分享**：分享事故经验和教训

## 升级矩阵

### SEV1升级流程
```
0-15分钟：值班工程师 → 技术负责人 → SRE工程师
15-30分钟：技术负责人 → CTO → CEO
30-60分钟：CTO → 公司管理层
```

### SEV2升级流程
```
0-30分钟：值班工程师 → 技术负责人
30-60分钟：技术负责人 → CTO
60-120分钟：CTO → 公司管理层（如需要）
```

### SEV3/SEV4升级流程
```
0-2小时：值班工程师 → 技术负责人
2-24小时：技术负责人 → CTO（如需要）
```

## 常见问题处理指南

### 1. 数据库连接问题
#### 症状
- API返回数据库连接错误
- 健康检查显示数据库不可用
- 应用启动失败

#### 诊断步骤
```bash
# 检查数据库状态
docker compose ps postgres

# 检查数据库日志
docker compose logs postgres

# 测试数据库连接
docker compose exec backend python -c "from app.database import engine; engine.connect()"

# 检查数据库配置
cat .env | grep DATABASE_URL
```

#### 解决方案
1. **数据库服务未启动**：启动数据库服务
2. **配置错误**：检查并修正数据库配置
3. **连接池耗尽**：重启应用或调整连接池配置
4. **磁盘空间不足**：清理磁盘空间或扩展存储

### 2. API性能问题
#### 症状
- API响应时间显著增加
- 用户报告系统缓慢
- 监控显示高延迟

#### 诊断步骤
```bash
# 检查系统资源
docker stats

# 检查应用日志
docker compose logs backend | tail -100

# 检查数据库查询
docker compose exec backend python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT * FROM pg_stat_activity'))
    for row in result:
        print(row)
"

# 检查慢查询
docker compose exec postgres psql -U postgres -d bilingual_cms -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
"
```

#### 解决方案
1. **数据库查询优化**：优化慢查询，添加索引
2. **连接池调整**：调整数据库连接池配置
3. **缓存优化**：添加或优化缓存策略
4. **资源扩展**：增加服务器资源

### 3. 内存溢出问题
#### 症状
- 应用崩溃或重启
- 监控显示高内存使用
- 系统响应缓慢

#### 诊断步骤
```bash
# 检查内存使用
docker stats --no-stream

# 检查应用内存
docker compose exec backend python -c "
import psutil
print(f'Memory usage: {psutil.virtual_memory().percent}%')
print(f'Available memory: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB')
"

# 检查内存泄漏
docker compose exec backend python -c "
import tracemalloc
tracemalloc.start()
# 执行一些操作
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"
```

#### 解决方案
1. **内存泄漏修复**：查找并修复内存泄漏
2. **内存限制调整**：调整Docker内存限制
3. **垃圾回收优化**：优化Python垃圾回收配置
4. **缓存清理**：清理不必要的缓存数据

### 4. 安全事件处理
#### 症状
- 异常登录尝试
- 可疑API调用
- 安全告警触发

#### 诊断步骤
```bash
# 检查登录日志
docker compose logs backend | grep -i "login\|auth\|failed"

# 检查异常请求
docker compose logs backend | grep -i "401\|403\|500"

# 检查用户活动
docker compose exec backend python -c "
from app.models.audit import AuditLog
from app.database import SessionLocal
db = SessionLocal()
logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
for log in logs:
    print(f'{log.created_at}: {log.user_id} - {log.action}')
db.close()
"
```

#### 解决方案
1. **IP封禁**：封禁可疑IP地址
2. **用户锁定**：锁定可疑用户账户
3. **密码重置**：强制重置相关用户密码
4. **安全审计**：进行全面安全审计

### 5. 外部服务依赖问题
#### 症状
- 第三方API调用失败
- 外部服务超时
- 集成功能异常

#### 诊断步骤
```bash
# 测试外部服务连接
curl -I https://api.example.com/health

# 检查网络连接
ping api.example.com

# 检查DNS解析
nslookup api.example.com

# 检查代理配置
env | grep -i proxy
```

#### 解决方案
1. **服务切换**：切换到备用服务或降级处理
2. **超时调整**：调整超时配置和重试策略
3. **缓存策略**：增加缓存减少外部依赖
4. **监控告警**：加强外部服务监控

## 预防措施

### 1. 监控和告警
- 设置全面的监控指标
- 配置合理的告警阈值
- 建立告警升级机制
- 定期审查告警规则

### 2. 变更管理
- 实施变更审批流程
- 进行变更影响评估
- 制定回滚计划
- 记录变更历史

### 3. 容量规划
- 定期进行容量评估
- 监控资源使用趋势
- 制定扩展计划
- 进行压力测试

### 4. 备份和恢复
- 定期进行数据备份
- 测试备份恢复流程
- 制定灾难恢复计划
- 维护恢复文档

### 5. 安全加固
- 定期进行安全审计
- 实施安全最佳实践
- 进行渗透测试
- 保持系统更新

## 工具和资源

### 监控工具
- **Prometheus**：指标收集和存储
- **Grafana**：可视化仪表板
- **Alertmanager**：告警管理
- **ELK Stack**：日志收集和分析

### 诊断工具
- **Docker**：容器管理和调试
- **kubectl**：Kubernetes管理
- **psql**：PostgreSQL客户端
- **curl/wget**：HTTP测试工具

### 文档资源
- **系统架构文档**：了解系统架构
- **API文档**：了解API接口
- **部署文档**：了解部署配置
- **运维手册**：了解运维流程

## 联系方式

### 紧急联系人
- **技术负责人**：参见团队通讯录或 Slack #oncall 频道
- **SRE工程师**：参见团队通讯录或 Slack #sre 频道
- **运维值班**：参见 PagerDuty 排班表

### 外部支持
- **云服务商支持**：Cloud Provider 工单系统
- **第三方服务支持**：服务商 SLA 文档
- **安全团队**：security@bilingual-cms.com

## 附录

### 事故报告模板
```
事故报告

1. 事故概述
   - 时间：YYYY-MM-DD HH:MM:SS
   - 持续时间：X小时X分钟
   - SEV等级：SEV1/SEV2/SEV3/SEV4
   - 影响范围：X用户/X功能

2. 事故时间线
   - HH:MM:SS 事故发生
   - HH:MM:SS 发现事故
   - HH:MM:SS 开始响应
   - HH:MM:SS 问题定位
   - HH:MM:SS 开始修复
   - HH:MM:SS 修复完成
   - HH:MM:SS 验证完成

3. 根本原因
   - 技术原因：[详细描述]
   - 流程原因：[详细描述]
   - 人员原因：[详细描述]

4. 影响分析
   - 用户影响：[详细描述]
   - 业务影响：[详细描述]
   - 财务影响：[详细描述]

5. 修复措施
   - 短期措施：[详细描述]
   - 长期措施：[详细描述]

6. 预防措施
   - 技术改进：[详细描述]
   - 流程改进：[详细描述]
   - 人员培训：[详细描述]

7. 经验教训
   - 成功经验：[详细描述]
   - 改进点：[详细描述]
```

### 常用命令速查
```bash
# 系统状态检查
docker compose ps
docker stats --no-stream

# 日志查看
docker compose logs -f backend
docker compose logs -f postgres

# 健康检查
curl http://localhost:8000/health
curl http://localhost:8000/health

# 数据库操作
docker compose exec postgres psql -U postgres -d bilingual_cms
docker compose exec backend python -c "from app.database import engine; engine.connect()"

# 性能监控
docker compose exec backend python -c "import psutil; print(psutil.virtual_memory())"
docker compose exec backend python -c "import psutil; print(psutil.cpu_percent())"

# 备份恢复
docker compose exec backend python scripts/backup.py
docker compose exec backend python scripts/backup.py
```
