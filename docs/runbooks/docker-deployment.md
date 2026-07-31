# Docker 部署运维手册

**版本**: 1.0  
**最后更新**: 2026-07-23  
**维护人**: SRE 团队

---

## 目录

1. [部署前准备](#1-部署前准备)
2. [首次部署](#2-首次部署)
3. [日常运维](#3-日常运维)
4. [故障排查](#4-故障排查)
5. [回滚操作](#5-回滚操作)
6. [监控配置](#6-监控配置)
7. [备份与恢复](#7-备份与恢复)

---

## 1. 部署前准备

### 1.1 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Docker | 20.10+ | 24.0+ |
| Docker Compose | 2.0+ | 2.20+ |
| 磁盘空间 | 2GB | 5GB+ |
| 内存 | 2GB | 4GB+ |

### 1.2 配置文件检查

```bash
# 验证 docker-compose.yml 语法
docker compose config

# 检查环境变量
cat .env

# 确认数据目录存在
ls -la data/
```

### 1.3 必需文件

```
project-root/
├── docker-compose.yml          # 主编排文件
├── .env                        # 环境变量
├── backend/
│   ├── Dockerfile              # 后端镜像构建
│   ├── requirements.txt        # Python 依赖
│   └── .env                    # 后端环境变量
└── data/
    └── dictionary.json         # 术语词典数据
```

---

## 2. 首次部署

### 2.1 构建镜像

```bash
# 进入项目目录
cd /path/to/bilingual-product-cms

# 构建后端镜像
docker compose build --no-cache backend

# 验证镜像构建成功
docker images | grep bilingual
```

### 2.2 启动服务

```bash
# 启动所有服务
docker compose up -d

# 查看启动状态
docker compose ps

# 查看启动日志
docker compose logs -f backend
```

### 2.3 验证部署

```bash
# 检查健康状态
curl http://localhost:8000/health

# 预期响应
{
  "status": "healthy",
  "database": "connected",
  "timestamp": 1234567890.123
}

# 检查 API 文档
curl http://localhost:8000/docs
```

### 2.4 初始化数据库

数据库会在容器首次启动时自动初始化：

```bash
# 查看初始化日志
docker compose logs backend | grep "Database initialized"

# 预期输出
Database initialized:
  Users: 1
  Terms: xxx
  Products: 0
```

---

## 3. 日常运维

### 3.1 查看服务状态

```bash
# 查看运行中的容器
docker compose ps

# 查看资源使用
docker stats --no-stream

# 查看特定服务日志
docker compose logs --tail=100 -f backend
```

### 3.2 重启服务

```bash
# 重启后端服务
docker compose restart backend

# 完全重启（停止后启动）
docker compose down
docker compose up -d
```

### 3.3 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建镜像
docker compose build backend

# 滚动更新
docker compose up -d --force-recreate backend

# 验证更新
curl http://localhost:8000/health
```

### 3.4 查看数据卷

```bash
# 列出卷
docker volume ls | grep bilingual

# 查看卷详情
docker volume inspect bilingual-product-cms_cms-data
```

---

## 4. 故障排查

### 4.1 常见问题

#### 问题：容器无法启动

```bash
# 查看容器状态
docker compose ps -a

# 查看错误日志
docker compose logs backend | tail -50

# 常见原因：
# 1. 端口被占用
netstat -tulpn | grep 8000

# 2. 数据目录权限问题
ls -la data/

# 3. 环境变量缺失
docker compose config
```

#### 问题：健康检查失败

```bash
# 手动测试健康端点
curl -v http://localhost:8000/health

# 进入容器调试
docker compose exec backend bash

# 在容器内测试
python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
```

#### 问题：数据库连接错误

```bash
# 检查数据库文件
ls -la data/runtime/

# 查看数据库日志
docker compose logs backend | grep -i "database\|sqlite"

# 检查环境变量
docker compose exec backend env | grep DATABASE
```

### 4.2 日志分析

```bash
# 实时日志
docker compose logs -f

# 按时间过滤
docker compose logs --since="2026-07-23T10:00:00" backend

# 搜索错误
docker compose logs backend | grep -i "error\|exception"
```

### 4.3 容器调试

```bash
# 进入运行中的容器
docker compose exec backend bash

# 查看进程
docker compose exec backend ps aux

# 检查网络连接
docker compose exec backend curl http://localhost:8000/health

# 查看磁盘使用
docker compose exec backend df -h
```

---

## 5. 回滚操作

### 5.1 回滚到上一版本

```bash
# 查看镜像历史
docker images | grep bilingual

# 停止当前版本
docker compose down

# 使用旧版本镜像启动
# 假设旧镜像标签为 bilingual-product-cms-backend:previous
docker compose up -d --force-recreate backend
```

### 5.2 回滚数据库

```bash
# 如果需要回滚数据库，使用备份恢复
# 参考 database-backup.md 文档

# 恢复数据库
cp backups/bilingual_cms_YYYYMMDD.db data/runtime/bilingual_cms.db

# 重启服务
docker compose restart backend
```

### 5.3 完全回滚

```bash
# 1. 停止所有服务
docker compose down

# 2. 恢复代码到指定版本
git checkout <commit-hash>

# 3. 恢复数据库备份
cp backups/database_YYYYMMDD.db data/runtime/bilingual_cms.db

# 4. 重新构建并启动
docker compose build --no-cache
docker compose up -d
```

---

## 6. 监控配置

### 6.1 启动监控服务

```bash
# 启动 Prometheus + Grafana
docker compose -f deploy/monitoring/docker-compose.monitoring.yml up -d

# 访问 Prometheus
# http://localhost:9090

# 访问 Grafana
# http://localhost:3001
# 用户名: admin
# 密码: admin
```

### 6.2 监控端点

| 端点 | 用途 |
|------|------|
| `/health` | 健康检查 |
| `/metrics` | 应用指标 (JSON) |
| `/metrics/prometheus` | Prometheus 格式指标 |

### 6.3 Prometheus 配置

```yaml
# deploy/monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'bilingual-product-cms-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### 6.4 关键指标

- `app_requests_total` - 总请求数
- `app_errors_total` - 错误总数
- `app_response_time_seconds` - 平均响应时间
- `system_cpu_percent` - CPU 使用率
- `system_memory_percent` - 内存使用率

---

## 7. 备份与恢复

### 7.1 数据备份

```bash
# 备份数据库
docker compose exec backend python -c "
import shutil
import datetime
dt = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy('/app/data/runtime/bilingual_cms.db', f'/app/data/backup_{dt}.db')
print(f'Backup created: backup_{dt}.db')
"

# 复制备份到宿主机
docker cp $(docker compose ps -q backend):/app/data/backup_*.db ./backups/
```

### 7.2 数据恢复

```bash
# 停止服务
docker compose stop backend

# 复制备份到容器
docker cp ./backups/backup_YYYYMMDD.db $(docker compose ps -q backend):/app/data/runtime/bilingual_cms.db

# 启动服务
docker compose start backend
```

### 7.3 定期备份

建议设置 cron 定期备份：

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * /path/to/backup-script.sh
```

---

## 8. 安全建议

### 8.1 生产环境配置

```bash
# 1. 修改默认密码
# 编辑 deploy/monitoring/docker-compose.monitoring.yml
# 修改 GF_SECURITY_ADMIN_PASSWORD

# 2. 限制 CORS
# 编辑 .env
ALLOWED_ORIGINS=["https://yourdomain.com"]

# 3. 使用 HTTPS
# 配置 nginx 反向代理 + SSL 证书
```

### 8.2 网络安全

```bash
# 仅暴露必要端口
# docker-compose.yml 中只映射 8000 端口

# 使用 Docker 网络隔离
docker network ls | grep bilingual
```

---

## 附录

### A. 有用命令速查

```bash
# 状态查看
docker compose ps
docker compose logs -f
docker stats --no-stream

# 服务管理
docker compose up -d
docker compose down
docker compose restart

# 镜像管理
docker compose build
docker image prune

# 清理
docker system prune -a
docker volume prune
```

### B. 配置文件位置

| 文件 | 用途 |
|------|------|
| `docker-compose.yml` | 主编排配置 |
| `.env` | 环境变量 |
| `backend/Dockerfile` | 镜像构建 |
| `backend/requirements.txt` | Python 依赖 |
| `data/dictionary.json` | 术语词典 |
| `deploy/monitoring/` | 监控配置 |

### C. 联系方式

- **SRE 团队**: sre-team@company.com
- **技术支持**: support@company.com

---

**文档维护**: 请在每次部署配置变更后更新此文档
