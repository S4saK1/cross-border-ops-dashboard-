# 分阶段修复执行计划（详细版）

**日期**: 2026-07-31
**基于**: 技术债评估报告 tech-debt-remaining-fixes-2026-07-31.md
**总漏洞数**: 73 项（P0×9 / P1×32 / P2×15 / P3×17）
**阶段**: Sprint-Hotfix（≤2 天）→ Sprint-A（第 1-2 周）→ Sprint-B（第 3-5 周）

---

## 一、Sprint-Hotfix（≤2 天）— 恢复可部署 + 堵核心安全边界

### 涉及漏洞清单（9 项 P0 + 2 项 P1 高优先插队）

| # | 严重度 | 漏洞ID | 简要描述 | 文件位置 |
|---|--------|--------|---------|---------|
| 1 | 🔴 P0 | P0-1 | 生产 nginx 引用 `deploy/nginx/ssl` 证书目录不存在 → nginx 起不来，HTTPS 全站白屏 | prod.yml:210 / deploy/nginx/ |
| 2 | 🔴 P0 | P0-2 | 根 `.env` 含真实 SECRET_KEY，compose 自动读入并注入 prod | .env:2 |
| 3 | 🔴 P0 | P0-3 | alertmanager 邮件链路死配置：无 environment 段 + 镜像无 envsubst | prod.yml:148-165 |
| 4 | 🔴 P0 | P0-5 | refresh token 仍走 JSON body 返回 + 服务端不读 refresh cookie（R4 声称落空） | auth.py:117-118 / security.py:174-209 |
| 5 | 🔴 P0 | P0-6 | /auth/register 开放注册、无限流 → 可批量建号/邮箱枚举 | main.py:146 |
| 6 | 🔴 P0 | P0-7 | 强制改密服务端不拦截：get_current_user 不检查 force_password_change claim | auth.py:92-103 / core/deps.py |
| 7 | 🔴 P0 | P0-4 | 备份无任何调度（cron/ofelia/systemd 均无） | 全仓 |
| 8 | 🔴 P0 | P0-8 | test_terms.py 静默收集 0 测试（3 个 def 误缩进嵌套进 _seed_terms） | test_terms.py:10-40 |
| 9 | 🔴 P0 | P0-9 | 真实覆盖率 69% 已跌破 CI 门槛 70%：pyproject 粉饰排除项虚高 4pp | pyproject.toml:16-26 |
| 10 | 🟠 P1 | H1 | login 端点无 db.commit() → last_login_at 与 user_login 审计回滚丢失 | auth.py:71-113 / database.py:27-32 |
| 11 | 🟠 P1 | H3 | import_.py:386 logger 未定义 → 文件解析失败预期 400 变 500（NameError） | import_.py:386 |

---

### 按依赖关系排序的执行步骤

> **依赖链**：P0-1（nginx 起不来阻塞一切）→ P0-2（密钥治理）→ P0-3（告警链路）→ P0-5/6/7（认证安全边界）→ P0-4（备份调度，依赖 BOM 清理 H2）→ P0-8/9（测试可信度，依赖 nginx 可起 + 与 P0-5/6/7 并行）

---

#### Step 1: P0-1 — nginx TLS 证书就位

**描述**: 生产 nginx 引用 `deploy/nginx/ssl` 证书目录，但该目录不存在，nginx 容器启动即 crash。

**文件位置**: `prod.yml:210` / `deploy/nginx/`

**修复步骤**:

```bash
# 1. 创建证书目录
mkdir -p deploy/nginx/ssl

# 2. 方案A：自签证书（开发/测试环境）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deploy/nginx/ssl/privkey.pem \
  -out deploy/nginx/ssl/fullchain.pem \
  -subj "/CN=localhost"

# 3. 方案B：Let's Encrypt（生产环境）
# certbot certonly --standalone -d your-domain.com
# cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/nginx/ssl/
# cp /etc/letsencrypt/live/your-domain.com/privkey.pem deploy/nginx/ssl/

# 4. 验证 nginx 配置引用路径
grep -n 'ssl_certificate\|ssl_certificate_key' deploy/nginx/nginx.conf

# 5. 在 prod.yml 或部署脚本中增加前置校验
# 在 docker compose up 前：
test -f deploy/nginx/ssl/fullchain.pem || { echo "FATAL: TLS cert missing"; exit 1; }
test -f deploy/nginx/ssl/privkey.pem || { echo "FATAL: TLS key missing"; exit 1; }
```

**验证方法**:
```bash
docker compose -f prod.yml config -q 2>&1    # 配置语法检查
docker compose -f prod.yml up nginx -d        # 单独起 nginx
docker compose -f prod.yml logs nginx         # 确认无 SSL 相关 Fatal
curl -k https://localhost/health              # 确认 HTTPS 可达
```

**完成标准**: `docker compose -f prod.yml up nginx -d` 不 crash，`curl -k https://localhost/health` 返回 200 或 503（后端可能未起）。

**估时**: 30 min

---

#### Step 2: P0-2 — 根 .env 真实密钥治理 + H17 密钥在盘风险

**描述**: 根 `.env` 含真实 SECRET_KEY，compose 自动读入并注入 prod，造成密钥暴露风险。

**文件位置**: `.env:2`、`prod.yml`

**修复步骤**:

```bash
# 1. 确认当前根 .env 含真实密钥
grep SECRET_KEY .env

# 2. 根 .env 改为占位值
# 编辑 .env:2，将 SECRET_KEY=真实值 → SECRET_KEY=__CHANGE_ME__REPLACE_WITH_REAL_KEY__

# 3. prod compose 增加必填校验
# 编辑 prod.yml，将 SECRET_KEY 引用改为 ${SECRET_KEY:?err} 形式：
#   environment:
#     - SECRET_KEY=${SECRET_KEY:?SECRET_KEY must be set explicitly}

# 4. 确认 compose 不会自动读根 .env
# docker compose -f prod.yml config -q   应报错提示 SECRET_KEY 未设置

# 5. 已暴露密钥轮换（最重要！）
# 生成新密钥：python -c "import secrets; print(secrets.token_urlsafe(32))"
# 替换所有环境中旧值
# 注意：轮换后所有现有 refresh token 失效，需通知用户重新登录
```

**验证方法**:
```bash
# 验证 compose 在缺密钥时不静默通过
unset SECRET_KEY
docker compose -f prod.yml config -q 2>&1 | grep -q "SECRET_KEY must be set" && echo "PASS" || echo "FAIL"

# 验证显式设置后正常
export SECRET_KEY="test-key-for-config-check"
docker compose -f prod.yml config -q && echo "PASS"
```

**完成标准**: 
- 根 `.env` 中 SECRET_KEY 不再是真实密钥
- `docker compose -f prod.yml config -q` 在未显式设 SECRET_KEY 时报错退出
- 已轮换旧密钥

**估时**: 45 min

---

#### Step 3: P0-3 — alertmanager 告警链路修复

**描述**: prod alertmanager 无 environment 段 → SMTP 变量 envsubst 全空；镜像为 busybox 基底无 envsubst 二进制 → 告警全链路不通。

**文件位置**: `prod.yml:148-165`、`deploy/prometheus/alerts.yml`

**修复步骤**:

```bash
# 1. 确认问题：检查 prod.yml alertmanager 段
sed -n '148,165p' prod.yml

# 2. 给 alertmanager service 增加 environment 段
# 在 prod.yml 中 alertmanager 定义下增加：
#   environment:
#     - SMTP_HOST=${SMTP_HOST}
#     - SMTP_PORT=${SMTP_PORT:-587}
#     - SMTP_USER=${SMTP_USER}
#     - SMTP_PASS=${SMTP_PASS}
#     - ALERT_TO=${ALERT_TO}
#     - ALERT_FROM=${ALERT_FROM:-noreply@example.com}

# 3. 替换镜像为基础含 envsubst 的镜像
# 将 alertmanager 镜像从 busybox 改为：
#   image: prom/alertmanager:latest （或 alpine:latest + apk add gettext）
# 或在 Dockerfile 中安装 gettext

# 4. 检查 alertmanager 配置模板
cat deploy/prometheus/alertmanager.yml | grep -o '\${[^}]*}' | sort -u
# 确保所有变量都在 environment 段中出现

# 5. 重写 entrypoint/cmd 使模板替换在启动时执行
# 示例：
#   command: >
#     sh -c "envsubst < /etc/alertmanager/alertmanager.yml.tmpl > /etc/alertmanager/alertmanager.yml
#            && /bin/alertmanager --config.file=/etc/alertmanager/alertmanager.yml"
```

**验证方法**:
```bash
# 容器启动后检查实际配置是否替换成功
docker compose -f prod.yml up -d alertmanager
docker compose -f prod.yml exec alertmanager cat /etc/alertmanager/alertmanager.yml
# 确认无空的 SMTP 变量

# 触发测试告警
# 手动触发一条告警（如停掉一个 scrape target）
# 检查 alertmanager 日志
docker compose -f prod.yml logs alertmanager | grep -i "notification\|send\|smtp"
```

**完成标准**:
- alertmanager 容器正常启动无 CrashLoop
- 配置文件中 SMTP 变量已替换为实际值
- 可成功发送测试邮件到配置的邮箱

**估时**: 1 h

---

#### Step 4: P0-5 — refresh token 改读 cookie（R4 声称落空项）

**描述**: R4 声称 refresh token 已迁移到 httpOnly cookie 读取，实测 security.py 仅写入 cookie 但 auth.py 仍从 JSON body 读取（全码无读 refresh cookie 逻辑）。

**文件位置**: `auth.py:117-118`（读取端）、`security.py:174-209`（写入端）

**修复步骤**:

```python
# 1. 修改 auth.py 的 refresh_token 端点（约117-118行）
# 原代码（推测）:
#   refresh_token = body.get("refresh_token")
#  或 refresh_token = request_data.get("refresh_token")
# 改为:
#   refresh_token = request.cookies.get("refresh_token")
#   if not refresh_token:
#       raise HTTPException(status_code=400, detail="refresh_token cookie required")

# 2. 确认 security.py 中 refresh cookie 设置（174-209行已有 set）
# 检查 cookie 属性：
# - httponly=True（必须）
# - secure=True（生产必须）
# - samesite="Strict" 或 "Lax"
# - path="/auth"（建议收窄，见 P3 低优项）

# 3. 缩短 refresh token TTL
# 在 .env 中（或 config.py 中）:
# REFRESH_TOKEN_EXPIRE_DAYS=7 → REFRESH_TOKEN_EXPIRE_DAYS=1
# 或在 auth.py 中 hardcode 缩短

# 4. 删除 refresh token 在 JSON body 中的返回
# 原 /login 响应可能含 {"refresh_token": "..."}，确认移除
# 改为仅通过 Set-Cookie 返回
```

**验证方法**:
```bash
# 1. 登录并检查响应中无 refresh_token 在 body
curl -s -X POST https://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}' \
  -c cookies.txt | jq .refresh_token  # 应为 null

# 2. 使用 cookie 刷新
curl -s -X POST https://localhost/auth/refresh \
  -b cookies.txt | jq .access_token   # 应返回新 token

# 3. 验证 XSS 无法读取（检查 cookie 属性）
curl -s -I -X POST https://localhost/auth/login \
  -d '{"username":"test","password":"test"}' \
  | grep -i "set-cookie.*refresh"    # 应包含 HttpOnly
```

**完成标准**:
- `/auth/login` 响应 body 不含 `refresh_token` 字段
- `/auth/refresh` 从 cookie 读取 refresh token 成功返回新 access token
- Set-Cookie 头包含 `HttpOnly; Secure; SameSite=Strict`
- refresh token TTL ≤ 1 天

**估时**: 1.5 h

---

#### Step 5: P0-6 + P0-7 — /register 限流 + 强制改密服务端拦截

**描述**: 
- P0-6: `/auth/register` 无任何限流装饰器 → 可批量建号/邮箱枚举
- P0-7: `get_current_user` 不检查 `force_password_change` claim → 持该标志用户可调全部接口

**文件位置**: `main.py:146`（限流）、`auth.py:92-103` / `core/deps.py`（强制改密）

**修复步骤**:

```python
# ---- P0-6: /register 限流 ----
# main.py 中 /register 路由（约146行）
# 原:
#   @router.post("/auth/register")
# 改为:
#   @router.post("/auth/register")
#   @limiter.limit("3/minute")     # 严格限流：3次/分钟
#   async def register(request: Request, ...):
#       ...

# ---- P0-7: 强制改密拦截 ----
# auth.py:92-103 get_current_user 函数中增加检查
# 在验证 token 有效性之后、返回 user 之前插入:
#
#   if token_data.force_password_change:
#       # 检查当前请求是否在允许跳过改密的路径中
#       from fastapi import Request
#       request_path = request.url.path if has_request_context() else ""
#       allowed_paths = ["/auth/change-password", "/auth/logout"]
#       if request_path not in allowed_paths:
#           raise HTTPException(
#               status_code=403,
#               detail="Password change required. Use /auth/change-password"
#           )

# 如果 get_current_user 被用作 Depends，需要调整依赖链，
# 确保 request 对象可访问。如果无法获取 request：
# 方法2：在 core/deps.py 中新增一个依赖：
#   async def require_password_not_expired(
#       current_user: User = Depends(get_current_user),
#       request: Request
#   ):
#       token = request.cookies.get("access_token") or \
#               request.headers.get("Authorization","").removeprefix("Bearer ")
#       payload = decode_token(token)  # 或从已有逻辑获取
#       if payload.get("force_password_change"):
#           raise HTTPException(403, detail="Password change required")
#       return current_user
```

**验证方法**:
```bash
# P0-6 验证：
# 快速连续注册5次，第4次应返回 429
for i in $(seq 1 5); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://localhost/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"test'$i'@test.com","password":"Test1234!","username":"test'$i'"}'
done
# 预期输出: 200,200,200,429,429

# P0-7 验证：
# 用 force_password_change=True 的 token 访问任意接口
curl -s -o /dev/null -w "%{http_code}\n" \
  https://localhost/products \
  -H "Authorization: Bearer <FORCE_CHANGE_TOKEN>"
# 预期: 403
```

**完成标准**:
- P0-6: `/auth/register` 被限流装饰器包裹，连续 4+ 次请求返回 429
- P0-7: `force_password_change=True` 的用户访问非 /change-password /logout 路径返回 403
- 两个修复均有对应测试断言

**估时**: 1 h

---

#### Step 6: P0-4 — 备份调度落地

**描述**: 全仓无任何备份调度机制（cron/ofelia/systemd timer 均无），runbook 称"daily via cron"与实现不符。

**前置依赖**: 需 H2（BOM 清理）完成后 backup.sh 才可正确执行。

**文件位置**: 全仓（`scripts/backup.sh`、`prod.yml`）

**修复步骤**:

```bash
# 方案A：ofelia 容器调度（推荐，与 Docker 生态一致）
# 在 prod.yml 中增加 ofelia service:
#
# ofelia:
#   image: mcuadros/ofelia:latest
#   volumes:
#     - /var/run/docker.sock:/var/run/docker.sock:ro
#     - ./backups:/backups
#   environment:
#     - BACKUP_RETENTION_DAYS=30
#   command: daemon --docker
#   labels:
#     ofelia.job-local.backup-daily.schedule: "@daily"
#     ofelia.job-local.backup-daily.command: >
#       sh -c "docker compose -f /path/to/prod.yml exec -T db pg_dump -U postgres bilingual_cms > /backups/backup_$(date +%Y%m%d).sql"

# 方案B：host cron + docker compose exec
# crontab -e
# 0 2 * * * cd /path/to/project && docker compose -f prod.yml exec -T db pg_dump -U postgres bilingual_cms > backups/daily_$(date +\%Y\%m\%d).sql 2>&1 | logger -t backup

# 方案C：systemd timer（Linux host）
# 创建 /etc/systemd/system/cms-backup.service 和 .timer

# 同时更新 runbook 中的描述，使其与实现一致
```

**验证方法**:
```bash
# ofelia 方案：
docker compose -f prod.yml logs ofelia | grep "backup"

# cron 方案：
grep backup /var/spool/cron/crontabs/* || grep backup /etc/crontab
crontab -l | grep backup

# 手动触发一次，确认成功
docker compose -f prod.yml exec ofelia ofelia run backup-daily --job-local
ls -la backups/ | tail -5
```

**完成标准**:
- 备份调度已配置并能自动触发（cron / ofelia / systemd timer 任一种）
- 手动触发一次备份成功生成 `.sql` 文件
- runbook 中的备份说明与实际机制一致

**估时**: 45 min

---

#### Step 7: P0-8 — 修正 test_terms.py 测试收集（零覆盖假象）

**描述**: `test_terms.py` 中 3 个测试函数（`test_list_terms` / `test_create_term` / `test_delete_term`）误缩进嵌套进 `_seed_terms` 辅助函数内，且 `admin_token` fixture 误用，导致 pytest 收集到 0 条 term 测试。

**文件位置**: `test_terms.py:10-40`

**修复步骤**:

```python
# 在 test_terms.py 中：

# 1. 修正缩进：将 3 个 test_ 函数从 _seed_terms 内部移出到模块顶级
# 当前（错误）结构：
#   def _seed_terms():
#       """helper"""
#       ...
#       def test_list_terms():    # ← 嵌套在 _seed_terms 内，pytest 不收集！
#           ...
#       def test_create_term():
#           ...
#       def test_delete_term():
#           ...

# 正确结构：
#   def _seed_terms():
#       """helper"""
#       ...
#
#   def test_list_terms(client, admin_token, _seed_terms):  # ← 模块顶级
#       ...
#   def test_create_term(client, admin_token, _seed_terms):
#       ...
#   def test_delete_term(client, admin_token, _seed_terms):
#       ...

# 2. 修正 admin_token fixture 调用
# 确认 conftest.py 中有 admin_token fixture，或改为直接获取 token：
#   admin_token = get_test_token(client, username="admin", password="admin")

# 3. 在 CI 中加入测试收集数断言
# .github/workflows/test.yml:
#   - run: pytest --co -q | tee /tmp/collected.txt
#   - run: grep -q "150 tests collected" /tmp/collected.txt || exit 1
```

**验证方法**:
```bash
# 确认 terms 测试被收集
pytest --co -q -k "term" | grep "test_terms"
# 预期输出: tests/test_terms.py::test_list_terms, test_create_term, test_delete_term

# 确认总收集数上升
pytest --co -q 2>&1 | tail -1
# 预期: 153 collected (原来 150，+3 terms)

# 运行 terms 测试
pytest tests/test_terms.py -v
# 预期: 3 passed (not 0 items / no tests ran)
```

**完成标准**:
- `pytest --co -q` 输出中 `test_terms.py` 贡献 ≥ 3 条测试
- `pytest tests/test_terms.py -v` 显示 3 passed
- 总收集数从 150 → ≥153（仅此修复，不含其他补测）

**估时**: 30 min

---

#### Step 8: P0-9 — 覆盖率诚实化（去除 pyproject 粉饰排除项）

**描述**: `pyproject.toml` 中 `[tool.coverage.report]` 排除了 `except Exception`/`pass`/`return None` 行，使名义覆盖率 73% vs 真实 69%，已跌破 CI 70% 门槛。

**文件位置**: `pyproject.toml:16-26`

**修复步骤**:

```toml
# 在 pyproject.toml 中 [tool.coverage.report] 段：

# 方案A（推荐）：完全移除排除项，接受真实覆盖率
# 删除或注释以下行：
#   exclude_lines = [
#       "except Exception",
#       "pass",
#       "return None",
#   ]

# 方案B：保留排除但临时放宽 CI 阈值，后续通过补测追回
# 在 CI 中：
#   --cov-fail-under=65   # 临时从 70 降到 65（如实值 69%）

# 方案C：保留排除但补测试追回 70%（需更多时间）
# 配合 Sprint-B 测试补齐任务（M4/M8/M12 等）

# 建议立即执行方案A + CI 阈值暂调为 65，Sprint-B 追回
```

**验证方法**:
```bash
# 去除排除项后重跑覆盖率
pytest --cov=backend --cov-report=term --cov-report=xml -q 2>&1 | tail -5
# 预期: TOTAL ... 69%（而非 73%）

# 检查 CI 配置中的阈值
grep "cov-fail-under" pyproject.toml .github/workflows/*.yml
```

**完成标准**:
- `pyproject.toml` 中 `exclude_lines` 段已移除或注释
- `pytest --cov --cov-report=term` 输出真实覆盖率（~69%）
- CI 门槛与真实覆盖率一致（临时 65% 或补测试后 70%）
- 无因覆盖率跌破门槛导致的 CI 假失败

**估时**: 20 min

---

#### Step 9: H1 — login 端点补 db.commit() 防审计丢失

**描述**: `auth.py` login 端点更新 `last_login_at` 和写入 `user_login` 审计记录后无 `db.commit()`，事务随 session 关闭回滚→审计数据丢失。

**文件位置**: `auth.py:71-113`、`database.py:27-32`

**修复步骤**:

```python
# auth.py 中 login 函数（~71-113行），在更新 last_login_at 后增加：
#
#   user.last_login_at = datetime.utcnow()
#   audit_log = UserLogin(user_id=user.id, ip=request.client.host, ...)
#   db.add(audit_log)
#   await db.commit()     # ← 关键行：提交事务
#   await db.refresh(user)

# 确认 database.py:27-32 中 get_db session 配置：
#   autocommit=False 是 FastAPI+SQLAlchemy 默认行为，无需改
#   但需确认无 expire_on_commit=False 覆盖
```

**验证方法**:
```bash
# 方法1：登录后检查数据库
curl -s -X POST https://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq .

# 查询 last_login_at 是否已更新
docker compose -f prod.yml exec db psql -U postgres -d bilingual_cms \
  -c "SELECT username, last_login_at FROM users WHERE username='admin';"

# 查询 user_login 审计表
docker compose -f prod.yml exec db psql -U postgres -d bilingual_cms \
  -c "SELECT * FROM user_login ORDER BY created_at DESC LIMIT 3;"

# 方法2：单元测试验证
# 在 test_auth.py 中增加：
#   def test_login_audit_persisted(client, db_session):
#       resp = client.post("/auth/login", json={"username":"u","password":"p"})
#       assert resp.status_code == 200
#       logs = db_session.query(UserLogin).filter_by(user_id=...).all()
#       assert len(logs) > 0
#       assert logs[0].ip is not None
```

**完成标准**:
- login 成功后 `users.last_login_at` 字段在数据库中持久更新
- `user_login` 表中出现新的审计记录（含 IP、时间）
- 登出仍正常（logout 已有 commit，不冲突）
- 测试断言可验证审计持久化

**估时**: 30 min

---

#### Step 10: H3 — import_.py 定义 logger 防 NameError

**描述**: `import_.py:386` 调用 `logger.error()` 但模块内从未定义 `logger`，文件解析失败时预期返回 400 实际抛 NameError → 500。

**文件位置**: `import_.py:386`

**修复步骤**:

```python
# import_.py 模块顶部增加 logger 定义（约第10行附近）：
import logging
logger = logging.getLogger(__name__)

# 同时全局搜索 import_.py 中所有 logger 调用点
grep -n "logger\." import_.py
# 确认所有调用点都使用同一个 logger 对象
```

**验证方法**:
```bash
# 构造一个会触发解析失败的上传请求
curl -s -X POST https://localhost/import/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/fixtures/broken_products.csv" \
  -w "\nHTTP %{http_code}"

# 预期: 400 (而非 500 Internal Server Error)
# 同时检查日志中是否有正确的错误信息
docker compose -f prod.yml logs backend | grep -i "logger\|NameError\|import"
```

**完成标准**:
- `import_.py` 模块顶部有 `logger = logging.getLogger(__name__)`
- 上传损坏的文件返回 4xx 而非 500
- 日志中有正确的错误信息输出

**估时**: 15 min

---

#### Step 11: H2 — UTF-8 BOM 清理（P1 前置依赖，插入 Hotfix 末尾）

**描述**: `backup.sh` shebang 前含 UTF-8 BOM 导致 `./backup.sh` 执行失败；多个 YAML 带 BOM；ci-content-gates 不检 BOM（门禁盲区）。

**前置说明**: 此修复为 P0-4（备份调度）的前置依赖——BOM 不清理则 backup.sh 无法执行。

**文件位置**: `backup.sh:1`、全仓 YAML

**修复步骤**:

```bash
# 1. 全仓扫描带 BOM 的文件
find . -type f \( -name "*.sh" -o -name "*.yml" -o -name "*.yaml" -o -name "*.py" \) \
  -exec sh -c 'head -c3 "$1" | grep -q $'\''\xef\xbb\xbf'\'' && echo "$1"' _ {} \;

# 2. 逐个去除 BOM
# 对 backup.sh:
sed -i '1s/^\xEF\xBB\xBF//' scripts/backup.sh

# 对 YAML 文件（逐个确认后执行）:
sed -i '1s/^\xEF\xBB\xBF//' path/to/file.yml

# 3. 验证 backup.sh 可执行
chmod +x scripts/backup.sh
./scripts/backup.sh --help 2>&1 || bash scripts/backup.sh --help

# 4. 在 ci-content-gates 中增加 BOM 检测规则
# 编辑 .github/workflows/ci-content-gates.yml 或脚本:
#   - run: |
#       BOM_FILES=$(find . -type f \( -name "*.sh" -o -name "*.yml" -o -name "*.py" \) \
#         -exec sh -c 'head -c3 "$1" | grep -q $'\''\xef\xbb\xbf'\'' && echo "$1"' _ {} \;)
#       if [ -n "$BOM_FILES" ]; then
#         echo "ERROR: Files with UTF-8 BOM found:"
#         echo "$BOM_FILES"
#         exit 1
#       fi
```

**验证方法**:
```bash
# 确认 backup.sh 第一字节不是 BOM
xxd scripts/backup.sh | head -1
# 预期: 00000000: 2321... (#!) 而非 00000000: efbb bf23... (BOM+#)

# 确认 BOM 门禁生效
# 故意创建带 BOM 的文件 → CI 应报错
printf '\xef\xbb\xbf#!/bin/sh\necho test' > /tmp/test_bom.sh
find . -name "*.sh" -exec ... BOM check ...  # 应输出含 /tmp/test_bom.sh

# 全仓确认
find . -type f \( -name "*.sh" -o -name "*.yml" -o -name "*.yaml" \) \
  -exec sh -c 'head -c3 "$1" | grep -q $'\''\xef\xbb\xbf'\'' && echo "BOM: $1"' _ {} \;
# 预期: 无输出
```

**完成标准**:
- 全仓 `.sh`/`.yml`/`.yaml` 文件均无 UTF-8 BOM
- `./scripts/backup.sh` 可正常执行
- CI 门禁含 BOM 检测规则，新 BOM 文件阻止合入

**估时**: 30 min

---

## 二、Sprint-A（第 1-2 周）— 安全加固 + 测试可信度 + 文档止损

### 涉及漏洞清单（约 32 项 P1 + 15 项 P2 测试项插入）

按依赖分组：**Group-A 认证安全** → **Group-B 代码正确性** → **Group-C 运维可观测** → **Group-D 测试健康度** → **Group-E 文档契约**

---

### Group-A：认证安全边界闭环（5 项）

| ID | 描述 | 位置 | 估时 |
|----|------|------|------|
| H4 | 4-worker 密钥分裂 → token 跨 worker 随机 401 | config.py:54-77 | 30 min |
| H9 | 限流 fail-open + 非线程安全 | redis.py:154-155 / main.py:31,152-162 | 1.5 h |
| H24 | 单设备 logout 不 bump token_version → access(24h) 登出仍有效 | auth.py:166-205 | 1 h |
| H29 | ACCESS_TOKEN_EXPIRE_MINUTES=1440 覆盖默认 30min→24h | .env:4 | 10 min |
| P0-5 收尾 | refresh cookie path 过宽（低优 #6） | security.py | 15 min |

---

#### Group-A Step 1: H4 — 生产密钥 fail-fast（防止随机 401）

**描述**: `config.py:54-77` 中 SECRET_KEY 缺失时每个 worker 进程各自 `token_urlsafe()` 生成不同临时密钥→token 跨 worker 随机 401。

**文件位置**: `config.py:54-77`

**修复步骤**:

```python
# config.py:54-77，当前逻辑（推测）:
#   SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
# 改为 fail-fast:
#   SECRET_KEY = os.getenv("SECRET_KEY")
#   if not SECRET_KEY:
#       raise RuntimeError(
#           "SECRET_KEY environment variable is required. "
#           "Set it explicitly before starting the application."
#       )

# 后续如确需开发环境缺省，使用明确区分：
#   if not SECRET_KEY:
#       if os.getenv("ENV", "production") == "development":
#           import warnings
#           warnings.warn("Using dev-only SECRET_KEY - do NOT use in production!")
#           SECRET_KEY = "dev-secret-not-for-production"
#       else:
#           raise RuntimeError("SECRET_KEY is required")
```

**验证方法**:
```bash
# 不设 SECRET_KEY 启动
unset SECRET_KEY
docker compose -f prod.yml up backend 2>&1
# 预期: 启动失败，日志含 "SECRET_KEY is required"

# 设 SECRET_KEY 启动
export SECRET_KEY="test-key-123"
docker compose -f prod.yml up backend -d
# 预期: 正常启动

# 多 worker 验证：两个请求使用同一 token 均返回一致结果
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" https://localhost/products
done
# 预期: 全部 200（无随机 401）
```

**完成标准**:
- 生产模式缺 SECRET_KEY 时启动 crash（非静默降级）
- 同一 token 在多 worker 环境下不出现随机 401
- 开发模式可选用显式 dev 密钥

**估时**: 30 min

---

#### Group-A Step 2: H9 — 限流 fail-closed + 线程安全

**描述**: `redis.py:154-155` 中 `except: return True` 使 Redis 宕机时限流 fail-open（放行所有请求）；`main.py:31,152-162` 内存回退是死代码；IP 键无限增长无清理锁。

**文件位置**: `redis.py:154-155`、`main.py:31,152-162`

**修复步骤**:

```python
# 1. redis.py:154-155 改 fail-open 为 fail-closed
# 原:
#   except Exception:
#       return True  # ← fail-open: Redis 挂了一切放行
# 改为:
#   except Exception as e:
#       logger.error(f"Rate limiter Redis unavailable: {e}")
#       return False  # fail-closed: Redis 挂时拒绝请求（安全优先）

# 2. main.py 内存回退改为可工作
# 删除死代码或将内存回退改为真实的 Redis 不可用时的 fallback：
#   if redis_unavailable:
#       # 使用 threading.Lock + dict 作为内存回退
#       with in_memory_lock:
#           now = time.time()
#           self._cleanup_expired(now)
#           key_entries = self.store.get(ip, [])
#           if len(key_entries) >= limit:
#               return False
#           self.store[ip] = key_entries + [now]
#           return True

# 3. IP 键过期清理
# 在 check_rate_limit 开头加定期清理：
#   if random.random() < 0.01:  # 1% 概率触发清理
#       for ip in list(store.keys()):
#           store[ip] = [t for t in store[ip] if t > time.time() - window]
#           if not store[ip]:
#               del store[ip]

# 4. 加锁（如果使用内存回退）
# from threading import Lock
# _rate_limit_lock = Lock()
```

**验证方法**:
```bash
# 验证 fail-closed: 停掉 Redis
docker compose -f prod.yml stop redis
# 发起正常限流范围内请求
curl -s -o /dev/null -w "%{http_code}" https://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"a","password":"b"}'
# 预期: 429 Too Many Requests（而非放行 200/401）

# 恢复 Redis
docker compose -f prod.yml start redis
curl -s -o /dev/null -w "%{http_code}" https://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"a","password":"b"}'
# 预期: 200/401（恢复正常限流判断）
```

**完成标准**:
- Redis 不可用时限流拒绝请求（429）而非放行
- 内存回退路径可工作（如保留）
- IP 键不会无限增长（有清理/过期机制）
- 多线程场景下限流计数正确（加锁）

**估时**: 1.5 h

---

#### Group-A Step 3: H24 — logout 时 bump token_version

**描述**: 单设备 logout 不 bump `token_version` → 5min 内 access token（24h TTL）登出后仍有效，可继续调用需认证接口。

**文件位置**: `auth.py:166-205`

**修复步骤**:

```python
# auth.py logout 函数（~166-205行）中增加 token_version 递增：
#
# @router.post("/auth/logout")
# async def logout(current_user: User = Depends(get_current_user)):
#     # 增加 token_version 使所有现有 token 立即失效
#     current_user.token_version += 1
#     db.add(current_user)
#     await db.commit()  # ← 确认有 commit！
#
#     response = JSONResponse({"detail": "Logged out"})
#     response.delete_cookie("access_token")
#     response.delete_cookie("refresh_token")
#     return response

# 同时在 get_current_user 的 token 校验中增加 version 检查：
#   if payload.get("token_version") != user.token_version:
#       raise HTTPException(401, "Token has been revoked")
```

**验证方法**:
```bash
# 1. 登录获取 token
TOKEN=$(curl -s -X POST https://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}' | jq -r .access_token)

# 2. 确认 token 有效
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" https://localhost/products
# 预期: 200

# 3. 登出
curl -s -X POST https://localhost/auth/logout \
  -H "Authorization: Bearer $TOKEN"

# 4. 用同一 token 再访问
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" https://localhost/products
# 预期: 401（而非 200）
```

**完成标准**:
- logout 后 token_version 在数据库中递增
- 使用登出前的 access token 访问需认证接口返回 401
- logout 本身有 db.commit()（确保持久化）
- 对应测试覆盖此场景

**估时**: 1 h

---

#### Group-A Step 4: H29 — ACCESS_TOKEN_EXPIRE_MINUTES 从 1440(24h) 缩短

**描述**: `.env:4` 中 `ACCESS_TOKEN_EXPIRE_MINUTES=1440` 覆盖默认 30min → 24h，攻击窗口过大。

**文件位置**: `.env:4`、`config.py`

**修复步骤**:

```bash
# .env:4 修改：
# ACCESS_TOKEN_EXPIRE_MINUTES=1440 → ACCESS_TOKEN_EXPIRE_MINUTES=30

# 如某些场景需要更长（如 CLI 工具），使用 refresh token 流程代替
```

**验证方法**:
```bash
# 生成 token 后等待 30min+ 或解析 JWT exp 字段
TOKEN=$(curl -s ... | jq -r .access_token)
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq .exp
# 计算 exp - iat，应 ≈ 1800 秒（30min）
```

**完成标准**:
- `.env` 中 `ACCESS_TOKEN_EXPIRE_MINUTES` = 30（或 ≤ 60）
- 生成的 access token JWT exp 字段与配置一致
- 无硬编码覆盖默认值

**估时**: 10 min

---

#### Group-A Step 5: refresh cookie path 收窄（低优 #6 补充）

**描述**: `security.py` 中 refresh cookie 的 `path="/"` 过宽，应改为 `path="/auth"`。

**文件位置**: `security.py:174-209`

**修复步骤**:

```python
# security.py 中 set_refresh_cookie 调用：
# response.set_cookie(
#     key="refresh_token",
#     value=refresh_token,
#     httponly=True,
#     secure=True,
#     samesite="Strict",
#     path="/auth",           # ← 从 "/" 改为 "/auth"
#     max_age=REFRESH_TTL
# )
```

**验证方法**:
```bash
# 登录后检查 Set-Cookie 头
curl -s -I -X POST https://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}' \
  | grep -i "set-cookie.*refresh" | grep -o "Path=[^;]*"
# 预期: Path=/auth
```

**完成标准**: Set-Cookie 中 refresh_token 的 Path 属性为 `/auth`。

**估时**: 15 min

---

### Group-B：代码正确性修复（7 项）

| ID | 描述 | 位置 | 估时 |
|----|------|------|------|
| H5 | 导出双重全表扫描 | export.py:45-48 / consistency.py:62,243 | 1 h |
| H6 | 导出审计早写且顺序错 | export.py:59-68 | 45 min |
| H7 | 三层 BaseHTTPMiddleware 包裹 StreamingResponse | exception_handler.py:12,20-25 / csrf.py:20 / monitoring.py:31 | 2 h |
| H8 | import 操作零审计 | import_.py:583 | 45 min |
| H10 | async 端点做阻塞 I/O | auth.py:221 / import_.py:326 | 1.5 h |
| H21 | CSV 注入防护缺 `\n` 检查 | csv_utils.py:21 | 15 min |
| H22 | extra_fields schema 静默跳过 required | product.py:69-70 | 30 min |

---

#### Group-B Step 1: H5 — 导出双重全表扫描消除

**描述**: `check_all_products` 无视 `product_ids` 参数恒扫全表，`export.py` 又调用一次全表查询→重复全表扫描。

**文件位置**: `export.py:45-48`、`consistency.py:62,243`

**修复步骤**:

```python
# 1. consistency.py:62 check_all_products 函数
# 原: 恒扫全表
#   all_products = db.query(Product).all()
#   for p in all_products:
#       ...
# 改为: 按需传参
#   def check_all_products(db, product_ids: Optional[list] = None):
#       query = db.query(Product)
#       if product_ids:
#           query = query.filter(Product.id.in_(product_ids))
#       products = query.all()
#       ...

# 2. export.py:45-48
# 原: 先调 check_all_products 又自己查全表
#   consistency.check_all_products(db)  # 全表
#   products = db.query(Product).all()  # 又全表！
# 改为:
#   products = db.query(Product).all()
#   consistency.check_all_products(db, product_ids=[p.id for p in products])
# 或: 直接传 products 列表避免两次查询

# 3. consistency.py:243 同样排查
```

**验证方法**:
```bash
# 开启 SQL 日志观察查询数
# 导出操作前后对比查询次数
docker compose -f prod.yml logs backend | grep -c "SELECT.*products"
# 导出前记一次数，导出后再记一次，增量应减少
```

**完成标准**:
- 单次导出操作只触发一次 `SELECT * FROM products` 全表扫描
- `check_all_products` 接受 `product_ids` 参数并正确过滤
- 导出功能行为不变（输出格式一致）

**估时**: 1 h

---

#### Group-B Step 2: H6 — 导出审计早写且顺序错

**描述**: `write_audit_log` 在 404 分支之前提交 → 空导出（无权限/无产品）也留"成功"审计记录→审计不可信。

**文件位置**: `export.py:59-68`

**修复步骤**:

```python
# export.py 导出端点中审计写位置调整：

# 当前错误顺序（推测）:
#   1. write_audit_log(db, "export", "success", ...)   # ← 过早！
#   2. if not products: raise HTTPException(404, ...)
#   3. generate csv...

# 正确顺序:
#   1. if not products: raise HTTPException(404, ...)
#   2. csv_data = generate_export(products, ...)
#   3. write_audit_log(db, "export", "success", ...)   # ← 移到生成成功后
#   4. return StreamingResponse(...)

# 同时区分审计状态:
#   write_audit_log(db, "export", "success" if products else "empty", ...)
```

**验证方法**:
```bash
# 1. 请求无权限的导出（如不带 token）
curl -s -o /dev/null -w "%{http_code}\n" https://localhost/export/products
# 预期: 401/403

# 2. 查询审计表确认无"成功"记录
docker compose -f prod.yml exec db psql -U postgres -d bilingual_cms \
  -c "SELECT * FROM audit_log WHERE action='export' ORDER BY created_at DESC LIMIT 5;"
# 预期: 401 的请求不应有 audit_log 记录

# 3. 正常导出后确认有审计记录
curl -s -H "Authorization: Bearer $TOKEN" https://localhost/export/products
# 再查审计表，确认有一条成功记录
```

**完成标准**:
- 401/403/404 响应不产生"成功"审计记录
- 成功导出后审计记录中包含操作者、时间、导出范围
- 审计记录不再早于业务逻辑结果

**估时**: 45 min

---

#### Group-B Step 3: H7 — 三层 BaseHTTPMiddleware 收敛

**描述**: csrf + exception + monitoring 三层 BaseHTTPMiddleware（继承自 Starlette 的同步中间件）包裹 StreamingResponse→异常逃逸 + 缓冲削弱真流式收益。

**文件位置**: `exception_handler.py:12,20-25`、`csrf.py:20`、`monitoring.py:31`

**修复步骤**:

```python
# 方案A（推荐）：将三层 BaseHTTPMiddleware 合并为一个 ASGI middleware
# 或使用纯 ASGI middleware 替代 BaseHTTPMiddleware：

# exception_handler.py:
# 将 BaseHTTPMiddleware 改为纯 ASGI middleware:
#   class ExceptionHandlerMiddleware:
#       def __init__(self, app):
#           self.app = app
#       async def __call__(self, scope, receive, send):
#           if scope["type"] != "http":
#               await self.app(scope, receive, send)
#               return
#           try:
#               await self.app(scope, receive, send)
#           except Exception:
#               # handle and send error response directly

# csrf.py: 同样改为纯 ASGI

# monitoring.py: 同样改为纯 ASGI（或使用 prometheus_fastapi_instrumentator）

# 方案B（保守）：合并为一个中间件，减少中间件层数
# 但 StreamingResponse 的兼容性仍然需要纯 ASGI 方式处理

# 验证 StreamingResponse 仍正常工作：
# 导出大文件时确认响应流式传输，不是全部缓冲后再返回
```

**验证方法**:
```bash
# 1. 导出大文件验证流式行为
time curl -s -H "Authorization: Bearer $TOKEN" \
  https://localhost/export/products > /dev/null
# 确认首字节时间明显早于总完成时间（流式特征）

# 2. 触发异常验证中间件仍能正确捕获
curl -s -w "\n%{http_code}" https://localhost/import/upload \
  -F "file=@/dev/null"
# 预期: 400/422（而非 500 或无响应）

# 3. CSRF 保护仍生效
curl -s -w "\n%{http_code}" -X POST https://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"a","password":"b"}'
# 预期: 403（缺 CSRF token）或 200（CSRF 放行已文档化）
```

**完成标准**:
- 三层中间件已合并或改为纯 ASGI middleware
- StreamingResponse 的流式特性保持（非缓冲后返回）
- 异常捕获、CSRF 保护、指标采集功能不变
- 中间件层数减少（目标 ≤2 层）

**估时**: 2 h

---

#### Group-B Step 4: H8 — import 操作零审计补全

**描述**: `write_audit_log` 全仓仅 auth/export/products/users 命中，import 操作完全无审计。

**文件位置**: `import_.py:583`

**修复步骤**:

```python
# import_.py:583 附近，在 import 完成/失败时增加审计：

# 成功路径：
#   write_audit_log(
#       db=db,
#       action="import",
#       status="success",
#       user_id=current_user.id,
#       details={
#           "filename": file.filename,
#           "rows_imported": imported_count,
#           "rows_skipped": skipped_count,
#           "product_type": product_type
#       }
#   )
#   # 确认 commit！

# 失败路径：
#   except Exception as e:
#       write_audit_log(db, "import", "failed",
#           user_id=current_user.id,
#           details={"error": str(e), "filename": file.filename}
#       )
#       raise
```

**验证方法**:
```bash
# 执行一次 import 后查审计表
curl -s -X POST https://localhost/import/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/fixtures/sample_products.csv"

docker compose -f prod.yml exec db psql -U postgres -d bilingual_cms \
  -c "SELECT * FROM audit_log WHERE action='import' ORDER BY created_at DESC LIMIT 3;"
# 预期: 至少一条 import 审计记录，含 filename 和 row count
```

**完成标准**:
- import 成功时产生审计记录（含文件名、导入行数）
- import 失败时产生审计记录（含错误原因）
- 审计记录持久化（有 db.commit()）

**估时**: 45 min

---

#### Group-B Step 5: H10 — async 端点阻塞 I/O 改线程池

**描述**: `change_password`（bcrypt×2+DB）和 `upload_file`（open/write/parse）在 async 端点中同步阻塞执行，未用 run_in_executor / aiofiles。

**文件位置**: `auth.py:221`、`import_.py:326`

**修复步骤**:

```python
# 1. auth.py:221 change_password 端点
# 原（推测）:
#   @router.post("/auth/change-password")
#   async def change_password(...):
#       user = await get_user(...)
#       if not bcrypt.verify(old_password, user.hashed_password):  # 同步阻塞
#           ...
#       user.hashed_password = bcrypt.hash(new_password)           # 同步阻塞
# 改为:
#   import asyncio
#   loop = asyncio.get_running_loop()
#   @router.post("/auth/change-password")
#   async def change_password(...):
#       user = await get_user(...)
#       valid = await loop.run_in_executor(
#           None, bcrypt.verify, old_password, user.hashed_password
#       )
#       if not valid:
#           ...
#       user.hashed_password = await loop.run_in_executor(
#           None, bcrypt.hash, new_password
#       )

# 2. import_.py:326 upload_file 端点
# 文件写入使用 aiofiles:
#   import aiofiles
#   async with aiofiles.open(temp_path, "wb") as f:
#       while chunk := await file.read(8192):
#           await f.write(chunk)

# 3. 文件解析（pandas/CSV）放到线程池:
#   result = await loop.run_in_executor(
#       None, parse_import_file, temp_path
#   )
```

**验证方法**:
```bash
# 1. 功能验证：change_password 仍正常工作
curl -s -X POST https://localhost/auth/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"old_password":"old","new_password":"new"}' | jq .
# 预期: 200 OK

# 2. 并发达标：同时发起 10 个 change_password 请求
# 使用 ab / wrk / hey 工具
hey -n 10 -c 10 -m POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"old_password":"old","new_password":"new"}' \
  https://localhost/auth/change-password
# 预期: 无超时、无 event loop 阻塞警告

# 3. 上传大文件验证
head -c 10M /dev/urandom > /tmp/large.csv
time curl -X POST https://localhost/import/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/large.csv"
# 预期: 不阻塞其他请求（期间 /health 仍快速响应）
```

**完成标准**:
- bcrypt 操作在 `run_in_executor` 中执行
- 文件 I/O 使用 `aiofiles` 或线程池
- 并发请求时不出现 event loop 阻塞警告
- 功能正确性不变

**估时**: 1.5 h

---

#### Group-B Step 6: H21 — CSV 注入防护缺 `\n` 检查

**描述**: `csv_utils.py:21` CSV 注入防护仅检查 `=`/`@`/`+`/`-` 开头，未检查 `\n`（换行符可构造多行注入）。

**文件位置**: `csv_utils.py:21`

**修复步骤**:

```python
# csv_utils.py:21，当前（推测）:
#   def sanitize_csv_value(value: str) -> str:
#       if value and value[0] in ('=', '@', '+', '-'):
#           return "'" + value
#       return value
#
# 改为:
#   def sanitize_csv_value(value: str) -> str:
#       if not value:
#           return value
#       # 移除换行符防止多行注入
#       value = value.replace('\n', ' ').replace('\r', ' ')
#       # 检查危险首字符
#       if value[0] in ('=', '@', '+', '-'):
#           return "'" + value
#       return value
```

**验证方法**:
```bash
# 单元测试：sanitize_csv_value("=CMD\n=INJECT") 
# 预期: "'=CMD =INJECT" （无换行，首字符转义）
```

**完成标准**:
- `sanitize_csv_value` 移除 `\n` 和 `\r` 字符
- 含换行的恶意输入无法产生多行 CSV 注入
- 单元测试覆盖注入场景

**估时**: 15 min

---

#### Group-B Step 7: H22 — extra_fields schema 静默跳过 required

**描述**: `product.py:69-70` 中加载 extra_fields schema 时 `except FileNotFoundError: pass`，若 schema 文件缺失则静默不校验必填字段。

**文件位置**: `product.py:69-70`

**修复步骤**:

```python
# product.py:69-70，当前（推测）:
#   try:
#       schema = load_extra_fields_schema()
#   except FileNotFoundError:
#       pass  # ← schema 缺失时静默跳过
#
# 改为：
#   try:
#       schema = load_extra_fields_schema()
#   except FileNotFoundError:
#       if os.getenv("ENV") == "development":
#           logger.warning("extra_fields schema not found, skipping validation")
#           schema = None
#       else:
#           raise RuntimeError("extra_fields schema is required but not found")
#
# 或直接:
#   schema = load_extra_fields_schema()  # 不捕获，缺失即 crash
```

**验证方法**:
```bash
# 1. 确认 schema 文件存在
ls -la path/to/extra_fields_schema.json

# 2. 故意删除 schema 文件后启动
mv extra_fields_schema.json extra_fields_schema.json.bak
docker compose -f prod.yml up backend 2>&1
# 预期: 报错，提示 schema 缺失（生产模式）
# 或: 有 warning 日志（开发模式）

# 3. 恢复
mv extra_fields_schema.json.bak extra_fields_schema.json
```

**完成标准**:
- schema 文件缺失时生产模式不应静默继续
- 或：schema 缺失时明确 warning 日志 + 跳过（仅开发）
- 不再有 `except FileNotFoundError: pass` 的静默行为

**估时**: 30 min

---

### Group-C：运维可观测加固（7 项）

| ID | 描述 | 位置 | 估时 |
|----|------|------|------|
| H11 | dev compose 仍暴露 5432 + 默认弱密码 | docker-compose.yml:22,40,44 | 15 min |
| H12 | 多 worker 指标分片 | monitoring.py:145-170 | 1.5 h |
| H13 | 缺 node-exporter/cadvisor/postgres_exporter | prometheus.yml:22-28 | 1 h |
| H14 | /metrics 公网可达无 auth | nginx.conf:48-51 / main.py:239-243 | 30 min |
| H15 | 各服务 1 副本无 HA | prod.yml | 文档评估 |
| H16 | 无 synthetic/外部探测 | monitoring/ | 1 h |
| H18 | instant_fixes.py 危险遗留未删 | scripts/instant_fixes.py | 5 min |

---

#### Group-C Step 1: H11 — dev compose 5432 暴露 + 默认弱密码

**描述**: `docker-compose.yml:22,40,44` 中 dev compose 将 PostgreSQL `5432:5432` 映射到宿主机 + 默认弱密码。

**文件位置**: `docker-compose.yml:22,40,44`

**修复步骤**:

```yaml
# docker-compose.yml:
# 将 ports 改为仅本地回环：
#   ports:
#     - "127.0.0.1:5432:5432"    # 仅本机可访问
# 或完全移除 ports 映射（通过 Docker 网络通信）

# 修改默认密码（db 段 environment）：
#   environment:
#     POSTGRES_PASSWORD: postgres  # 改为复杂随机密码
#   # 或: POSTGRES_PASSWORD: ${DEV_DB_PASSWORD:-dev-random-pwd-123!}
```

**验证方法**:
```bash
# 确认 dev compose 5432 不暴露给外部网络
docker compose -f docker-compose.yml config | grep -A2 "ports:"
# 预期: 127.0.0.1:5432:5432（或无 ports 段）

# 从其他机器尝试连接（应失败）
nc -zv <host-ip> 5432
# 预期: Connection refused
```

**完成标准**:
- dev compose 中 DB 端口仅绑定 localhost（或不暴露）
- dev compose 中无硬编码弱密码
- 从宿主机外无法连接 dev DB

**估时**: 15 min

---

#### Group-C Step 2: H12 — 多 worker 指标聚合

**描述**: `/metrics` 使用进程内内存计数，多 worker 时每个 worker 独立计数→指标失真（如请求计数只反映命中该 worker 的量）。

**文件位置**: `monitoring.py:145-170`

**修复步骤**:

```python
# 方案A：prometheus_client multiprocess mode
# 设置环境变量:
#   PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
# 
# monitoring.py 中:
#   import prometheus_client
#   from prometheus_client import CollectorRegistry, multiprocess
#   
#   def metrics_app():
#       registry = CollectorRegistry()
#       multiprocess.MultiProcessCollector(registry)
#       return Response(
#           prometheus_client.generate_latest(registry),
#           media_type="text/plain"
#       )

# 方案B：使用 prometheus_fastapi_instrumentator（内置 multiproc 支持）
#   from prometheus_fastapi_instrumentator import Instrumentator
#   Instrumentator().instrument(app).expose(app)

# 注意事项：
# - PROMETHEUS_MULTIPROC_DIR 需要在所有 worker 间共享（挂载同一目录）
# - 需要定期清理 PROMETHEUS_MULTIPROC_DIR 中的过期文件
# - 需确认 gunicorn/uvicorn worker 类型支持 preload
```

**验证方法**:
```bash
# 启动多 worker 后：
# 向不同 worker 分别发请求，验证 /metrics 返回的计数是聚合值
for i in $(seq 1 100); do
  curl -s -o /dev/null https://localhost/products
done

# 查 metrics
curl -s https://localhost/metrics/prometheus | grep "http_requests_total"
# 预期: 计数 = 100（而非 ≈100/N 个 worker）
```

**完成标准**:
- `/metrics` 返回的是跨 worker 聚合值
- `PROMETHEUS_MULTIPROC_DIR` 已配置且共享
- 无多 worker 导致的指标分片/丢失

**估时**: 1.5 h

---

#### Group-C Step 3: H13 — exporter 补齐

**描述**: `prometheus.yml:22-28` 配置了 node-exporter/cadvisor/postgres_exporter 的 scrape target，但 compose 中未启动这些 exporter→两个 target 永久 DOWN。

**文件位置**: `prometheus.yml:22-28`

**修复步骤**:

```yaml
# prod.yml 中增加 exporter services:
#
# node-exporter:
#   image: prom/node-exporter:latest
#   volumes:
#     - /proc:/host/proc:ro
#     - /sys:/host/sys:ro
#     - /:/rootfs:ro
#   command:
#     - '--path.procfs=/host/proc'
#     - '--path.sysfs=/host/sys'
#     - '--path.rootfs=/rootfs'
#   restart: unless-stopped
#
# cadvisor:
#   image: gcr.io/cadvisor/cadvisor:latest
#   volumes:
#     - /:/rootfs:ro
#     - /var/run:/var/run:ro
#     - /sys:/sys:ro
#     - /var/lib/docker/:/var/lib/docker:ro
#   restart: unless-stopped
#
# postgres-exporter:
#   image: prometheuscommunity/postgres-exporter
#   environment:
#     DATA_SOURCE_NAME: "postgresql://postgres:${DB_PASSWORD}@db:5432/bilingual_cms?sslmode=disable"
#   restart: unless-stopped

# 同时更新 prometheus.yml 的 targets 确保地址与 service name 一致
```

**验证方法**:
```bash
# 启动所有 exporter
docker compose -f prod.yml up -d node-exporter cadvisor postgres-exporter

# 检查 prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
# 预期: 所有 targets health 均为 "up"

# 确认无 DOWN 的 scrape target
```

**完成标准**:
- node-exporter / cadvisor / postgres_exporter 容器正常启动
- Prometheus targets 页面无 DOWN 状态
- 可以查到主机/容器/数据库级别的基础指标

**估时**: 1 h

---

#### Group-C Step 4: H14 — /metrics 公网可达加访问控制

**描述**: `/metrics/prometheus` 经 nginx 公网可达，无 IP 白名单/无 auth（代码注释 "unauthenticated"）。

**文件位置**: `nginx.conf:48-51`、`main.py:239-243`

**修复步骤**:

```nginx
# nginx.conf:48-51，/metrics 路由加 IP 白名单：
#   location /metrics {
#       allow 10.0.0.0/8;       # 内网
#       allow 172.16.0.0/12;
#       allow 192.168.0.0/16;
#       allow 127.0.0.1;
#       deny all;                # 拒绝其他来源
#       proxy_pass http://backend:8000;
#   }

# 或：使用 basic auth
#   location /metrics {
#       auth_basic "Metrics";
#       auth_basic_user_file /etc/nginx/.htpasswd;
#       proxy_pass http://backend:8000;
#   }
```

**验证方法**:
```bash
# 从外部 IP 访问
curl -s -o /dev/null -w "%{http_code}\n" https://public-ip/metrics/prometheus
# 预期: 403 Forbidden

# 从内网/本地访问
curl -s -o /dev/null -w "%{http_code}\n" https://localhost/metrics/prometheus
# 预期: 200 OK
```

**完成标准**:
- 从公网 IP 访问 `/metrics` 返回 403
- 从信任的 IP 范围可正常访问
- prometheus server（同一 Docker 网络）仍可 scrape

**估时**: 30 min

---

#### Group-C Step 5: H15 — 单点故障评估

**描述**: prod.yml 中各服务只有 1 副本，无 HA。

**文件位置**: `prod.yml`

**修复步骤**:

```bash
# 1. 文档化单点影响评估（本文档即为评估记录）
# 2. 对核心无状态服务（backend / nginx）增加 replicas：
#   在 prod.yml backend 段:
#     deploy:
#       replicas: 2
# 3. 数据库 HA 需要额外方案（pgpool/patroni），Sprint-B 评估
```

**验证方法**:
```bash
# docker compose 本身不直接支持 replicas（需 swarm mode）
# 或使用 docker compose --scale:
docker compose -f prod.yml up -d --scale backend=2

# 确认两个 backend 实例均健康
docker compose -f prod.yml ps
```

**完成标准**:
- 单点故障清单已文档化（即本文档此条目）
- backend 至少有 2 副本配置（swarm 或 scale）
- 提供 HA 评估文档

**估时**: 文档评估（4 h，含 swarm 迁移评估）

---

#### Group-C Step 6: H16 — synthetic 探测

**描述**: 无任何外部/合成探测，仅靠 healthcheck + `up{}` 指标。

**文件位置**: `monitoring/`

**修复步骤**:

```yaml
# 在 prod.yml 中增加 blackbox-exporter：
#
# blackbox-exporter:
#   image: prom/blackbox-exporter:latest
#   volumes:
#     - ./deploy/prometheus/blackbox.yml:/etc/blackbox_exporter/config.yml
#   restart: unless-stopped

# prometheus.yml 增加 blackbox 探测 job:
#   - job_name: 'blackbox'
#     metrics_path: /probe
#     params:
#       module: [http_2xx]
#     static_configs:
#       - targets:
#         - https://localhost/health
#         - https://localhost/products
#     relabel_configs:
#       - source_labels: [__address__]
#         target_label: __param_target
#       - target_label: __address__
#         replacement: blackbox-exporter:9115

# 增加告警规则：
#   - alert: SiteDown
#     expr: probe_success == 0
#     for: 1m
#     labels:
#       severity: critical
#     annotations:
#       summary: "Site {{ $labels.instance }} is down"
```

**验证方法**:
```bash
# 检查 blackbox probe 指标
curl -s http://localhost:9090/api/v1/query?query=probe_success | jq .
# 预期: probe_success = 1

# 停掉 nginx 确认告警触发
docker compose -f prod.yml stop nginx
# 等待 1-2 min 后检查 alertmanager
```

**完成标准**:
- blackbox-exporter 运行且可探测 /health 端点
- probe_success 指标存在
- 站点下线时 1-2 分钟内触发告警

**估时**: 1 h

---

#### Group-C Step 7: H18 — 删除 instant_fixes.py

**描述**: `scripts/instant_fixes.py` 正则热补丁脚本为危险遗留物。

**文件位置**: `scripts/instant_fixes.py`

**修复步骤**:

```bash
# 1. 确认脚本内容无害后删除
cat scripts/instant_fixes.py  # 确认无关键逻辑
rm scripts/instant_fixes.py

# 2. 如有需要保留的逻辑，合并到正式代码中
# 3. 确认没有其他文件引用此脚本
grep -r "instant_fixes" . --include="*.py" --include="*.sh" --include="*.yml"
```

**验证方法**:
```bash
# 确认文件已删除
test -f scripts/instant_fixes.py && echo "STILL EXISTS" || echo "REMOVED"

# 确认无引用
grep -r "instant_fixes" . | wc -l
# 预期: 0
```

**完成标准**: `scripts/instant_fixes.py` 已删除，全仓无引用。

**估时**: 5 min

---

### Group-D：测试健康度修复（11 项 P2 插入 Sprint-A）

> 这些项为 P2 级别，但 P0-8/9 暴露的测试可信度问题是全局性风险，故将关键测试修复提前。

| ID | 描述 | 位置 | 估时 |
|----|------|------|------|
| M1 | pytest.ini 与 pyproject 双配置冲突 | pytest.ini / pyproject.toml | 30 min |
| M3 | CI Postgres 不可达时 conftest 静默 fallback SQLite→假绿 | conftest.py:30-54 | 30 min |
| M4 | users.py 写端点零覆盖（29%） | test_users.py / users.py | 3 h |
| M5 | 限流测试模糊 `in [401,429]` 恒真 | test_rate_limit.py | 30 min |
| M6 | 缺黑名单/过期 token fixture | test_auth.py | 1 h |
| M7 | tests/integration/ 空置 + import update 0% | tests/ / test_import.py | 2 h |
| M8 | 覆盖率极不均（users 29%/terms 44%/i18n 0%） | 全测试 | 持续 |
| M9 | /products/stats 整套 skip | test_products.py | 30 min |
| M2 | 无真实 E2E（伪 E2E + Playwright 未入 CI） | tests/e2e/ / .github/ | 3 h |
| — | CI 门禁与 BOM 检测接入 | .github/workflows/ | 1 h |
| — | test_terms.py 覆盖率从 44% 补到 70%+ | test_terms.py | 1 h |

---

#### Group-D Step 1: M1 — 合并 pytest 配置

**描述**: `pytest.ini` 与 `pyproject.toml` 中存在双重 pytest 配置，本地跑无覆盖率（CI 靠命令行显式传参）。

**文件位置**: `pytest.ini`、`pyproject.toml`

**修复步骤**:

```bash
# 1. 确认两个配置文件中的差异
diff <(grep -E "^\[|=" pytest.ini) <(sed -n '/\[tool.pytest/,/^\[/p' pyproject.toml)

# 2. 合并到 pyproject.toml（推荐）并删除 pytest.ini
# pyproject.toml 中保留完整配置：
#   [tool.pytest.ini_options]
#   testpaths = ["tests"]
#   addopts = "-v --cov=backend --cov-report=term-missing --cov-report=xml"
#   pythonpath = ["backend"]

# 3. 删除 pytest.ini
rm pytest.ini

# 4. 验证本地也能出覆盖率
pytest --cov=backend --cov-report=term -q 2>&1 | tail -5
```

**验证方法**:
```bash
# 本地运行确认覆盖率输出
pytest -q 2>&1 | tail -3
# 预期: 有 TOTAL 行和百分比

# 确认不是靠命令行显式传参
pytest -q  # 不带任何 --cov 参数
# 预期: 仍有 coverage 输出（来自 pyproject 配置）
```

**完成标准**:
- 只存在一处 pytest 配置（pyproject.toml 或 pytest.ini，非双份）
- 不带命令行参数运行 `pytest` 也输出覆盖率
- CI 中不再需要显式传 `--cov` 参数

**估时**: 30 min

---

#### Group-D Step 2: M3 — conftest 严格化（消除 SQLite 假绿）

**描述**: `conftest.py:30-54` 读 DATABASE_URL 但 CI Postgres 不可达时静默 fallback 到临时 SQLite→测试假绿。

**文件位置**: `conftest.py:30-54`

**修复步骤**:

```python
# conftest.py:30-54，当前逻辑（推测）:
#   db_url = os.getenv("DATABASE_URL")
#   if not db_url:
#       db_url = "sqlite:///./test.db"  # 静默 fallback
#
# 改为严格模式：
#   db_url = os.getenv("DATABASE_URL")
#   if not db_url:
#       raise RuntimeError(
#           "DATABASE_URL must be set for tests. "
#           "Running tests against SQLite when CI expects PostgreSQL "
#           "creates false confidence."
#       )
#   
#   # 可选：仅本地开发允许 SQLite fallback
#   if os.getenv("CI") and "postgresql" not in db_url:
#       raise RuntimeError(
#           f"CI must use PostgreSQL, got: {db_url}"
#       )
```

**验证方法**:
```bash
# 1. 不设 DATABASE_URL 跑测试
unset DATABASE_URL
pytest --co -q 2>&1 | tail -5
# 预期: 报错 "DATABASE_URL must be set"（而非静默 fallback 到 SQLite）

# 2. 设 DATABASE_URL 后正常
export DATABASE_URL="postgresql://postgres:test@localhost:5432/test_db"
pytest --co -q
# 预期: 正常收集和运行
```

**完成标准**:
- CI 环境下缺 DATABASE_URL / PostgreSQL 不可达时测试报错（不静默 fallback）
- 本地开发可保留 SQLite fallback（明确标注）
- 消除"以为在测 PostgreSQL 实际在测 SQLite"的假绿风险

**估时**: 30 min

---

#### Group-D Step 3: M4 — users.py 写端点补测

**描述**: `users.py` 中 create/update/delete/bulk 写端点完全无测试覆盖（29% 总覆盖率）。

**文件位置**: `test_users.py`、`users.py`

**修复步骤**:

```python
# test_users.py 补写端点测试：

def test_create_user(client, admin_token):
    """POST /users/ — 管理员创建用户"""
    resp = client.post("/users/",
        json={"username": "newuser", "email": "new@test.com", "password": "Str0ng!Pass"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert "password" not in data  # 响应不含密码

def test_create_user_duplicate(client, admin_token):
    """创建重名用户应返回 409"""
    resp = client.post("/users/", json={...}, headers=...)
    assert resp.status_code == 409

def test_create_user_unauthorized(client):
    """非管理员创建用户应返回 403"""
    resp = client.post("/users/", json={...})
    assert resp.status_code == 401

def test_update_user(client, admin_token):
    """PUT /users/{id} — 更新用户"""
    ...

def test_delete_user(client, admin_token):
    """DELETE /users/{id} — 删除用户"""
    ...

def test_bulk_create_users(client, admin_token):
    """POST /users/bulk — 批量创建"""
    ...

# 每个端点至少覆盖: 正常路径 / 权限不足 / 输入校验 / 边界条件
```

**验证方法**:
```bash
# 运行 users 测试并查覆盖率
pytest tests/test_users.py -v --cov=backend/routers/users --cov-report=term
# 预期: users.py 覆盖率 ≥ 60%（从 29% 提升）
```

**完成标准**:
- users.py 所有写端点（create/update/delete/bulk）至少 1 条测试
- 覆盖权限校验（非管理员 403）
- 覆盖输入校验（重复用户名 409、无效 email 422）
- users.py 覆盖率 ≥ 60%

**估时**: 3 h

---

#### Group-D Step 4: M5 — 限流测试严格化

**描述**: 限流测试用 `assert resp.status_code in [401, 429]` 断言，`in [401,429]` 恒真（任何状态码都在集合中判断前已通过）。

**文件位置**: `test_rate_limit.py`

**修复步骤**:

```python
# test_rate_limit.py 中：
# 原: assert resp.status_code in [401, 429]  # 几乎恒真
# 改为分场景精确断言:

# 未认证 → 401
resp = client.post("/auth/login", json={"username":"u","password":"p"})
assert resp.status_code == 401

# 超限 → 429
for i in range(limit + 5):
    resp = client.post(...)
    if i < limit:
        assert resp.status_code in [200, 401]  # 未超限
    else:
        assert resp.status_code == 429  # 精确 429

# 同时移除测试中的 clear_rate_limiter 调用
# 或确保各测试独立（用不同 IP/用户）
```

**验证方法**:
```bash
# 运行限流测试
pytest tests/test_rate_limit.py -v
# 预期: 全部通过，且确实有 429 断言被触发

# 确认测试失败时会真的失败：
# 临时注释掉限流装饰器，测试应失败
```

**完成标准**:
- 限流测试中 429 断言是精确的（`== 429`，不是 `in [...]`）
- `clear_rate_limiter` 不在测试中重置限流状态（或用独立测试用户）
- 测试失败时能真实反映限流异常

**估时**: 30 min

---

#### Group-D Step 5: M6 — 黑名单/过期 token fixture

**描述**: 测试中缺少黑名单 token 和过期 token 的 fixture。

**文件位置**: `test_auth.py`、`conftest.py`

**修复步骤**:

```python
# conftest.py 增加 fixture：

@pytest.fixture
def expired_token():
    """生成一个已过期的 JWT token"""
    import jwt
    from datetime import datetime, timedelta
    payload = {
        "sub": "testuser",
        "exp": datetime.utcnow() - timedelta(hours=1)  # 1 小时前过期
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")

@pytest.fixture
def blacklisted_token(client, admin_token):
    """生成一个已被加入黑名单的 token（登出后）"""
    # 先登录
    resp = client.post("/auth/login", json={"username":"u","password":"p"})
    token = resp.json()["access_token"]
    # 登出（进入黑名单）
    client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    return token

# test_auth.py 中使用：
def test_expired_token_rejected(client, expired_token):
    resp = client.get("/products", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401

def test_blacklisted_token_rejected(client, blacklisted_token):
    resp = client.get("/products", headers={"Authorization": f"Bearer {blacklisted_token}"})
    assert resp.status_code == 401
```

**验证方法**:
```bash
pytest tests/test_auth.py -v -k "expired or blacklisted"
# 预期: 测试通过，expired/blacklisted token 正确返回 401
```

**完成标准**:
- `conftest.py` 中有 `expired_token` 和 `blacklisted_token` fixture
- 对应测试验证过期/黑名单 token 返回 401
- 无假阳性（确认 token 确实过期/黑名单）

**估时**: 1 h

---

#### Group-D Step 6: M7/M8/M9 — 集成测试 + import update 补测 + stats 去 skip

**M7**: `tests/integration/` 空置 + import update 模式 0% 覆盖
**M8**: 覆盖率极不均（持续改进）
**M9**: `/products/stats` 整套 skip（2 passed 实为 pass）

**文件位置**: `tests/`、`test_import.py`、`test_products.py`

**修复步骤**:

```python
# M7: tests/integration/ 增加基本测试
# tests/integration/test_import_flow.py:
def test_import_to_export_flow(client, admin_token):
    """完整流程：上传 CSV → 导入成功 → 导出包含新数据"""
    with open("tests/fixtures/sample.csv", "rb") as f:
        resp = client.post("/import/upload", 
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": f})
    assert resp.status_code == 200
    imported_id = resp.json()["product_id"]
    
    # 导出验证
    resp = client.get("/export/products",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    # 验证导出中含有刚导入的数据

# M7: test_import.py 增加 update 模式测试
def test_import_update_existing(client, admin_token):
    """导入更新已有产品"""
    ...

# M9: /products/stats 去 skip
# test_products.py 中：
# 原: @pytest.mark.skip(reason="stats endpoint not ready")
# 改为：实际运行测试（如端点实现完整）
# 或定义 skip 条件：
#   @pytest.mark.skipif(not stats_enabled, reason="stats feature flag off")
def test_products_stats(client):
    resp = client.get("/products/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
```

**验证方法**:
```bash
# M7
pytest tests/integration/ -v
# 预期: 至少 1 条集成测试运行通过

# M8（持续跟踪）
pytest --cov=backend --cov-report=term 2>&1 | grep -E "users|terms|i18n|import"
# 预期: 各模块覆盖率逐步提升

# M9
pytest tests/test_products.py -v -k "stats"
# 预期: 实际运行（非 skip），passed
```

**完成标准**:
- `tests/integration/` 目录有 ≥2 条测试
- import update 模式有 ≥1 条测试
- `/products/stats` 测试不再 skip（或明确 skip 条件而非无条件 skip）
- 各模块覆盖率趋势：users ≥60%、terms ≥70%、import ≥30%

**估时**: 3 h（M7）+ 持续（M8）+ 30 min（M9）= 3.5 h

---

#### Group-D Step 7: M2 — E2E 测试框架搭建

**描述**: e2e 用 TestClient 伪 E2E（非真实浏览器）；前端 Playwright/vitest 未入 CI。

**文件位置**: `tests/e2e/`、`.github/workflows/`

**修复步骤**:

```bash
# 1. 安装 Playwright
pip install playwright
playwright install chromium

# 2. 编写真实 E2E 测试
# tests/e2e/test_login_flow.py:
#   def test_full_login_flow(page):
#       page.goto("https://localhost/login")
#       page.fill("[name=username]", "admin")
#       page.fill("[name=password]", "admin123")
#       page.click("button[type=submit]")
#       page.wait_for_url("**/dashboard")
#       assert page.locator(".user-menu").is_visible()

# 3. CI 中增加 Playwright 步骤
# .github/workflows/test.yml:
#   - name: Run Playwright E2E
#     run: |
#       docker compose -f docker-compose.yml up -d
#       sleep 10
#       pytest tests/e2e/ -v
```

**验证方法**:
```bash
# 本地运行 E2E
docker compose -f docker-compose.yml up -d
pytest tests/e2e/ -v
# 预期: E2E 测试通过（真实浏览器操作）
```

**完成标准**:
- 至少 1 条真实浏览器 E2E 测试（非 TestClient）
- Playwright 配置在 CI 中可运行
- 测试覆盖核心用户流程（登录→浏览→操作→登出）

**估时**: 3 h

---

### Group-E：文档契约止损（8 项）

| ID | 描述 | 位置 | 估时 |
|----|------|------|------|
| H30 | .env.example 默认 DATABASE_URL 占位值使一键启动失败 | .env.example:3 | 10 min |
| H31 | QUICKSTART 称有 frontend:3000/grafana:3001 但 compose 无 | QUICKSTART.md:23-25 | 10 min |
| H32 | DEPLOY.md 围栏损坏 + 第5节重复 | DEPLOY.md:120-146 | 20 min |
| M14 | PRD 7 处旧 data 路径 | PRD.md | 30 min |
| M15 | 配置矩阵缺失（6 compose + 3 .env 零说明） | docs/ | 1 h |
| — | .env.example 补充所有必填变量及说明 | .env.example | 15 min |
| — | api-reference 缺 /users/me 端点文档 | api-reference.md | 30 min |
| — | monitoring-guide 残留 2024 日志 | monitoring-guide.md | 10 min |

---

#### Group-E Step 1-8：文档快速止损

**H30 修复**:
```
# .env.example:3
# 原: DATABASE_URL=postgresql://user:pass@localhost:5432/db
# 改为: DATABASE_URL=postgresql://postgres:postgres@db:5432/bilingual_cms
# 加注释: # Docker compose 中 host 为 service name "db"，非 localhost
```

**H31 修复**:
```
# QUICKSTART.md:23-25
# 原: 访问 http://localhost:3000（frontend）/ http://localhost:3001（grafana）
# 改为: 访问 http://localhost:8000/docs（API 文档）/ http://localhost:9090（prometheus）
# 如 frontend/grafana 确实不在基础 compose 中，删除对应行
```

**H32 修复**:
```bash
# DEPLOY.md:120-146 修复围栏标记
# 将 `/ash` 改为 ```bash
# 将 `/ash` 改为 ```bash（4 处）
# 删除重复的第5节
```

**M14 修复**:
```bash
# PRD.md: 搜索并替换旧路径
# synonyms/ → data/synonyms/
# consistency-rules/ → data/consistency-rules/
```

**M15 修复**: 在 `docs/configuration-matrix.md` 中新建配置矩阵，列出 6 个 compose 文件 + 3 个 .env 文件的用途、依赖关系、各变量说明。

**api-reference 补全**: `api-reference.md` 增加 `/users/me` 端点（含请求/响应示例）。

**monitoring-guide 清理**: 搜索并删除/更新所有 "2024" 年份日志示例。

**验证**: 逐文件确认修改后无误。

**估时**: 合计约 3 h

---

## 三、Sprint-B（第 3-5 周）— 结构性还债

### 涉及漏洞清单（约 33 项 P2 + 低优长尾）

分组：**Group-F 架构演进** → **Group-G 依赖治理** → **Group-H 测试补齐** → **Group-I 运维增强** → **Group-J 文档长尾**

---

### Group-F：架构演进（5 项）

| ID | 描述 | 位置 | 估时 |
|----|------|------|------|
| M10 | i18n 死模块（0 引用，json 不存在） | backend/i18n/ | 1 h |
| M11 | 无 API 弃用/sunset 机制 | 架构决策 | 2 h |
| M12 | Refresh 7d 偏长 + 审计无保留策略 | config.py / audit | 30 min |
| M13 | 数据双加载契约（dictionary bind-mount vs 规则镜像内） | Dockerfile / prod.yml | 2 h |
| — | ADR-008~013 实施 | docs/adr/ | 持续 |

---

#### Group-F Step 1: M10 — i18n 死模块处理

**描述**: `backend/i18n/` 模块全仓 0 引用，且引用的 json 翻译文件不存在。

**文件位置**: `backend/i18n/`

**修复步骤**:

```bash
# 方案A（推荐）：删除死模块
rm -rf backend/i18n/

# 方案B：接入实际使用
# 如需国际化，正确接入 i18n 并添加翻译文件
# 确认所有路由使用 gettext 或类似方案

# 确认删除后全仓无引用
grep -r "import.*i18n\|from.*i18n" . --include="*.py"
```

**验证方法**:
```bash
# 方案A：确认删除后测试通过
pytest -q
# 预期: 收集数和通过数不变

# 方案B：切换语言设置确认生效
curl -H "Accept-Language: zh-CN" https://localhost/products
```

**完成标准**: 
- 方案A：i18n 模块已删除，无引用残留
- 方案B：i18n 模块接入实际使用，翻译文件存在且生效

**估时**: 1 h

---

#### Group-F Step 2: M11 — API 弃用/sunset 机制

**描述**: 无 API 版本管理和弃用通知机制→breaking change 直接破坏客户端。

**文件位置**: 新建 `docs/api-versioning.md` / `main.py`

**修复步骤**:

```python
# 1. 路由增加版本前缀
# main.py:
#   app.include_router(products.router, prefix="/api/v1")
# 旧路径保留并加 Sunset header:
#   @app.get("/products")
#   async def products_v0_deprecated(request: Request):
#       return JSONResponse(
#           content={"error": "deprecated", "migrate_to": "/api/v1/products"},
#           headers={"Sunset": "Sat, 31 Dec 2026 23:59:59 GMT",
#                    "Link": '</api/v1/products>; rel="successor-version"'}
#       )

# 2. 建立弃用时间表文档
# docs/api-versioning.md:
#   | 端点 | 弃用日期 | 移除日期 | 替代 |
#   | /products | 2027-01-01 | 2027-04-01 | /api/v1/products |
```

**验证方法**:
```bash
# 旧端点返回弃用头
curl -s -I https://localhost/products | grep -i "sunset\|deprecation"
# 预期: Sunset 头存在

# 新端点正常工作
curl -s https://localhost/api/v1/products | jq .
# 预期: 正常数据返回
```

**完成标准**:
- 至少 1 个旧端点返回 Sunset 头
- 文档中记录了弃用时间表
- 新版本端点可用

**估时**: 2 h

---

#### Group-F Step 3: M12 — Refresh TTL 缩短 + 审计保留策略

**描述**: Refresh token 7d TTL 偏长；审计表无自动清理/归档策略→无限增长。

**文件位置**: `config.py`、`models/audit.py`

**修复步骤**:

```python
# 1. TTL 缩短（已在 Sprint-Hotfix P0-5 中处理）
# REFRESH_TOKEN_EXPIRE_DAYS=7 → 1

# 2. 审计保留策略
# 方案A：定时清理脚本
#   DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '90 days';
# 方案B：按月归档
#   创建 audit_log_archive 表 + cron 每月归档

# 3. 在 config.py 中增加配置：
#   AUDIT_RETENTION_DAYS = 90

# 4. 定时任务（配合备份调度）:
#   cleanup_old_audit_logs.sh:
#     psql -c "DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '$RETENTION_DAYS days';"
```

**验证方法**:
```bash
# 确认清理脚本可执行
bash scripts/cleanup_audit.sh --dry-run

# 检查 audit_log 表大小
docker compose -f prod.yml exec db psql -U postgres -d bilingual_cms \
  -c "SELECT count(*) FROM audit_log;"
```

**完成标准**:
- Refresh TTL ≤ 1 天
- 审计保留策略已文档化和实现（清理脚本或归档流程）

**估时**: 30 min

---

#### Group-F Step 4: M13 — 数据双加载契约统一

**描述**: dictionary 走 bind-mount 加载，consistency rules 走镜像内 COPY→双契约易割裂。

**文件位置**: `Dockerfile`、`prod.yml`

**修复步骤**:

```bash
# 统一为 bind-mount（推荐，修改时无需 rebuild）
# 在 prod.yml backend service:
#   volumes:
#     - ./data/dictionary:/app/data/dictionary
#     - ./data/consistency-rules:/app/data/consistency-rules
# 在 Dockerfile 中去除 COPY data/ 指令

# 更新文档说明数据加载方式
```

**验证方法**:
```bash
# 修改 bind-mount 中的数据文件
echo "test" >> data/dictionary/sample.json
docker compose -f prod.yml restart backend
# 确认新数据生效（无需 rebuild 镜像）
```

**完成标准**:
- dictionary 和 consistency rules 使用相同加载方式（均为 bind-mount 或均为镜像内）
- 修改数据后无需 rebuild 镜像即可生效

**估时**: 2 h

---

### Group-G：依赖治理（4 项）

| ID | 描述 | 位置 | 估时 |
|----|------|------|------|
| H19 | requirements 全 `>=` 零锁定 + 无 lockfile；bcrypt 上限允许 4.1+ 与 passlib 冲突 | requirements.txt:8-9 | 2 h |
| H20 | python:3.12-slim 无 digest、psycopg2-binary 非生产推荐 | Dockerfile:1 / requirements.txt:17 | 1 h |
| H23 | term_dictionary.created_by 无 FK | term.py:20 | 30 min |
| H27 | 仅 1 个 Alembic 迁移，后续模型变更易 schema 漂移 | alembic/versions/ | 1 h |

---

#### Group-G Step 1: H19 — 依赖锁定 + 版本冲突修复

**描述**: `requirements.txt` 全使用 `>=` 无上限锁定，无 lockfile；bcrypt 上限允许 4.1+ 与 passlib 1.7.4 存在探测冲突。

**文件位置**: `requirements.txt:8-9`

**修复步骤**:

```bash
# 1. 生成锁定版本
pip freeze > requirements-lock.txt

# 2. requirements.txt 改为精确版本范围
# 原：
#   bcrypt>=3.2.0
#   passlib>=1.7.4
# 改为：
#   bcrypt>=3.2.0,<4.1
#   passlib>=1.7.4,<2.0

# 3. 考虑迁移方案（长期）
# 方案A：passlib → bcrypt 直接使用（passlib 已停滞维护）
# 方案B：bcrypt → argon2-cffi（更安全）
# 方案C：python-jose → PyJWT（jose 维护频率低）

# 4. 增加 hash 校验（pip install --require-hashes）
pip-compile --generate-hashes requirements.in > requirements.txt
```

**验证方法**:
```bash
# 确认无版本冲突
pip check

# 确认依赖可重装
pip install -r requirements.txt --dry-run

# 确认 passlib + bcrypt 组合正常工作
python -c "
from passlib.hash import bcrypt
h = bcrypt.hash('test')
assert bcrypt.verify('test', h)
print('PASS')
"
```

**完成标准**:
- requirements.txt 中所有依赖有合理上限版本
- bcrypt 上限 < 4.1（与 passlib 兼容）
- 生成了 lockfile 用于 CI 可重现构建
- `pip check` 无冲突

**估时**: 2 h

---

#### Group-G Step 2: H20 — Docker 基础镜像固化

**描述**: `Dockerfile:1` 使用 `python:3.12-slim` 无 digest→构建不可重现；`requirements.txt:17` 中 `psycopg2-binary` 非生产推荐。

**文件位置**: `Dockerfile:1`、`requirements.txt:17`

**修复步骤**:

```dockerfile
# Dockerfile:1
# 原:
#   FROM python:3.12-slim
# 改为（含 digest）:
#   FROM python:3.12-slim@sha256:<latest-digest>

# requirements.txt:17
# psycopg2-binary → psycopg2（或 psycopg[binary]）
# 如在 Alpine 上编译困难，可改为 psycopg2-binary 并加说明
```

```bash
# 获取最新 digest
docker pull python:3.12-slim
docker inspect python:3.12-slim --format='{{index .RepoDigests 0}}'
# 将输出填到 Dockerfile FROM 行
```

**验证方法**:
```bash
# 确认 digest 有效
docker pull python:3.12-slim@sha256:<digest>

# 确认 psycopg2 可正常工作
docker compose -f prod.yml up backend
docker compose -f prod.yml exec backend python -c "import psycopg2; print('OK')"
```

**完成标准**:
- Dockerfile FROM 行含 sha256 digest
- psycopg2 使用非 binary 版本（或在文档中说明 binary 版本的使用限制）
- 镜像构建可重现

**估时**: 1 h

---

#### Group-G Step 3: H23 — term_dictionary.created_by 加 FK

**描述**: `term.py:20` 中 `term_dictionary.created_by` 字段无外键约束→可能出现指向不存在用户的记录。

**文件位置**: `term.py:20`

**修复步骤**:

```python
# term.py:20，当前（推测）:
#   created_by = Column(Integer, nullable=True)
# 改为:
#   created_by = Column(
#       Integer,
#       ForeignKey("users.id", ondelete="SET NULL"),
#       nullable=True
#   )

# 生成 Alembic 迁移:
# alembic revision --autogenerate -m "add_fk_term_created_by"
# alembic upgrade head

# 确认现有数据无孤儿引用
# SELECT * FROM term_dictionary WHERE created_by NOT IN (SELECT id FROM users);
```

**验证方法**:
```bash
# 尝试插入不存在的 user_id
docker compose -f prod.yml exec db psql -U postgres -d bilingual_cms \
  -c "INSERT INTO term_dictionary (term, created_by) VALUES ('test', 99999);"
# 预期: ERROR: insert or update violates foreign key constraint

# 删除用户时确认对应 term 的 created_by 自动 SET NULL
```

**完成标准**:
- `term_dictionary.created_by` 有 FK 约束指向 `users.id`
- 至少 1 条 Alembic 迁移生成并应用
- 现有数据无孤儿引用（或已清理）

**估时**: 30 min

---

#### Group-G Step 4: H27 — Alembic 迁移补齐

**描述**: 仅有 1 个 Alembic 迁移文件，后续模型变更（如 H23 加 FK）易 schema 漂移。

**文件位置**: `alembic/versions/`

**修复步骤**:

```bash
# 1. 检查当前数据库与模型差异
alembic check  # 如不支持则用:
alembic revision --autogenerate -m "sync_current_schema"

# 2. 确认自动生成的迁移与实际模型一致
alembic upgrade head

# 3. CI 中加入 schema 一致性检查
# .github/workflows/test.yml:
#   - run: alembic check  # 或 alembic upgrade head --sql > /dev/null
```

**验证方法**:
```bash
# 确认无差异
alembic revision --autogenerate -m "check" --sql 2>&1 | grep "No changes"
# 预期: No changes detected

# 升级后确认
alembic upgrade head && alembic current
```

**完成标准**:
- 所有模型变更都有对应 Alembic 迁移
- `alembic upgrade head` 执行成功无报错
- CI 中有 schema 漂移检查

**估时**: 1 h

---

### Group-H：测试补齐（持续）

| ID | 描述 | 目标 | 估时 |
|----|------|------|------|
| — | terms.py 覆盖率 44% → 80%+ | test_terms.py | 2 h |
| — | users.py 覆盖率 29% → 70%+（续 M4） | test_users.py | 2 h |
| — | i18n 覆盖（如保留）或删除（如 M10 删除） | — | 0 或 1 h |
| — | schemas/ 覆盖 0% → 30%+ | test_schemas.py | 1 h |
| — | import.py 覆盖率 0% → 50%+ | test_import.py | 3 h |
| — | 整体覆盖率追回 70%+ | 全测试 | 持续 |

**所有测试补齐项的修复步骤**略（与 Group-D 模式相同：逐文件写 test_ 函数 + 覆盖率驱动）。

**完成标准**:
- 整体真实覆盖率 ≥ 70%（不含粉饰排除项）
- 无模块覆盖率 < 30%
- 核心业务模块（users/terms/import/products）≥ 60%

---

### Group-I：运维增强（6 项）

| ID | 描述 | 位置 | 估时 |
|----|------|------|------|
| — | prometheus.yml 挂载未 :ro | prod.yml | 5 min |
| — | compose 注释与 depends_on 矛盾 | prod.yml | 15 min |
| — | 根 .dockerignore 缺 .env.* | .dockerignore | 5 min |
| H25 | 根目录残留调试文件清理 | 仓库根 | 5 min |
| H26 | 双 .env 密钥不同（根 vs backend） | .env vs backend/.env | 15 min |
| H28 | 上传临时文件仅 TTLCache 淘汰永不删 | import_.py:364,587 | 30 min |

---

#### Group-I Step 1: prometheus.yml 挂载 :ro

```yaml
# prod.yml prometheus service:
#   volumes:
#     - ./deploy/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro  # 加 :ro
```

#### Group-I Step 2: compose 注释与 depends_on 对齐

```bash
# prod.yml: 检查每个 service 的 depends_on 是否与注释中描述的一致
grep -A5 "depends_on" prod.yml
# 修正矛盾处
```

#### Group-I Step 3: .dockerignore 补 .env.*

```bash
# .dockerignore 追加:
echo ".env.*" >> .dockerignore
```

#### Group-I Step 4: H25 根残留文件清理

```bash
# 删除调试残留
rm -f _patch_auth.py temp_patch1.txt nul
```

#### Group-I Step 5: H26 双 .env 统一

```bash
# 确保根 .env 和 backend/.env 中 SECRET_KEY 一致或明确分工
diff .env backend/.env
# 消除差异或文档化分工（如：根 .env 仅 compose 变量，backend/.env 仅应用变量）
```

#### Group-I Step 6: H28 上传临时文件清理

```python
# import_.py:364,587
# 增加文件清理逻辑（在 TTLCache 淘汰回调中或定时任务中）
# import atexit, os
# 
# def cleanup_temp_files():
#     for f in TEMP_FILE_CACHE.values():
#         try:
#             os.remove(f)
#         except OSError:
#             pass
# 
# atexit.register(cleanup_temp_files)

# 或在文件处理完成后立即删除：
#   try:
#       result = parse_file(temp_path)
#   finally:
#       if os.path.exists(temp_path):
#           os.remove(temp_path)
```

**验证方法**（H28）:
```bash
# 上传文件后检查临时目录
docker compose -f prod.yml exec backend ls /tmp/
# 预期: 处理完成后临时文件已删除
```

**完成标准**:
- 所有 6 项均修复
- `.dockerignore` 包含 `.env.*`
- 根目录无调试残留文件
- 上传临时文件处理完成后被删除

**估时**: 合计 1.5 h

---

### Group-J：文档长尾（6 项）

| ID | 描述 | 位置 | 估时 |
|----|------|------|------|
| — | ADR-008~013 事实错误勘误（Archi 新#3） | docs/adr/ADR-008~013 | 1 h |
| — | api-reference 契约漂移残留 4 处 | api-reference.md | 30 min |
| — | CHANGELOG 结构倒置+损坏文本 | CHANGELOG.md | 15 min |
| — | README 死章节清理 | README.md | 15 min |
| — | user-manual 无截图 | docs/user-manual.md | 2 h |
| — | runbook 与 backup.sh 保留天数矛盾 | docs/runbook.md | 10 min |

**ADR-008~013 勘误**: 逐文件确认事实错误（如 ADR-008 中关于 refresh token 实现的描述需修正为"只写不读"的实际情况）。

**api-reference 契约漂移**: 对比实际 API 响应与文档，修正 4 处不一致。

**CHANGELOG**: 修正倒置的版本顺序 + 修复损坏/garbled 文本。

**README**: 删除无效章节链接和过时内容。

**user-manual**: 增加关键页面截图（登录、产品管理、导入导出）。

**runbook 保留天数矛盾**: 统一 `backup.sh`（如 30 天）和 runbook 中的保留天数描述。

**估时**: 合计约 4 h

---

## 四、验证矩阵总表

> 全部 73 项漏洞的修复步骤摘要、验证方法、完成标准、估时汇总。

| 漏洞ID | 阶段 | 修复步骤摘要 | 验证命令/方法 | 完成标准 | 估时 |
|--------|------|-------------|-------------|---------|------|
| P0-1 | Hotfix | 创建 `deploy/nginx/ssl/`，放入 TLS 证书（自签或 Let's Encrypt），部署前校验 | `docker compose -f prod.yml up nginx -d` + `curl -k https://localhost/health` | nginx 不 crash，HTTPS 可达 | 30 min |
| P0-2 | Hotfix | 根 .env SECRET_KEY 改占位值；prod 改 `${SECRET_KEY:?}`；轮换已暴露密钥 | `unset SECRET_KEY; docker compose -f prod.yml config -q 2>&1 \| grep "must be set"` | compose 缺密钥时报错，密钥已轮换 | 45 min |
| P0-3 | Hotfix | alertmanager 加 environment 段 + 换含 envsubst 镜像 | `docker compose -f prod.yml exec alertmanager cat /etc/alertmanager/alertmanager.yml` | SMTP 变量已替换，可发送测试邮件 | 1 h |
| P0-5 | Hotfix | auth.py refresh 改读 cookie；security.py cookie path/secure/httponly | `curl -c jar login; curl -b jar /auth/refresh \| jq .access_token` | refresh 从 cookie 读，body 不含 token | 1.5 h |
| P0-6 | Hotfix | /register 加 `@limiter.limit("3/minute")` | 连续 5 次注册请求，第 4 次起返回 429 | /register 被限流包裹，4+ 次返回 429 | 30 min |
| P0-7 | Hotfix | get_current_user 拦截 force_password_change；允许 /change-password /logout | `curl /products -H "Bearer <force_change_token>" → 403` | force_password_change 用户访问业务接口返回 403 | 30 min |
| P0-4 | Hotfix | ofelia/cron/systemd timer 落地备份调度 | `docker compose -f prod.yml logs ofelia \| grep backup` | 备份调度配置存在且可手动触发 | 45 min |
| P0-8 | Hotfix | test_terms.py 修正缩进（3 个 def 移到模块顶级）+ admin_token fixture | `pytest --co -q \| grep test_terms` | test_terms 贡献 ≥3 条，总收集数 ≥153 | 30 min |
| P0-9 | Hotfix | pyproject.toml 去除 exclude_lines 粉饰项 | `pytest --cov --cov-report=term \| tail -1` | 覆盖率输出真实值 ~69%，CI 门槛对齐 | 20 min |
| H1 | Hotfix | auth.py login 成功路径加 `await db.commit()` | `psql -c "SELECT last_login_at FROM users"` 确认登录后更新 | last_login_at 和 user_login 记录持久化 | 30 min |
| H3 | Hotfix | import_.py 顶部加 `logger = logging.getLogger(__name__)` | 上传损坏文件 → 返回 400，日志无 NameError | 解析失败返回 4xx 而非 500 | 15 min |
| H2 | Hotfix | 全仓 BOM 清理 + ci-content-gates 加 BOM 检测 | `xxd backup.sh \| head -1` + 全仓 BOM 扫描 | 全仓无 BOM 文件，CI 门禁含 BOM 检测 | 30 min |
| H4 | Sprint-A | config.py SECRET_KEY 缺时 fail-fast（raise RuntimeError） | `unset SECRET_KEY; docker compose up backend → 报错退出` | 生产缺密钥时 crash，多 worker 不随机 401 | 30 min |
| H9 | Sprint-A | redis.py fail-open → fail-closed；加线程锁；内存回退可工作 | `docker compose stop redis; curl /auth/login → 429` | Redis 不可用时限流拒绝而非放行 | 1.5 h |
| H24 | Sprint-A | logout 时 bump token_version + get_current_user 校验 version | 登出后用旧 token 访问 → 401 | 登出后旧 access token 立即失效 | 1 h |
| H29 | Sprint-A | .env ACCESS_TOKEN_EXPIRE_MINUTES 1440→30 | 解析 JWT exp 字段，确认 ≈1800s | access token TTL ≤ 30 min | 10 min |
| —(低#6) | Sprint-A | security.py refresh cookie path "/" → "/auth" | `curl -I login \| grep "Set-Cookie.*Path=/auth"` | cookie Path 为 /auth | 15 min |
| H5 | Sprint-A | consistency.py check_all_products 接受 product_ids 参数；export.py 去重查 | 导出操作 SQL 日志中 SELECT products 次数减少 | 单次导出仅一次全表扫描 | 1 h |
| H6 | Sprint-A | export.py 审计日志移到 404 之后、流式生成之后 | 401 访问后审计表无"成功"记录 | 非成功导出不产生审计记录 | 45 min |
| H7 | Sprint-A | 三层 BaseHTTPMiddleware → ASGI middleware 或合并 | StreamingResponse 流式特征保持 + 异常正常捕获 | 中间件 ≤2 层，功能不变 | 2 h |
| H8 | Sprint-A | import_.py:583 后加 write_audit_log（成功+失败路径） | import 后审计表有记录，含 filename + row count | import 操作有审计记录并持久化 | 45 min |
| H10 | Sprint-A | bcrypt→run_in_executor；文件 I/O→aiofiles 或线程池 | 10 并发 change_password 无超时/event loop 警告 | 异步端点不阻塞 event loop | 1.5 h |
| H21 | Sprint-A | csv_utils.py sanitize 加 `\n`/`\r` 移除 | 含换行的恶意输入无法构造多行 CSV | sanitize 移除换行符 | 15 min |
| H22 | Sprint-A | product.py:69-70 except FileNotFoundError: pass → raise/log | 删除 schema 文件后启动 → 报错/warning（非静默） | schema 缺失不再静默跳过 | 30 min |
| H11 | Sprint-A | docker-compose.yml DB ports 限 127.0.0.1 + 改弱密码 | `nc -zv <host-ip> 5432 → Connection refused` | dev DB 不暴露给外部网络 | 15 min |
| H12 | Sprint-A | 启用 PROMETHEUS_MULTIPROC_DIR + MultiProcessCollector | 多 worker 后 /metrics 计数为聚合值 | 指标跨 worker 聚合 | 1.5 h |
| H13 | Sprint-A | prod.yml 加 node-exporter/cadvisor/postgres_exporter | `curl localhost:9090/api/v1/targets \| jq` → 全部 UP | exporter 补齐，无 DOWN target | 1 h |
| H14 | Sprint-A | nginx /metrics location 加 allow/deny IP 白名单 | 公网 IP 访问 /metrics → 403 | /metrics 公网不可达 | 30 min |
| H15 | Sprint-A | 文档化单点清单 + backend --scale=2 评估 | `docker compose ps` 确认多实例 | 单点风险已评估和文档化 | 4 h |
| H16 | Sprint-A | blackbox-exporter + probe 配置 + SiteDown 告警 | `probe_success` 指标存在，停 nginx 触发告警 | synthetic 探测就位 | 1 h |
| H18 | Sprint-A | `rm scripts/instant_fixes.py` | `test -f scripts/instant_fixes.py → 不存在` | 危险脚本已删除 | 5 min |
| M1 | Sprint-A | 合并 pytest.ini 到 pyproject.toml，删除 pytest.ini | `pytest -q` 不带 --cov 仍有覆盖率输出 | 单一 pytest 配置源 | 30 min |
| M3 | Sprint-A | conftest 缺 DATABASE_URL 时 raise 而非 SQLite fallback | `unset DATABASE_URL; pytest → 报错退出` | CI 环境不静默 fallback SQLite | 30 min |
| M4 | Sprint-A | test_users.py 补 create/update/delete/bulk 测试 | `pytest test_users.py --cov=users --cov-report=term` | users.py 覆盖率 ≥60% | 3 h |
| M5 | Sprint-A | 限流测试 `in [401,429]` → 精确 `==429` | `pytest test_rate_limit.py -v` 全部通过 | 限流测试精确断言 429 | 30 min |
| M6 | Sprint-A | conftest 加 expired_token / blacklisted_token fixture | `pytest -k "expired or blacklisted"` 通过 | 过期/黑名单 token 有 fixture 和测试 | 1 h |
| M7/M8/M9 | Sprint-A | tests/integration/ 补测试 + import update 测试 + stats 去 skip | `pytest tests/integration/` 有测试运行 | integration 有 ≥2 条；stats 不 skip | 3.5 h |
| M2 | Sprint-A | Playwright 安装 + E2E 测试 + CI 集成 | `pytest tests/e2e/ -v` 真实浏览器通过 | E2E 有 ≥1 条 + CI 可运行 | 3 h |
| H30 | Sprint-A | .env.example DATABASE_URL 占位值改为 Docker 内可达 | `cp .env.example .env && docker compose up` 后端不 crash | 一键启动不因 DB URL 失败 | 10 min |
| H31 | Sprint-A | QUICKSTART.md 错误的 frontend/grafana 端口删除 | `grep -c "localhost:3000\|localhost:3001" QUICKSTART.md` | 端口描述与实际 compose 一致 | 10 min |
| H32 | Sprint-A | DEPLOY.md 围栏 `/ash` → ``` + 删除重复第 5 节 | 视觉检查 DEPLOY.md 渲染 | 围栏正确，无重复章节 | 20 min |
| M14 | Sprint-A | PRD.md 搜索替换 7 处旧 data 路径 | `grep "synonyms/\|consistency-rules/" PRD.md` | 路径指向新 data 目录 | 30 min |
| M15 | Sprint-A | 新建 docs/configuration-matrix.md | 确认文件存在且内容完整 | 配置矩阵覆盖所有 compose + .env | 1 h |
| — | Sprint-A | api-reference.md 补 /users/me 端点 | `grep "/users/me" api-reference.md` | /users/me 在文档中 | 30 min |
| — | Sprint-A | monitoring-guide.md 清理残留 2024 日志示例 | `grep "2024" monitoring-guide.md → 0` | 无过时日志示例 | 10 min |
| — | Sprint-A | .env.example 补充所有必填变量及说明 | 对照 config.py 检查 .env.example | 所有必填变量有说明 | 15 min |
| M10 | Sprint-B | i18n 模块删除或接入实际使用 | `grep -r "i18n" --include="*.py" → 0` 或翻译生效 | i18n 不再死模块 | 1 h |
| M11 | Sprint-B | API 增加 /api/v1 前缀 + 旧端点 Sunset 头 | `curl -I /products → Sunset 头存在` | API 弃用机制就位 | 2 h |
| M12 | Sprint-B | 审计保留策略（90 天清理脚本）+ TTL 缩短 | 审计表清理脚本可执行 | 审计有保留策略 + TTL ≤1d | 30 min |
| M13 | Sprint-B | 统一为 bind-mount 或镜像内（Dockerfile + prod.yml） | 修改数据文件后重启生效，无需 rebuild | 数据加载方式统一 | 2 h |
| H19 | Sprint-B | requirements 锁版本 + bcrypt<4.1 + lockfile | `pip check` 无冲突 | 依赖版本锁定，可重现构建 | 2 h |
| H20 | Sprint-B | Dockerfile FROM 加 sha256 digest；psycopg2 用非 binary | `docker pull` 确定 digest 有效 | 镜像构建可重现 | 1 h |
| H23 | Sprint-B | term_dictionary.created_by 加 FK → users.id | `INSERT INTO ... created_by=99999 → FK violation` | FK 约束存在，无孤儿引用 | 30 min |
| H27 | Sprint-B | Alembic revision --autogenerate 补齐迁移 | `alembic upgrade head` 成功 | model 与 migration 无差异 | 1 h |
| —(测试) | Sprint-B | terms/users/import 覆盖率补齐；整体追回 70%+ | `pytest --cov --cov-report=term` | 真实覆盖率 ≥70%，无模块 <30% | 持续 |
| — | Sprint-B | prometheus.yml :ro + compose 注释对齐 + .dockerignore .env.* | 各文件检查 | 3 项全修复 | 15 min |
| H25 | Sprint-B | `rm _patch_auth.py temp_patch1.txt nul` | `ls _patch_auth.py → No such file` | 根目录无调试残留 | 5 min |
| H26 | Sprint-B | 统一根 .env 与 backend/.env 密钥策略 | `diff .env backend/.env` 无冲突 | 密钥策略统一 | 15 min |
| H28 | Sprint-B | import_.py 临时文件处理完立即删除/atexit 清理 | 上传后在 /tmp/ 中确认无残留 | 临时文件不泄漏 | 30 min |
| —(F11) | Sprint-B | api-reference 修正 4 处契约漂移 | 对比文档与 API 实际响应 | 文档与 API 一致 | 30 min |
| —(D4) | Sprint-B | CHANGELOG 修正结构 + 损坏文本 | 视觉检查 CHANGELOG | 版本倒序，无乱码 | 15 min |
| —(F68) | Sprint-B | README 删除死章节 | 视觉检查 README | 无无效链接和过时章节 | 15 min |
| —(F67) | Sprint-B | user-manual 加截图（登录/产品/导入导出） | 文件检查 | 关键页面有截图 | 2 h |
| — | Sprint-B | runbook 保留天数与 backup.sh 统一 | `grep "retention\|保留\|天" runbook.md backup.sh` | 保留天数两处一致 | 10 min |
| —(ADR) | Sprint-B | ADR-008~013 勘误 + 未实施标记 | 逐文件确认描述与实现一致 | ADR 事实正确 | 1 h |

---

### 低优长尾项（约 17 项，按严重度顺序）

以下项目已在上述各 Sprint 中覆盖或由对应 Group 自然处理：

| 编号 | 描述 | 覆盖位置 | 状态 |
|------|------|---------|------|
| 低-1 | Redis 宕机限流失效无测试 | Group-A H9 修复后 Group-H 补测 | Sprint-B |
| 低-2 | 异常回文泄漏内部细节 | Group-B H7 中间件收敛中处理 | Sprint-A |
| 低-3 | CSRF 无 Origin 放行未文档化 | Group-E 文档止损补充 | Sprint-A |
| 低-4 | refresh cookie path 过宽 | Group-A Step 5 | Sprint-A |
| 低-5 | 裸 `except:` | Group-B H7/H9 中附带修复 | Sprint-A |
| 低-6 | 根 .dockerignore 缺 .env.* | Group-I Step 3 | Sprint-B |
| 低-7 | ADR-008 事实错误建议勘误 | Group-J | Sprint-B |
| 低-8 | compose 注释与 depends_on 矛盾 | Group-I Step 2 | Sprint-B |
| 低-9 | prometheus.yml 挂载未 :ro | Group-I Step 1 | Sprint-B |
| 低-10 | runbook 与 backup.sh 保留天数矛盾 | Group-J | Sprint-B |
| 低-11 | api-reference 契约漂移残留 4 处 | Group-J | Sprint-B |
| 低-12 | CHANGELOG 结构倒置+损坏文本 | Group-J | Sprint-B |
| 低-13 | api-reference 缺 /users/me | Group-E | Sprint-A |
| 低-14 | monitoring-guide 残留 2024 日志 | Group-E | Sprint-A |
| 低-15 | README 死章节 | Group-J | Sprint-B |
| 低-16 | user-manual 无截图 | Group-J | Sprint-B |
| 低-17 | ADR-008~013 存在但未实施 | Group-J + Group-F | Sprint-B |

---

## 五、依赖关系图

### 硬依赖（必须先修 A 才能修 B）

```
P0-1（TLS 证书）
  ├─→ P0-3（alertmanager）——需 nginx 起来后才能端到端验证告警
  ├─→ P0-5（refresh cookie）——需 HTTPS 才能验证 Secure cookie
  ├─→ P0-6/7（限流+改密）——需 nginx 可达
  ├─→ P0-8/9（测试可信度）——需 compose 全栈可起
  └─→ 所有后续验证

P0-2（根 .env 密钥治理）
  └─→ P0-3（alertmanager SMTP 变量依赖 .env 管理方式）

H2（BOM 清理）
  └─→ P0-4（备份调度）——backup.sh 含 BOM 无法执行

H4（密钥 fail-fast）
  └─→ P0-2 完成后才能安全实施（避免轮换前 crash）

H9（限流 fail-closed）
  └─→ M5（限流测试严格化）——需先修行为再修测试

M1（pytest 配置合并）
  └─→ 所有测试相关修复（M2-M9 等）
```

### 组间依赖

```
Sprint-Hotfix 完成
  ├─→ Group-A（认证安全）——需要 P0-5/6/7 作为基线
  ├─→ Group-B（代码正确性）——独立，可与 A 并行
  ├─→ Group-C（运维可观测）——需要 P0-1/2/3 环境可用
  │     └─→ Group-I（运维增强 Sprint-B）
  ├─→ Group-D（测试健康度）——需要 M1 配置合并先行
  └─→ Group-E（文档止损）——完全独立

Sprint-A 完成
  ├─→ Group-F（架构演进）——需要 H5/H6/H7/H8 修复验证后
  ├─→ Group-G（依赖治理）——独立
  ├─→ Group-H（测试补齐）——需要 Group-D 基线
  └─→ Group-J（文档长尾）——独立
```

### 可并行项

| 并行组 | 包含项 | 条件 |
|--------|--------|------|
| 并行-1 | P0-8 + P0-9（测试可信度）与 P0-5/6/7（认证） | 均可独立修复和验证 |
| 并行-2 | Group-A（认证）∥ Group-B（代码）∥ Group-E（文档） | 修改不同文件 |
| 并行-3 | Group-D（测试）∥ Group-C（运维） | 不同维度 |
| 并行-4 | Group-F ∥ Group-G ∥ Group-H ∥ Group-I ∥ Group-J | Sprint-B 各组件独立 |
| 并行-5 | M4（users 补测）∥ terms 补测 ∥ import 补测 | 不同测试文件 |

---

## ⚠️ 注意事项

1. **报告源自五成员实读代码复核**，修复前请对照当前代码版本确认文件行号。行号为报告产出时的快照，代码可能已有变动。
2. **nginx 证书为 Ops 前置依赖**：放 cert → 验证 nginx 启 → 才能验证其他 compose 变更。必须第一步执行。
3. **备份调度取决于 backup.sh 去 BOM 完成**：BOM 不清理则 backup.sh 无法执行。
4. **覆盖率变更涉及 CI/CD 流水线**：建议先本地验证再改 GitHub Actions。P0-9 中 CI 门槛降低需 CI 配置文件同步修改。
5. **密钥轮换（P0-2）将使所有现有 refresh token 失效**：执行前需通知所有用户，执行后需用户重新登录。
6. **H7（中间件收敛）风险最高**：涉及请求/响应处理链路变更，建议充分测试后再合入。
7. **低优项中"需进一步定位"的项目**：
   - 低-2（异常回文泄漏内部细节）：需审计所有 exception handler 返回内容
   - 低-5（裸 `except:`）：需全仓搜索 `except:` 无异常类型的情况
   - 低-11（api-reference 契约漂移 4 处）：需对比 API 实际响应逐一定位
8. **估时合计**：
   - Sprint-Hotfix：约 7.5 h（≤2 天，2 人并行）
   - Sprint-A：约 40 h（第 1-2 周，3-4 人并行）
   - Sprint-B：约 30 h（第 3-5 周，2-3 人并行）
   - **总计约 77.5 h**（约 10 人天）

---

> 本文档由工程保障团队技术文档师 Docu 基于五成员复核报告生成。
> 日期：2026-07-31
> 所有修复步骤、验证方法、完成标准均基于实际代码位置和实测验证编写。
> 如需调整优先级或补充新发现漏洞，请联系工程督导更新本计划。
