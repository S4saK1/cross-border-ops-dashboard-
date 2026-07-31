# 跨境产品资料中英对照系统

[![Build Status](https://img.shields.io/github/workflow/status/liaogengqin-creator/bilingual-product-cms/CI?label=build)](https://github.com/liaogengqin-creator/bilingual-product-cms/actions)
[![Test Coverage](https://img.shields.io/codecov/c/github/liaogengqin-creator/bilingual-product-cms?label=coverage)](https://codecov.io/gh/liaogengqin-creator/bilingual-product-cms)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

> 不是翻译工具，是跨境卖家的产品资料一致性管理系统

## 项目简介

这是一个专为跨境卖家设计的产品资料一致性管理系统，帮助卖家维护产品参数的中英文对照关系，确保在全球电商平台上的产品资料准确、一致、专业。

### 项目特点

- **术语一致性**：通过术语词典确保产品参数的中英文翻译一致性
- **批量管理**：支持CSV批量导入产品数据，提高工作效率
- **质量检测**：自动检测产品资料的中英文对照一致性
- **权限管理**：基于角色的访问控制（RBAC），支持多用户协作
- **审计追踪**：完整记录所有操作日志，便于追溯和审计
- **现代化界面**：基于React/Next.js的响应式Web界面

## 技术栈

### 后端
- **框架**：Python FastAPI
- 数据库：PostgreSQL（生产环境） / SQLite（默认开发环境）
- **缓存**：Redis（Token黑名单、会话存储）
- **认证**：JWT（JSON Web Tokens）+ httpOnly Cookie
- **密码加密**：bcrypt
- **API文档**：自动生成的OpenAPI/Swagger文档

### 前端
- **框架**：Next.js 14 + React 18
- **样式**：Tailwind CSS
- **语言**：TypeScript
- **状态管理**：React Context + Hooks

### 部署
- **容器化**：Docker + Docker Compose
- **反向代理**：Nginx（生产环境推荐）
- **监控**：Prometheus + Grafana
- **日志**：结构化JSON日志

### 测试
- **后端测试**：pytest + httpx
- **前端测试**：Jest + React Testing Library
- **端到端测试**：Playwright
- **性能测试**：Locust/k6
- **图标**：Lucide React


## 快速开始

### 本地开发

#### 1. 克隆项目
```bash
git clone <repository-url>
cd bilingual-product-cms
```

#### 2. 启动后端服务
```bash
cd backend
pip install -r requirements.txt
python init_db.py
python -m uvicorn app.main:app --reload --port 8000
```

#### 3. 启动前端开发服务器
```bash
cd frontend
npm install
npm run dev
```

#### 4. 访问系统
- 前端界面：http://localhost:3000
- API文档：http://localhost:8000/docs
- 默认管理员：admin@bilingual-product-cms.com（密码由环境变量ADMIN_PASSWORD设置，首次登录需修改密码）

### Docker部署

#### 前置条件
- Docker Desktop 已安装
- Docker Compose v2+ 已安装

#### 环境配置

`docker compose` 启动时需要 `SECRET_KEY` 环境变量。从 `.env.example` 创建 `.env` 文件：

```bash
# 复制环境变量模板
cp .env.example .env

# 生成安全密钥（Linux/Mac）
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env

# Windows PowerShell
(Get-Content .env) -replace '^SECRET_KEY=.*', ('SECRET_KEY=' + -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})) | Set-Content .env
```

#### 一键启动
```bash
docker compose up -d --build
```

#### 验证部署
```bash
# 检查容器状态
docker compose ps

# 查看日志
docker compose logs -f backend

# 测试健康检查
curl http://localhost:8000/health
```

#### 停止服务
```bash
docker compose down
```

#### 数据持久化
开发环境默认使用 SQLite（`bilingual_cms.db`），生产环境可配置为 PostgreSQL。

## 功能特性

### 1. 产品参数管理
- 产品参数的中英文对照CRUD操作
- 支持产品分类和标签管理
- 产品图片和附件上传

### 2. 术语词典管理
- 专业术语的中英文对照维护
- 术语分类和标签系统
- 内置术语词典支持

### 3. 术语一致性检测
- 自动检测产品参数与术语词典的一致性
- 一致性评分和问题报告
- 修复建议和批量更新

### 4. CSV数据导入导出
- 支持CSV格式批量导入产品数据
- 产品数据导出为CSV格式
- 数据模板下载功能

### 5. 用户权限管理
- 多角色权限控制（admin/editor/reviewer/viewer）
- 用户注册和登录系统
- 个人资料管理

### 6. 审计日志
- 操作日志记录
- 用户行为追踪
- 系统变更历史

## API文档

### 认证API
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/refresh` - 刷新令牌
- `POST /api/v1/auth/logout` - 用户登出
- `POST /api/v1/auth/logout-all` - 撤销所有令牌
- `GET /api/v1/auth/me` - 获取当前用户信息
- `POST /api/v1/auth/change-password` - 修改密码

### 产品管理API
- `GET /api/v1/products` - 产品列表查询
- `POST /api/v1/products` - 创建产品
- `GET /api/v1/products/{id}` - 产品详情
- `PUT /api/v1/products/{id}` - 更新产品
- `DELETE /api/v1/products/{id}` - 删除产品

### 术语词典API
- `GET /api/v1/terms` - 术语列表查询
- `POST /api/v1/terms` - 创建术语

### 用户管理API (Admin only)
- `GET /api/v1/users` - 用户列表
- `POST /api/v1/users` - 创建用户
- `GET /api/v1/users/me` - 当前用户信息
- `GET /api/v1/users/{id}` - 用户详情
- `PUT /api/v1/users/{id}` - 更新用户
- `DELETE /api/v1/users/{id}` - 删除用户
- `PUT /api/v1/users/{id}/role` - 更改用户角色
- `POST /api/v1/users/{id}/reset-password` - 重置用户密码
- `POST /api/v1/users/bulk` - 批量用户操作

### 导出API
- `POST /api/v1/export/csv` - 导出产品数据为CSV (Amazon/Alibaba)

### 导入API
- `POST /api/v1/import/upload` - 上传导入文件
- `POST /api/v1/import/preview` - 预览导入数据
- `POST /api/v1/import/execute` - 执行批量导入

### 审计日志API
- `GET /api/v1/audit-logs` - 审计日志查询

## 测试说明

### 后端测试
```bash
cd backend
pytest
```

### 前端测试
```bash
cd frontend
npm run lint
```

### 端到端测试
```bash
# 启动服务后运行测试
docker compose up -d
python test_password_validation.py
```

## 贡献指南

我们欢迎任何形式的贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

### 快速开始
1. Fork 项目仓库
2. 克隆到本地：`git clone https://github.com/your-username/bilingual-product-cms.git`
3. 安装依赖：`pip install -r requirements.txt && cd frontend && npm install`
4. 创建功能分支：`git checkout -b feature/your-feature`
5. 提交更改：`git commit -m 'feat: Add some feature'`
6. 推送到分支：`git push origin feature/your-feature`
7. 创建 Pull Request

### 开发环境
```bash
# 后端开发
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload

# 前端开发
cd frontend
npm install
npm run dev
```

### 代码规范
- **Python**：遵循 PEP 8，使用类型注解
- **TypeScript**：严格模式，ESLint + Prettier
- **提交信息**：遵循 [Conventional Commits](https://www.conventionalcommits.org/)
- **测试**：新功能必须包含测试用例

### 问题反馈
- 使用 [GitHub Issues](https://github.com/your-username/bilingual-product-cms/issues) 报告问题
- 提供详细的问题描述和复现步骤
- 附上相关日志和错误信息
- 使用提供的Issue模板

### 行为准则
本项目遵循 [Contributor Covenant 行为准则](CODE_OF_CONDUCT.md)。参与本项目即表示您同意遵守此准则。

## 生产环境部署

### 安全配置
1. **替换默认密钥**：
   ```bash
   export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

2. **配置CORS白名单**：修改 `docker-compose.yml` 中的 `ALLOWED_ORIGINS`

3. **使用HTTPS**：配置Nginx反向代理并启用SSL

### 数据备份
```bash
# 备份SQLite数据库
docker compose exec backend python -c "
import shutil
shutil.copy('/app/data/runtime/bilingual_cms.db', '/app/data/runtime/backup.db')
print('Backup created')
"
```

### 数据库迁移
### 数据库切换
开发环境默认使用 SQLite。如需切换到 PostgreSQL：
2. 安装 `psycopg2-binary` 驱动
3. 运行数据库迁移脚本

## 许可证

本项目采用 MIT 许可证。详情请查看 [LICENSE](LICENSE) 文件。

## 相关文档

- [部署指南](DEPLOY.md)
- [产品需求文档](docs/PRD.md)
- [部署检查清单](docs/deployment-checklist.md)
- [运行手册](docs/runbooks/)

## 联系方式

如有任何问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 发送邮件至项目维护者

---

**注意**：本系统不是通用的翻译工具，而是专门针对跨境卖家的产品资料一致性管理解决方案。我们专注于确保产品参数在不同语言版本间的一致性，而不是进行实时翻译。
