# 快速开始指南

## 🚀 5分钟快速启动

### 方式一：Docker 快速启动（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-username/bilingual-product-cms.git
cd bilingual-product-cms

# 2. 配置环境变量（必做！）
cp .env.example .env
# 生成 SECRET_KEY（Linux/Mac）
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env
# Windows PowerShell:
# (Get-Content .env) -replace '^SECRET_KEY=.*', ('SECRET_KEY=' + -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})) | Set-Content .env

# 3. 启动服务（基础 compose：仅 backend API + PostgreSQL，不含前端/nginx/Grafana）
docker compose up -d

# 4. 访问系统
# API 服务: http://localhost:8000
# API 文档: http://localhost:8000/docs
# 健康检查: http://localhost:8000/health

# 如需完整前端 UI，请使用全栈 compose：
# docker compose -f docker-compose.full.yml up -d --build
# 详见 docker-compose.full.yml 注释
```

### 方式二：本地开发环境

#### 环境要求
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (可选，可使用SQLite)
- Redis 7+ (可选)

#### 后端设置
```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
python init_db.py

# 5. 启动后端服务
uvicorn app.main:app --reload --port 8000
```

#### 前端设置
```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动前端服务
npm run dev
```

## 🔧 配置说明

### 环境变量配置
复制 `.env.example` 到 `.env` 并修改配置：

```bash
cp .env.example .env
```

主要配置项：
```env
# 数据库配置
DATABASE_URL=sqlite:///./bilingual_cms.db
# 或 PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/bilingual_cms

# 安全配置
SECRET_KEY=your-secret-key-here-at-least-32-characters

# 管理员配置
ADMIN_EMAIL=admin@bilingual-cms.com
ADMIN_PASSWORD=your-secure-password

# Redis配置（可选）
REDIS_URL=redis://localhost:6379/0
```

### Docker 配置
使用 `docker-compose.prod.yml` 进行生产环境部署：

```bash
# 1. 复制生产环境配置
cp .env.example .env.production

# 2. 修改生产环境配置
vi .env.production

# 3. 启动生产环境
docker compose -f docker-compose.prod.yml up -d
```

## 📚 核心功能

### 1. 产品管理
- 创建、编辑、删除产品
- 产品参数中英文对照
- 批量导入导出

### 2. 术语词典
- 内置300+专业术语
- 自定义术语管理
- 术语一致性检测

### 3. 用户权限
- 基于角色的访问控制 (RBAC)
- 多用户协作
- 操作审计日志

### 4. 数据导出
- CSV格式导出
- 多平台模板支持
- 数据一致性检测

## 🧪 测试

### 运行测试
```bash
# 后端测试
cd backend
pytest --cov=app --cov-report=term-missing

# 前端测试
cd frontend
npm test

# 端到端测试
npm run test:e2e
```

### 测试覆盖率
```bash
# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 查看报告
open htmlcov/index.html
```

## 🚀 部署

### 生产环境部署
```bash
# 1. 准备环境
cp .env.example .env.production
vi .env.production

# 2. 启动服务
docker compose -f docker-compose.prod.yml up -d

# 3. 初始化数据库
docker compose -f docker-compose.prod.yml exec backend python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"

# 4. 验证部署
curl http://localhost:8000/health
```

### 监控部署
```bash
# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f

# 访问监控面板
# Grafana: https://localhost/grafana (via nginx reverse proxy)
# Prometheus: http://localhost:9090 (internal only)
```

## 🔍 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库服务
docker compose ps

# 查看数据库日志
docker compose logs postgres

# 重启数据库服务
docker compose restart postgres
```

#### 2. Redis连接失败
```bash
# 检查Redis服务
docker compose ps

# 查看Redis日志
docker compose logs redis

# 测试Redis连接
docker compose exec redis redis-cli ping
```

#### 3. 前端构建失败
```bash
# 清理缓存
cd frontend
rm -rf node_modules .next
npm install

# 重新构建
npm run build
```

#### 4. 测试失败
```bash
# 清理测试缓存
cd backend
rm -rf .pytest_cache __pycache__
pytest --cache-clear
```

## 📖 API 使用示例

### 用户认证
```bash
# 用户登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bilingual-cms.com", "password": "your-password"}'

# 获取用户信息
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 产品管理
```bash
# 创建产品
curl -X POST http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "TEST-001",
    "product_name_zh": "测试产品",
    "product_name_en": "Test Product",
    "category": "通用属性"
  }'

# 获取产品列表
curl -X GET http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'feat: Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

详细信息请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📞 获取帮助

- **GitHub Issues**: 报告问题和功能请求
- **文档**: 查看项目文档
- **社区**: 参与讨论

## 📝 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新信息。

---

**祝您使用愉快！** 🎉