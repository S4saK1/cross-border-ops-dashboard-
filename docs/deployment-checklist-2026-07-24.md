# 生产环境部署检查清单

**项目**：跨境产品资料中英对照系统
**日期**：2026-07-24
**版本**：v1.0.0
**部署负责人**：DevOps团队

---

## 📋 部署前检查

### 1. 环境准备 ✅
- [ ] 服务器环境准备完成
- [ ] Docker和Docker Compose安装完成
- [ ] 网络配置完成（端口开放、防火墙规则）
- [ ] SSL证书准备完成
- [ ] 域名解析配置完成

### 2. 配置文件检查 ✅
- [ ] `.env.production`文件配置正确
- [ ] 数据库连接字符串正确
- [ ] Redis连接配置正确
- [ ] 密钥和密码已更换为生产环境值
- [ ] CORS配置正确

### 3. 数据库准备 ✅
- [ ] PostgreSQL数据库创建完成
- [ ] 数据库用户权限配置正确
- [ ] 数据库备份策略配置完成
- [ ] 数据库迁移脚本准备完成

### 4. Redis准备 ✅
- [ ] Redis服务部署完成
- [ ] Redis密码配置正确
- [ ] Redis持久化配置完成
- [ ] Redis监控配置完成

### 5. 监控准备 ✅
- [ ] Prometheus配置完成
- [ ] Grafana仪表板配置完成
- [ ] 告警规则配置完成
- [ ] 告警通知渠道配置完成

---

## 🚀 部署步骤

### 步骤1：拉取最新代码
```bash
cd /path/to/project
git pull origin main
git checkout v1.0.0
```

### 步骤2：构建Docker镜像
```bash
# 构建后端镜像
docker build -t bilingual-product-cms-backend:v1.0.0 ./backend

# 构建前端镜像
docker build -t bilingual-product-cms-frontend:v1.0.0 ./frontend
```

### 步骤3：启动服务
```bash
# 使用生产环境配置启动
docker compose -f docker-compose.prod.yml up -d

# 检查服务状态
docker compose -f docker-compose.prod.yml ps
```

### 步骤4：初始化数据库
```bash
# 运行数据库迁移
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 初始化管理员账户
docker compose -f docker-compose.prod.yml exec backend python init_db.py
```

### 步骤5：验证服务
```bash
# 检查健康状态
curl -f http://localhost:8000/health

# 检查API文档
curl -f http://localhost:8000/docs

# 检查监控端点
curl -f http://localhost:8000/metrics
```

---

## 🔍 部署后验证

### 1. 服务验证
- [ ] 后端服务正常运行
- [ ] 前端服务正常运行
- [ ] 数据库连接正常
- [ ] Redis连接正常
- [ ] 监控服务正常

### 2. 功能验证
- [ ] 用户登录功能正常
- [ ] 产品CRUD功能正常
- [ ] 术语管理功能正常
- [ ] CSV导入导出功能正常
- [ ] 一致性检测功能正常

### 3. 性能验证
- [ ] API响应时间<500ms
- [ ] 并发用户支持正常
- [ ] 数据库查询性能正常
- [ ] Redis缓存命中率正常

### 4. 安全验证
- [ ] HTTPS配置正确
- [ ] 认证授权正常
- [ ] 输入验证正常
- [ ] 错误处理正常

---

## 🔄 回滚方案

### 回滚触发条件
- 服务无法正常启动
- 关键功能无法使用
- 性能严重下降
- 安全漏洞发现

### 回滚步骤
```bash
# 1. 停止当前服务
docker compose -f docker-compose.prod.yml down

# 2. 切换到上一个版本
git checkout v0.9.0

# 3. 重新构建和部署
docker compose -f docker-compose.prod.yml up -d

# 4. 验证回滚成功
curl -f http://localhost:8000/health
```

### 回滚后检查
- [ ] 服务恢复正常
- [ ] 数据完整性检查
- [ ] 功能验证通过
- [ ] 监控恢复正常

---

## 📊 监控和告警

### 关键监控指标
1. **服务可用性**
   - 指标：`up{job="bilingual-product-cms-backend"}`
   - 告警：服务宕机

2. **错误率**
   - 指标：`rate(app_errors_total[5m]) / rate(app_requests_total[5m])`
   - 告警：错误率>5%

3. **响应时间**
   - 指标：`histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
   - 告警：P95响应时间>1s

4. **数据库连接**
   - 指标：`db_connection_pool_size`
   - 告警：连接池使用率>80%

5. **Redis连接**
   - 指标：`redis_connected_clients`
   - 告警：连接数异常

### 告警通知
- **邮件通知**：devops@company.com
- **Slack通知**：#alerts频道
- **电话通知**：严重故障时

---

## 📝 部署记录

### 部署信息
- **部署时间**：2026-07-24 02:41
- **部署版本**：v1.0.0
- **部署人员**：DevOps团队
- **部署环境**：生产环境

### 变更记录
1. Access Token短效化（30分钟）
2. Redis黑名单集成
3. CI测试过滤修复
4. API文档100%覆盖
5. PostgreSQL生产环境配置
6. Prometheus监控集成

### 已知问题
1. Redis单实例配置（Sprint 3将升级为集群）
2. 备份脚本需手动执行（Sprint 3将自动化）
3. 性能测试未执行（Sprint 3将执行）

---

## ✅ 部署确认

### 部署团队确认
- [ ] DevOps工程师确认部署完成
- [ ] 后端开发确认功能正常
- [ ] 前端开发确认界面正常
- [ ] QA工程师确认测试通过
- [ ] 产品经理确认业务正常

### 部署签字
- **DevOps负责人**：_________________ 日期：_______
- **技术负责人**：_________________ 日期：_______
- **产品负责人**：_________________ 日期：_______

---

> 本检查清单由工程保障团队 AI 协作生成，关键决策请由人类工程负责人复核。
> 部署前请仔细检查所有项目，确保生产环境稳定运行。