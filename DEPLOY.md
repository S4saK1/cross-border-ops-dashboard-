# 部署指南

## 本地开发

```bash
cd backend
pip install -r requirements.txt
python init_db.py
python -m uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

默认管理员：admin@bilingual-product-cms.com（密码由环境变量ADMIN_PASSWORD设置，首次登录需修改密码）

## Docker 部署

### 前置条件
- Docker Desktop 已安装
- Docker Compose v2+ 已安装

### 环境变量配置

`docker compose` 启动时需要 `SECRET_KEY`。从 `.env.example` 创建 `.env` 文件：

```bash
# 复制模板并生成安全密钥
cp .env.example .env
# Linux/Mac: 自动替换 SECRET_KEY
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env
# Windows: 手动编辑 .env，或用 PowerShell 替换（见 README.md）
```

> **重要**：`.env` 必须在启动容器前配置完成。`SECRET_KEY` 为必填项（docker-compose.yml 使用 `${SECRET_KEY:?}` 校验），缺少会导致启动失败。详见 `.env.example` 中的全部配置项。

### 一键启动

```bash
docker compose up -d --build
```

### 验证

```bash
# 检查容器状态
docker compose ps

# 查看日志
docker compose logs -f backend

# 测试健康检查
curl http://localhost:8000/health
```

### 停止

```bash
docker compose down
```

### 数据持久化

SQLite 数据库存储在 Docker volume `cms-data` 中，重启不会丢失数据。

## 生产环境建议

### 1. 替换 SECRET_KEY

```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 2. 配置 CORS 白名单

修改 `docker-compose.yml` 中的 `ALLOWED_ORIGINS`。

### 3. 使用反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. 数据备份

```bash
# 备份 SQLite 数据库
docker compose exec backend python -c "
import shutil
shutil.copy('/app/data/runtime/bilingual_cms.db', '/app/data/runtime/backup.db')
print('Backup created')
"

# 或导出为 SQL
docker compose exec backend python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    # SQLite 导出
    pass
"
```

### 5. 迁移到 PostgreSQL（参考 ADR-006）

安装驱动：
pip install psycopg2-binary

修改 .env 或环境变量：
`
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bilingual_product_cms
`

使用 Alembic 管理迁移：
`ash
cd backend
alembic revision --autogenerate -m "initial_migration"
alembic upgrade head
`

验证连接：
`ash
python -c "from app.database import engine; engine.connect()"
`

生产环境使用 Docker Compose，确保 postgres 服务启用了 DATABASE_URL 环境变量。

修改 `.env`：
```
DATABASE_URL=postgresql://user:password@localhost:5432/bilingual_cms
```

安装驱动：
```bash
pip install psycopg2-binary
```
