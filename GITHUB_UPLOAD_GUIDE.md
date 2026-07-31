# GitHub 仓库创建和代码推送指南

## 📋 前置条件

### 1. 安装 Git
```bash
# Windows (使用 Git for Windows)
# 下载地址: https://git-scm.com/download/win

# 或使用 Chocolatey
choco install git

# 或使用 Scoop
scoop install git
```

### 2. 配置 Git
```bash
# 设置用户信息
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 验证配置
git config --list
```

### 3. 安装 GitHub CLI (可选但推荐)
```bash
# Windows (使用 Chocolatey)
choco install gh

# 或使用 Scoop
scoop install gh

# 或下载安装程序
# https://cli.github.com/
```

## 🚀 步骤 1: 创建 GitHub 仓库

### 方式一: 使用 GitHub CLI (推荐)
```bash
# 1. 登录 GitHub
gh auth login

# 2. 创建仓库
gh repo create bilingual-product-cms --public --description "跨境产品资料中英对照系统 - 跨境卖家的产品资料一致性管理系统"

# 3. 克隆仓库到本地
gh repo clone bilingual-product-cms
```

### 方式二: 手动创建
1. 访问 https://github.com/new
2. 填写仓库信息:
   - **Repository name**: `bilingual-product-cms`
   - **Description**: `跨境产品资料中英对照系统 - 跨境卖家的产品资料一致性管理系统`
   - **Visibility**: Public
   - **Initialize this repository with**: 不要勾选任何选项
3. 点击 "Create repository"

## 🚀 步骤 2: 推送代码到 GitHub

### 1. 进入项目目录
```bash
cd "C:\Users\28900\WorkBuddy\bilingual-product-cms — 跨境产品资料中英对照系统"
```

### 2. 初始化 Git 仓库 (如果尚未初始化)
```bash
git init
```

### 3. 添加远程仓库
```bash
# 使用 HTTPS
git remote add origin https://github.com/your-username/bilingual-product-cms.git

# 或使用 SSH (推荐)
git remote add origin git@github.com:your-username/bilingual-product-cms.git
```

### 4. 添加文件到暂存区
```bash
# 添加所有文件
git add .

# 或选择性添加
git add README.md
git add CONTRIBUTING.md
git add CODE_OF_CONDUCT.md
git add CHANGELOG.md
git add LICENSE
git add QUICKSTART.md
git add OPEN_SOURCE_READINESS.md
git add .gitignore
git add .github/
git add backend/
git add frontend/
git add docs/
git add scripts/
git add deploy/
git add monitoring/
git add data/
```

### 5. 提交代码
```bash
git commit -m "feat: Initial release v1.0.0 - 跨境产品资料中英对照系统

- 完整的产品参数管理功能
- 术语词典和一致性检测
- 用户认证和权限管理
- CSV导入导出功能
- Docker容器化部署
- Prometheus监控集成
- 完整的API文档
- 开源社区配置"
```

### 6. 推送到 GitHub
```bash
# 推送到 main 分支
git push -u origin main
```

## 🚀 步骤 3: 创建第一个版本

### 1. 创建标签
```bash
git tag -a v1.0.0 -m "Release v1.0.0 - 跨境产品资料中英对照系统

## 主要功能
- 产品参数库 CRUD (中英字段一一对应)
- 术语词典 (内置 300+ 术语 + 用户自定义)
- CSV 导出 (阿里国际站 + Amazon 模板)
- 术语一致性检测 (L1 精确匹配 + 同义词)
- 批量导入 (Excel/CSV)
- 用户认证和权限管理 (JWT + RBAC)
- 审计日志记录
- Docker容器化部署
- Prometheus监控集成

## 技术栈
- 后端: Python FastAPI + SQLAlchemy ORM + PostgreSQL
- 前端: Next.js 14 + React 18 + TypeScript
- 缓存: Redis
- 部署: Docker + Docker Compose
- 监控: Prometheus + Grafana

## 文档
- README.md: 项目说明
- CONTRIBUTING.md: 贡献指南
- API文档: http://localhost:8000/docs
- 部署指南: docs/deployment-checklist.md"
```

### 2. 推送标签
```bash
git push origin v1.0.0
```

## 🚀 步骤 4: 配置 GitHub 仓库

### 1. 设置分支保护规则
1. 访问仓库的 Settings > Branches
2. 点击 "Add rule"
3. 配置规则:
   - Branch name pattern: `main`
   - Require pull request reviews before merging
   - Require status checks to pass before merging
   - Require branches to be up to date before merging

### 2. 配置 GitHub Actions
工作流文件已经创建在 `.github/workflows/ci.yml`，推送到 GitHub 后会自动运行。

### 3. 设置仓库网站
1. 访问仓库的 Settings > Pages
2. 选择 Source: Deploy from a branch
3. 选择 Branch: main
4. 选择文件夹: / (root)
5. 点击 Save

### 4. 配置 Issue 和 PR 模板
模板已经创建在 `.github/ISSUE_TEMPLATE/` 和 `.github/PULL_REQUEST_TEMPLATE.md`

## 🔧 常用 Git 命令

### 查看状态
```bash
git status
git log --oneline
git branch -a
```

### 创建新分支
```bash
# 创建并切换到新分支
git checkout -b feature/new-feature

# 推送新分支
git push -u origin feature/new-feature
```

### 合并分支
```bash
# 切换到 main 分支
git checkout main

# 拉取最新代码
git pull origin main

# 合并功能分支
git merge feature/new-feature

# 推送合并结果
git push origin main
```

### 创建 Pull Request
```bash
# 使用 GitHub CLI
gh pr create --title "feat: Add new feature" --body "Description of changes"

# 或手动在 GitHub 网站创建
```

## 📊 仓库管理

### 查看仓库信息
```bash
# 查看远程仓库
git remote -v

# 查看分支
git branch -a

# 查看标签
git tag
```

### 更新仓库
```bash
# 拉取最新代码
git pull origin main

# 推送本地更改
git push origin main
```

### 创建发布版本
```bash
# 创建新标签
git tag -a v1.1.0 -m "Release v1.1.0"

# 推送标签
git push origin v1.1.0

# 在 GitHub 创建 Release
gh release create v1.1.0 --title "Release v1.1.0" --notes-file CHANGELOG.md
```

## 🛡️ 安全最佳实践

### 1. 保护敏感信息
- 确保 `.env` 文件在 `.gitignore` 中
- 不要提交密码、密钥等敏感信息
- 使用环境变量存储配置

### 2. 代码审查
- 所有更改通过 Pull Request
- 至少一人审查后合并
- 自动化测试必须通过

### 3. 依赖管理
- 定期更新依赖
- 使用 `npm audit` 和 `pip audit` 检查漏洞
- 锁定依赖版本

## 📞 获取帮助

### GitHub 文档
- [GitHub Docs](https://docs.github.com/)
- [Git Handbook](https://guides.github.com/introduction/git-handbook/)
- [GitHub CLI Manual](https://cli.github.com/manual/)

### 社区支持
- [GitHub Discussions](https://github.com/features/discussions)
- [GitHub Issues](https://github.com/features/issues)

---

**注意**: 请将 `your-username` 替换为你的 GitHub 用户名。