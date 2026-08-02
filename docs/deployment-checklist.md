# 生产环境部署检查清单

**项目**：跨境产品资料中英对照系统
**版本**：v1.0.0
**部署负责人**：DevOps团队
**创建日期**：2026-07-24
**最后更新**：2026-07-31

---

## 📋 部署前检查

### 1. 环境准备
- [ ] 服务器环境准备完成
- [ ] Docker和Docker Compose安装完成
- [ ] 网络配置完成（端口开放、防火墙规则）
- [ ] SSL证书准备完成
- [ ] 域名解析配置完成

### 2. 配置文件检查
- [ ] `.env.production`文件配置正确
- [ ] 数据库连接字符串正确
- [ ] Redis连接配置正确
- [x] ~~密钥和密码已更换为生产环境值~~ → **`SECRET_KEY` 使用 `${SECRET_KEY:?}` 语法强制校验，若未设置则容器启动即报错**
- [ ] CORS配置正确
- [x] `.dockerignore` 已包含 `.env` / `*.db` / `__pycache__` 等敏感文件，防止密钥泄露到镜像层

### 3. 数据库准备
- [ ] PostgreSQL数据库创建完成
- [ ] 数据库用户权限配置正确
- [ ] 数据库备份验证：运行 `bash scripts/backup.sh`，确认退出码为 0，产物存在于 `./backups/` 目录且大小 > 1KB
- [ ] 数据库迁移脚本准备完成

### 4. Redis准备
- [ ] Redis服务部署完成
- [ ] Redis密码配置正确
- [ ] Redis持久化配置完成
- [x] `redis>=5.0.0` 已包含在生产镜像 `requirements.txt` 中
- [ ] Redis监控配置完成

### 5. 监控准备
- [ ] Prometheus配置完成
- [ ] Grafana仪表板配置完成
- [ ] 告警规则配置完成
- [x] Alertmanager 使用 `envsubst` 模板化启动，环境变量自动注入
- [x] `alerts.yml` 已挂载到 Prometheus 容器 (`./monitoring/alerts.yml:/etc/prometheus/alerts.yml:ro`)
- [ ] 告警通知渠道配置完成

### 6. 安全加固 (2026-07-31 更新)
- [x] `SECRET_KEY` 使用 Bash `${SECRET_KEY:?}` 语法 — 未设置时容器立即退出，防止空密钥运行
- [x] `/health` 端点已验证：数据库不可用时返回 HTTP 503（而非 200），负载均衡器可正确摘除不健康节点
- [x] CI 内容门禁 R1-R4 全部通过（字节级损坏扫描：0x08、isolated CR、无LF的.sh、超长行）
- [ ] 确认所有 `.env` / `.env.production` / `.env.example` 中无硬编码生产密钥（仅占位符）

---

## 🚀 部署步骤

### 步骤1：拉取最新代码
```bash
cd /path/to/project
git pull origin main
```

### 步骤2：构建Docker镜像
```bash
# 构建后端镜像（含 redis>=5.0.0）
docker build -t bilingual-product-cms-backend:latest ./backend

# 构建前端镜像
docker build -t bilingual-product-cms-frontend:latest ./frontend
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
# 检查健康状态（DB正常时返回200；DB不可用时返回503）
curl -f http://localhost:8000/health

# 检查API文档
curl -f http://localhost:8000/docs

# 检查监控端点
curl -f http://localhost:8000/metrics
```

---

## 🔍 部署后验证

### 1. 服务验证
- [ ] 后端服务正常运行，`/health` 返回 200
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

### 5. 监控配置验证（手动）
- [ ] `promtool check config ../deploy/monitoring/prometheus.yml` — 确认 Prometheus 配置语法正确
- [ ] `amtool check-config monitoring/alertmanager.yml` — 确认 Alertmanager 配置语法正确
  > 提示：若 CI 环境中未安装 `promtool` / `amtool`，可在本地或部署服务器上执行。安装方式：
  > ```bash
  > # promtool 随 Prometheus 发布包提供
  > # amtool 随 Alertmanager 发布包提供
  > # 或用 Docker 运行：
  > docker run --rm -v $(pwd)/monitoring:/etc/prometheus prom/prometheus:v2.54.1 promtool check config /etc/prometheus/prometheus.yml
  > docker run --rm -v $(pwd)/monitoring:/etc/alertmanager prom/alertmanager:v0.27.0 amtool check-config /etc/alertmanager/alertmanager.yml
  > ```

### 6. CI 内容门禁验证
- [ ] `python scripts/ci-content-gates.py` 退出码为 0（确认 R1-R4 全部通过）
- [ ] `.github/workflows/` 中已配置内容门禁步骤

---

## 🔐 密码轮换（2026-07-31 新增 ⚠️）

> **重要**：`.dockerignore` 修复前构建的历史镜像可能包含明文密钥。本次部署后必须执行以下轮换。

### 轮换清单

| 密钥 | 位置 | 轮换方法 |
|------|------|----------|
| `SECRET_KEY` | `.env.production` | 生成新值：`python -c "import secrets; print(secrets.token_urlsafe(32))"`，更新后重启 backend |
| `POSTGRES_PASSWORD` | `.env.production` | `ALTER USER postgres PASSWORD 'new_password'`，同步更新 `.env.production`，重启 postgres + backend |
| `REDIS_PASSWORD` | `.env.production` | 更新 `requirepass` → `CONFIG SET requirepass newpass` + `CONFIG REWRITE`，同步更新 `.env.production` |
| `GRAFANA_PASSWORD` | `.env.production` | 通过 Grafana UI 或 API 修改管理员密码 |
| `ADMIN_PASSWORD` | `.env.production` | 部署后通过应用内修改管理员密码 |
| SMTP 凭据 | Alertmanager 环境变量 | 更新 SMTP 密码，同步修改 `.env.production` 中对应变量 |

### 轮换步骤
```bash
# 1. 停止所有服务
docker compose -f docker-compose.prod.yml down

# 2. 生成新密钥并更新 .env.production
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# 3. 确认 .dockerignore 包含 .env / .env.production / *.db
cat .dockerignore

# 4. 重新构建镜像（确保不包含旧密钥）
docker compose -f docker-compose.prod.yml build --no-cache

# 5. 启动服务
docker compose -f docker-compose.prod.yml up -d

# 6. 验证
curl -f http://localhost:8000/health
```

### 轮换后验证
- [ ] 所有密钥已更换为新值
- [ ] 新构建的镜像层中不含 `.env` 文件（确认 `.dockerignore` 生效）
- [ ] 旧密钥已失效，无法登录任何服务
- [ ] 备份中不含明文密钥（运行 `bash scripts/backup.sh` 并检查备份文件内容）

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
git checkout <previous-tag>

# 3. 重新构建和部署
docker compose -f docker-compose.prod.yml up -d

# 4. 验证回滚成功（/health 返回 200；若 DB 不可用返回 503）
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
   - 指标：`up{job="backend"}`
   - 告警：服务宕机 → `/health` 返回 503 时由负载均衡器自动摘除

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

6. **磁盘空间**（新增）
   - 指标：Docker 日志大小（已配置 `max-size=10m, max-file=3` 日志轮转）
   - 告警：`system_disk_percent > 80`

### 告警通知
- **邮件通知**：通过 Alertmanager `email-admin` receiver
- **告警抑制**：critical 告警自动抑制同组 warning 告警 (`inhibit_rules`)

---

## 📝 部署记录

### 最近部署
| 日期 | 版本 | 部署人员 | 变更摘要 |
|------|------|----------|----------|
| 2026-07-31 | v1.0.1 | SRE团队 | 安全加固（SECRET_KEY :?守卫、健康检查503、CI内容门禁、密码轮换、日志轮转） |
| 2026-07-24 | v1.0.0 | DevOps团队 | 初始生产部署 |

### 已知问题
1. Redis单实例配置（Sprint 3将升级为集群）
2. 备份脚本需手动执行（Sprint 3将自动化）
3. 性能测试未执行（Sprint 3将执行）
4. Prometheus `alerts.yml` 中的 `app_errors_total` / `app_requests_total` / `app_response_time_seconds` 等指标依赖应用层暴露，需确认后端已实现 `/metrics/prometheus` 端点

---

## ✅ 部署确认

### 部署团队确认
- [ ] DevOps/SRE工程师确认部署完成
- [ ] 后端开发确认功能正常
- [ ] 前端开发确认界面正常
- [ ] QA工程师确认测试通过
- [ ] 产品经理确认业务正常

### 部署签字
- **SRE负责人**：_________________ 日期：_______
- **技术负责人**：_________________ 日期：_______
- **产品负责人**：_________________ 日期：_______

---

> 本检查清单由工程保障团队 AI 协作生成，关键决策请由人类工程负责人复核。
> 部署前请仔细检查所有项目，确保生产环境稳定运行。
> **注意**：密码轮换章节为本次部署的必做项 — 旧镜像中可能存在密钥泄露。
