# 备份策略文档

## 概述

本文档详细说明跨境产品资料中英对照系统的数据备份策略，包括备份目标、备份策略、恢复流程和监控机制。

> **注意**：以下路径基于 Docker Compose 部署（DATABASE_URL=sqlite:///./data/runtime/bilingual_cms.db）  
> 本地开发模式（sqlite:///./bilingual_cms.db）时请将路径中的 /app/data/runtime/ 替换为项目根目录。

## 备份目标

### 数据重要性分级

#### 关键数据（必须备份）
1. **用户数据**：用户账户、权限信息
2. **产品数据**：产品信息、分类、属性
3. **术语数据**：术语词典、分类、同义词
4. **审计日志**：操作记录、用户行为

#### 重要数据（建议备份）
1. **系统配置**：系统设置、环境变量
2. **用户配置**：用户偏好设置
3. **导入文件**：上传的CSV/Excel文件

#### 临时数据（可选备份）
1. **缓存数据**：临时缓存、会话数据
2. **日志文件**：应用日志、访问日志

## 备份策略

### 1. 数据库备份

#### 全量备份
- **频率**：每日凌晨2:00
- **保留期**：30天
- **存储位置**：本地 + 远程存储
- **压缩**：启用gzip压缩
- **加密**：启用AES-256加密

#### 增量备份
- **频率**：每小时
- **保留期**：7天
- **存储位置**：本地存储
- **压缩**：启用gzip压缩

#### 事务日志备份
- **频率**：每5分钟
- **保留期**：3天
- **存储位置**：本地存储

### 2. 文件备份

#### 上传文件备份
- **频率**：每日凌晨3:00
- **保留期**：30天
- **存储位置**：远程存储
- **增量备份**：启用

#### 配置文件备份
- **频率**：每次配置变更
- **保留期**：永久
- **存储位置**：版本控制系统
- **版本管理**：Git

### 3. 日志备份

#### 应用日志备份
- **频率**：每日凌晨4:00
- **保留期**：90天
- **存储位置**：远程存储
- **压缩**：启用gzip压缩

#### 访问日志备份
- **频率**：每日凌晨4:00
- **保留期**：90天
- **存储位置**：远程存储
- **压缩**：启用gzip压缩

## 备份实现

### 统一备份脚本

项目提供了 `scripts/backup.sh`，自动识别数据库类型（PostgreSQL / SQLite）并执行备份。

```bash
# 使用 Docker Compose 环境变量运行备份
docker compose exec -T backend bash scripts/backup.sh
```

备份文件输出到 `./backups/` 目录，文件命名格式：
- PostgreSQL：`bilingual_cms_YYYYMMDD_HHMMSS.sql.gz`
- SQLite：`bilingual_cms_YYYYMMDD_HHMMSS.db`

也可在容器外直接使用 Python 版备份工具：

```bash
python scripts/backup.py --database-url "$DATABASE_URL" --action backup
```

### 备份脚本位置

| 脚本 | 路径 | 说明 |
|------|------|------|
| Shell 备份 | `scripts/backup.sh` | Bash 脚本，支持 PostgreSQL (pg_dump → .sql.gz) 和 SQLite (.backup → .db) |
| Python 备份 | `scripts/backup.py` | Python 脚本，支持 backup / list / cleanup / verify 子命令 |

### 文件备份脚本

```python
import os
import shutil
import tarfile
from datetime import datetime

def backup_files(source_dir, backup_dir):
    """文件备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/files_backup_{timestamp}.tar.gz"
    
    with tarfile.open(backup_file, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))
    
    return backup_file
```

### 备份验证脚本

```python
import os
import sqlite3
import subprocess

def verify_backup(backup_file):
    """验证备份文件完整性"""
    if backup_file.endswith('.db'):
        # SQLite备份验证
        conn = sqlite3.connect(backup_file)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()
        return result[0] == 'ok'
    
    elif backup_file.endswith('.sql'):
        # PostgreSQL备份验证
        cmd = ["pg_restore", "--list", backup_file]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    
    return False
```

## 备份存储

### 存储层级

#### 本地存储
- **位置**：`/backup/local/`
- **用途**：快速恢复、临时存储
- **容量**：100GB
- **保留期**：7天

#### 远程存储
- **位置**：云存储服务（AWS S3/阿里云OSS）
- **用途**：长期存储、灾难恢复
- **容量**：1TB
- **保留期**：1年

#### 归档存储
- **位置**：冷存储服务
- **用途**：合规要求、历史数据
- **容量**：无限
- **保留期**：永久

### 存储加密

#### 加密算法
- **算法**：AES-256
- **密钥管理**：使用密钥管理服务（KMS）
- **加密位置**：传输中 + 静态

#### 密钥轮换
- **频率**：每90天
- **策略**：新密钥加密新数据，旧密钥解密旧数据
- **备份**：密钥备份到安全位置

## 恢复流程

> **重要**：以下恢复步骤使用 `docker compose cp` 将备份文件从宿主机复制到容器内，避免 "stop + exec" 错误（`docker compose exec` 只能在运行中的容器执行）。

### 1. 数据库恢复

#### SQLite 恢复

备份文件格式：`bilingual_cms_YYYYMMDD_HHMMSS.db`（由 `scripts/backup.sh` 生成）

```bash
# 1. 停止应用服务
docker compose stop backend

# 2. 将备份文件复制到容器内的数据库路径
docker compose cp /path/to/backups/bilingual_cms_20240101_020000.db backend:/app/data/runtime/bilingual_cms.db

# 3. 启动应用服务
docker compose start backend

# 4. 验证恢复结果
curl -f http://localhost:8000/health
```

#### PostgreSQL 恢复

备份文件格式：`bilingual_cms_YYYYMMDD_HHMMSS.sql.gz`（由 `scripts/backup.sh` 生成，pg_dump --clean 压缩输出）

```bash
# 1. 将备份文件复制到 postgres 容器
docker compose cp /path/to/backups/bilingual_cms_20240101_020000.sql.gz postgres:/tmp/restore.sql.gz

# 2. 解压并恢复到数据库（postgres 容器保持运行）
docker compose exec -T postgres bash -c "gunzip -c /tmp/restore.sql.gz | psql -U \${POSTGRES_USER:-postgres} -d \${POSTGRES_DB:-bilingual_cms}"

# 3. 清理容器内临时文件
docker compose exec postgres rm -f /tmp/restore.sql.gz

# 4. 重启 backend 以重新连接数据库
docker compose restart backend

# 5. 验证恢复结果
curl -f http://localhost:8000/health
```

### 2. 文件恢复

```bash
# 1. 将备份文件复制到容器并解压（服务保持运行）
docker compose cp /path/to/backups/files_backup_20240101_030000.tar.gz backend:/tmp/restore.tar.gz
docker compose exec backend tar -xzf /tmp/restore.tar.gz -C /app/data/
docker compose exec backend rm -f /tmp/restore.tar.gz

# 2. 重启应用服务以加载恢复的文件
docker compose restart backend
```

### 3. 完整系统恢复

```bash
# 1. 停止所有服务
docker compose down

# 2. 恢复数据库（参考上述 SQLite 或 PostgreSQL 恢复步骤）
# 先启动数据库服务：
docker compose up -d postgres  # PostgreSQL
# 或只启 backend（SQLite 模式）：
docker compose up -d backend

# 3. 按对应步骤执行数据库恢复

# 4. 恢复文件（参考文件恢复步骤）

# 5. 重新启动全部服务
docker compose up -d

# 6. 验证系统状态
curl -f http://localhost:8000/health
```

### 恢复后验证

恢复完成后，建议执行以下验证步骤确保数据完整性：

```bash
# 1. 健康检查
curl -f http://localhost:8000/health

# 2. 运行后端测试套件（健康检查相关）
pytest backend/tests/ -k "test_health" -v

# 3. 验证数据可读性
curl -s http://localhost:8000/api/v1/products?limit=5 \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" | jq -r '.access_token')" | jq '.total'
```

## 备份监控

### 监控指标

#### 备份成功率
- **指标**：`backup_success_total`
- **告警阈值**：< 95%
- **检查频率**：每日

#### 备份时长
- **指标**：`backup_duration_seconds`
- **告警阈值**：> 1小时
- **检查频率**：每次备份

#### 备份大小
- **指标**：`backup_size_bytes`
- **监控**：趋势分析
- **检查频率**：每日

#### 存储使用率
- **指标**：`storage_usage_percent`
- **告警阈值**：> 80%
- **检查频率**：每日

### 告警配置

#### 备份失败告警
- **级别**：严重
- **通知**：邮件 + Slack + 短信
- **响应时间**：15分钟

#### 存储空间告警
- **级别**：警告
- **通知**：邮件 + Slack
- **响应时间**：4小时

#### 备份超时告警
- **级别**：警告
- **通知**：邮件 + Slack
- **响应时间**：1小时

## 备份测试

### 测试频率
- **恢复测试**：每月一次
- **完整性测试**：每日一次
- **性能测试**：每季度一次

### 测试内容

#### 恢复测试
1. 选择随机备份文件
2. 在测试环境恢复
3. 验证数据完整性
4. 测试应用功能
5. 记录测试结果

#### 完整性测试
1. 检查备份文件完整性
2. 验证加密解密
3. 检查压缩解压
4. 验证文件权限

#### 性能测试
1. 测量备份时间
2. 测量恢复时间
3. 分析存储使用
4. 优化备份策略

## 备份策略优化

### 1. 备份时间优化
- 使用增量备份减少备份时间
- 并行执行多个备份任务
- 调整备份窗口避开业务高峰

### 2. 存储优化
- 使用压缩减少存储空间
- 实施数据分层存储
- 定期清理过期备份

### 3. 恢复优化
- 实施快速恢复机制
- 使用快照技术
- 优化恢复流程

## 合规要求

### 数据保留要求
- **财务数据**：7年
- **用户数据**：3年
- **审计日志**：1年
- **系统配置**：永久

### 备份要求
- **备份频率**：每日
- **备份验证**：每日
- **恢复测试**：每月
- **文档更新**：每季度

### 安全要求
- **加密**：AES-256
- **访问控制**：最小权限原则
- **审计**：备份操作审计
- **监控**：实时监控备份状态

## 文档维护

### 更新频率
- **策略文档**：每季度
- **操作手册**：每月
- **配置文档**：每次变更
- **测试报告**：每次测试

### 版本控制
- 使用Git管理文档
- 记录变更历史
- 审批流程
- 发布管理
