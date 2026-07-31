# 修复README.md目录名不一致问题

## 问题分析
根据技术债评估报告#27，README.md中指引的目录名与实际目录名不一致：
- **README.md中**：`cd bilingual-cms`
- **实际目录**：`bilingual-product-cms`

## 影响范围
通过搜索发现，以下文件中存在命名不一致问题：

### 1. Docker配置文件
- `docker-compose.yml` - 容器名、数据库名
- `docker-compose.prod.yml` - 生产环境配置
- `docker-compose.test.yml` - 测试环境配置
- `docker-compose.monitoring.yml` - 监控配置

### 2. 监控配置文件
- `monitoring/alerts.yml` - 告警规则
- `deploy/monitoring/docker-compose.monitoring.yml` - 监控服务

### 3. 文档文件
- `README.md` - 主文档
- `DEPLOY.md` - 部署文档
- `docs/runbooks/docker-deployment.md` - Docker部署手册
- `docs/runbooks/monitoring-setup.md` - 监控配置手册
- `docs/runbooks/logging-configuration.md` - 日志配置手册

### 4. 脚本文件
- `scripts/health-check.sh` - 健康检查脚本

### 5. 前端文件
- `frontend/package.json` - 包名
- `frontend/src/app/login/page.tsx` - 占位符文本

## 修复策略

### 原则
1. **保持向后兼容**：数据库名和容器名可能影响现有部署
2. **渐进式修改**：优先修复文档和配置，再考虑运行时配置
3. **统一命名规范**：使用`bilingual-product-cms`作为标准名称

### 分阶段修复

#### 第一阶段：文档和配置文件修复（低风险）
1. **README.md** - 修复目录名指引
2. **DEPLOY.md** - 修复默认管理员邮箱
3. **文档文件** - 修复所有引用
4. **前端文件** - 修复占位符文本

#### 第二阶段：Docker配置修复（中风险）
1. **容器名** - 从`bilingual-cms-*`改为`bilingual-product-cms-*`
2. **数据库名** - 从`bilingual_cms`改为`bilingual_product_cms`
3. **服务名** - 更新所有相关配置

#### 第三阶段：运行时配置修复（高风险）
1. **数据库迁移** - 需要数据迁移脚本
2. **容器重建** - 需要重新构建镜像
3. **监控配置** - 更新Prometheus和Grafana配置

## 具体修复内容

### 1. README.md修复
```markdown
#### 1. 克隆项目
```bash
git clone <repository-url>
cd bilingual-product-cms  # 修复：从bilingual-cms改为bilingual-product-cms
```
```

### 2. Docker配置修复
```yaml
# docker-compose.yml
services:
  backend:
    container_name: bilingual-product-cms-backend  # 修复
    environment:
      - ADMIN_EMAIL=${ADMIN_EMAIL:-admin@bilingual-product-cms.com}  # 修复
      - POSTGRES_DB=${POSTGRES_DB:-bilingual_product_cms}  # 修复
  
  postgres:
    container_name: bilingual-product-cms-postgres  # 修复
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-bilingual_product_cms}  # 修复
```

### 3. 前端文件修复
```typescript
// frontend/src/app/login/page.tsx
placeholder="admin@bilingual-product-cms.com"  // 修复
```

### 4. 监控配置修复
```yaml
# monitoring/alerts.yml
- name: bilingual-product-cms-alerts  # 修复
  rules:
    - alert: BackendServiceDown
      expr: up{job="bilingual-product-cms-backend"} == 0  # 修复
```

## 风险评估

### 低风险修改
- 文档文件修改
- 前端占位符文本
- 配置文件注释

### 中风险修改
- Docker容器名
- 数据库连接字符串
- 监控作业名

### 高风险修改
- 数据库名变更（需要数据迁移）
- 生产环境配置变更

## 测试验证

### 1. 文档验证
- 检查所有文档中的引用是否一致
- 验证克隆和部署流程是否正确

### 2. 配置验证
- 验证Docker配置语法正确
- 测试容器启动和健康检查
- 验证数据库连接正常

### 3. 功能验证
- 测试用户登录流程
- 测试API端点功能
- 测试监控告警规则

## 实施计划

### 立即修复（今天）
1. 修复README.md目录名
2. 修复DEPLOY.md默认管理员邮箱
3. 修复前端占位符文本

### 本周修复
1. 修复所有文档文件中的引用
2. 修复Docker配置文件中的容器名
3. 更新监控配置文件

### 下周修复
1. 创建数据库迁移脚本
2. 更新生产环境配置
3. 全面测试验证

## 回滚计划

### 文档修改回滚
- 使用Git版本控制回滚
- 无数据影响

### 配置修改回滚
- 保留原配置文件备份
- 使用Docker Compose重新部署

### 数据库修改回滚
- 备份现有数据库
- 准备数据恢复脚本