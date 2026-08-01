# 变更日志

本文件记录跨境产品资料中英对照系统的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本控制](https://semver.org/lang/zh-CN/)。

## [2.0.0] - 2026-08-01

### Added
- 第二版本正式发布，CI 全绿：171 测试通过（2 跳过），覆盖率 72.45%
- 完善项目介绍：README 重写（技术架构图、安全设计、项目结构），clone 与 Issue 链接统一
- 默认管理员凭证环境变量化管理，密码强度验证

### Fixed
- 文档示例令牌脱敏，gitleaks 密钥扫描零命中
- 移除测试产物 backend/test_results.xml（含测试 JWT）
- flake8 规范清零：修复 215 处违规（空白、未用导入、布尔比较、裸 except 等）
- redis-py 3.0.1 → 8.0.1，兼容 Python 3.12（distutils 已移除）
- Docker 镜像名修正（ghcr 拒绝仓库名结尾连字符）
- 移除内部交付报告 deliverables/ 与 P1_P2_Issue_Report.md
- 废弃 GitHub 网页上传指南，仓库改为纯 Git 管理

## [1.1.0] - 2026-07-30

### Fixed
- Login session断裂：普通登录分支补 set_auth_cookies，前端补 setToken (F-01)
- 密码重置死代码：补 return 临时密码，删除不可达代码 (F-02)
- Alembic 迁移空壳：生成初始迁移，移除 create_all，支持 --skip-create-tables (F-03)
- Prometheus 可观测性：无鉴权 /metrics/prometheus，修复 scrape 路径和告警规则 (F-06/F-07/F-20)
- 生产端口暴露：移除 Postgres/Redis 宿主机映射，Nginx TLS 配置 (F-08/F-22)
- 文档事实源对齐：删除 11 个虚构 API 端点，修复 README 矛盾 (F-04/F-05/F-30)
- 导出一致性阻断 + 审计补充：export 前调用 ConsistencyEngine，登录/登出/导出写审计 (F-10/F-13)
- CI 门禁：--cov-fail-under=70 + gitleaks 密钥扫描 + PG/Redis 测试服务 (F-24/F-58)
- 安全测试：禁用用户/令牌吊销/XSS/SQL注入等 12 个新用例 (F-25~F-29)
- 两套审计实现合并为统一 core.audit.write_audit_log (F-61)
- 模型 FK 补全：audit_logs/token_blacklist 加 ForeignKey (F-38)
- JSON 方言统一：sqlalchemy.dialects.sqlite.JSON → sqlalchemy.JSON (F-14)
- CSV 注入防护覆盖到所有数值字段 (F-31)
- backup.sh 增强：pg_dump/SQLite 双模式 + GPG 加密 + S3/SFTP 远端 (F-21)
- JWT token type 校验：get_current_user 拒绝 refresh token 冒充 access token (F-11)
- SECRET_KEY 不再写入 .env 文件 (F-43/F-64)
- 调试脚本移出源码树 (F-60)
- 文档日期 2024→2026，README 重复小节清理 (F-50/F-52/F-57)

### Security
- COOKIE_SECURE 生产环境自动置 True
- 黑名单清理 startup 时自动执行 (F-39)
- 生产环境 Grafana 密码变强口令 (F-08)

## [1.0.0] - 2026-07-23

### 新增
- 产品参数库CRUD功能
- 术语词典管理（内置300+术语）
- CSV导出功能（阿里国际站+Amazon模板）
- 术语一致性检测（L1精确匹配+同义词）
- 批量导入功能（Excel/CSV）
- 用户认证和权限管理（JWT+RBAC）
- 审计日志记录
- Docker容器化部署
- Prometheus监控集成
- Grafana可视化仪表板

### 技术栈
- 后端：Python FastAPI + SQLAlchemy ORM
- 数据库：SQLite + PostgreSQL支持
- 前端：React/Next.js
- 认证：JWT + RBAC
- 测试：pytest + httpx + Playwright
- 部署：Docker + Docker Compose

### 文档
- 完整的API文档
- 部署指南
- 用户手册
- 备份策略文档
- 监控指南

## [0.9.0] - 2026-07-20

### 新增
- 初始项目结构
- 核心数据库模型
- 基础API框架
- 前端框架搭建

---

## 版本说明

### 版本号规则
- **主版本号（MAJOR）**：不兼容的API变更
- **次版本号（MINOR）**：向下兼容的功能性新增
- **修订号（PATCH）**：向下兼容的问题修正

### 变更类型
- **新增（Added）**：新功能
- **变更（Changed）**：对现有功能的变更
- **弃用（Deprecated）**：即将移除的功能
- **移除（Removed）**：已移除的功能
- **修复（Fixed）**：任何bug修复
- **安全（Security）**：安全相关的变更

### 贡献指南
1. 在`[未发布]`部分添加您的变更
2. 使用正确的变更类型标签
3. 提供清晰的变更描述
4. 关联相关的Issue或PR

---

## 计划中的功能

### V2.0
- 三审三校流程（草稿→校对→定稿）
- 多平台模板扩展（Shopee/Lazada/TikTok Shop/Temu）
- 图片/富媒体关联
- 多SKU/变体管理

### V3.0
- 国际化多语言界面
- API版本策略
- 高级数据分析
- 移动端支持
