# CI/CD 流程文档

## 概述

本文档描述了 bilingual-product-cms 项目的完整 CI/CD 流程，包括自动化测试、构建、部署和监控。

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     CI/CD 流程架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ 代码提交  │ → │  测试    │ → │  构建    │ → │  部署    │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│       │              │              │              │           │
│       ▼              ▼              ▼              ▼           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ Git Hook │    │  Lint    │    │  Docker  │    │  测试    │ │
│  │ 预提交   │    │  安全检查│    │  镜像    │    │  环境    │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│                        │              │              │         │
│                        ▼              ▼              ▼         │
│                   ┌──────────┐    ┌──────────┐    ┌──────────┐│
│                   │  测试    │    │  推送    │    │  生产    ││
│                   │  报告    │    │  Registry│    │  环境    ││
│                   └──────────┘    └──────────┘    └──────────┘│
│                                              │                 │
│                                              ▼                 │
│                                        ┌──────────┐           │
│                                        │  监控    │           │
│                                        │  告警    │           │
│                                        └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## 流程阶段

### 1. 代码提交触发

- **触发条件**：
  - 推送到 `main` 或 `develop` 分支
  - 创建 Pull Request 到 `main` 分支
- **触发事件**：
  - `push` 事件
  - `pull_request` 事件

### 2. 测试阶段

#### 2.1 代码质量检查
- **Flake8**：代码风格和语法检查
- **Bandit**：安全漏洞扫描
- **Safety**：依赖包安全检查

#### 2.2 单元测试
- **Pytest**：运行所有测试用例
- **覆盖率报告**：生成代码覆盖率报告
- **测试报告**：生成 JUnit XML 格式报告

#### 2.3 测试环境
- Python 3.12
- Ubuntu-latest
- 矩阵测试：支持多版本 Python

### 3. 构建阶段

#### 3.1 Docker 镜像构建
- **基础镜像**：`python:3.12-slim`
- **多阶段构建**：优化镜像大小
- **构建缓存**：使用 GitHub Actions 缓存

#### 3.2 镜像标签策略
- **分支标签**：`main`, `develop`
- **提交标签**：`main-abc1234`
- **语义版本标签**：`v1.0.0`, `v1.0`

#### 3.3 镜像推送
- **目标仓库**：GitHub Container Registry (ghcr.io)
- **认证方式**：GitHub Token
- **构建参数**：支持环境变量注入

### 4. 部署阶段

#### 4.1 测试环境部署
- **触发条件**：推送到 `develop` 分支
- **部署方式**：Docker Compose
- **验证**：冒烟测试

#### 4.2 生产环境部署
- **触发条件**：推送到 `main` 分支
- **部署策略**：蓝绿部署 / 金丝雀发布
- **验证**：生产环境冒烟测试

### 5. 监控和告警

#### 5.1 监控组件
- **Prometheus**：指标收集和存储
- **Grafana**：可视化仪表板
- **Node Exporter**：系统指标
- **cAdvisor**：容器指标

#### 5.2 监控指标
- **应用指标**：请求量、响应时间、错误率
- **系统指标**：CPU、内存、磁盘、网络
- **容器指标**：容器资源使用情况

#### 5.3 告警规则
- **服务健康**：服务宕机或无响应
- **性能指标**：高延迟、高错误率
- **资源使用**：CPU/内存使用率过高

## 配置文件

### GitHub Actions 工作流
- **文件位置**：`.github/workflows/ci-cd.yml`
- **功能**：完整的 CI/CD 流程编排

### Docker 配置
- **生产环境**：`docker-compose.prod.yml`
- **测试环境**：`docker-compose.test.yml`
- **开发环境**：`docker-compose.yml`

### 监控配置
- **Prometheus**：`deploy/monitoring/prometheus.yml`
- **Grafana**：`monitoring/grafana/`

## 环境变量

### 必需环境变量
```bash
# 生产环境
SECRET_KEY=your-secret-key
ALLOWED_ORIGINS=["https://yourdomain.com"]
GRAFANA_PASSWORD=your-grafana-password
```

### 可选环境变量
```bash
# 数据库
DATABASE_URL=sqlite:///./data/runtime/bilingual_cms.db

# 应用配置
ENVIRONMENT=production
LOG_LEVEL=INFO
WORKERS=4
```

## 安全考虑

### 1. 密钥管理
- 使用 GitHub Secrets 存储敏感信息
- 生产环境密钥通过环境变量注入
- 定期轮换密钥

### 2. 镜像安全
- 使用官方基础镜像
- 定期更新依赖包
- 扫击镜像漏洞

### 3. 部署安全
- 限制部署权限
- 使用最小权限原则
- 审计部署日志

## 使用指南

### 本地开发
```bash
# 启动开发环境
docker-compose up -d

# 运行测试
cd backend
pytest tests/ -v

# 代码检查
flake8 app/
bandit -r app/
```

### 测试环境部署
```bash
# 部署到测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行冒烟测试
curl -f http://localhost:8001/health
```

### 生产环境部署
```bash
# 部署到生产环境
docker-compose -f docker-compose.prod.yml up -d

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 监控访问
- **Prometheus**：http://localhost:9090
- **Grafana**：http://localhost:3001

## 故障排除

### 常见问题

#### 1. 测试失败
```bash
# 查看详细测试输出
pytest tests/ -v --tb=long

# 检查测试覆盖率
pytest tests/ --cov=app --cov-report=html
```

#### 2. Docker 构建失败
```bash
# 清理构建缓存
docker builder prune

# 重新构建
docker-compose build --no-cache
```

#### 3. 部署失败
```bash
# 查看容器日志
docker-compose logs backend

# 检查容器状态
docker-compose ps
```

### 监控问题
```bash
# 检查 Prometheus 目标
curl http://localhost:9090/api/v1/targets

# 检查 Grafana 数据源
curl http://localhost:3001/api/datasources
```

## 性能优化

### 1. 构建优化
- 使用多阶段构建
- 利用构建缓存
- 优化镜像大小

### 2. 测试优化
- 并行执行测试
- 缓存依赖包
- 增量测试

### 3. 部署优化
- 滚动更新
- 健康检查
- 资源限制

## 维护和更新

### 定期任务
- **依赖更新**：每月更新依赖包
- **安全扫描**：每周运行安全扫描
- **性能测试**：每月运行性能测试

### 版本管理
- **语义版本**：遵循 SemVer 规范
- **变更日志**：维护 CHANGELOG.md
- **发布标签**：使用 Git 标签

## 联系和支持

- **团队**：工程保障团队
- **负责人**：SRE 工程师
- **文档**：项目 Wiki
- **问题**：GitHub Issues
