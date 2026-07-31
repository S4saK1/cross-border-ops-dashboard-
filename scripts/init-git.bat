@echo off
REM 跨境产品资料中英对照系统 - Git 仓库初始化脚本
REM 使用方法: scripts\init-git.bat

echo 🚀 跨境产品资料中英对照系统 - Git 仓库初始化
echo =============================================

REM 检查是否在项目根目录
if not exist "README.md" (
    echo ❌ 错误: 请在项目根目录运行此脚本
    pause
    exit /b 1
)

REM 检查 Git 是否安装
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Git，请先安装 Git
    echo 下载地址: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo ✅ Git 已安装
git --version

REM 初始化 Git 仓库
if not exist ".git" (
    echo 📁 初始化 Git 仓库...
    git init
    echo ✅ Git 仓库初始化完成
) else (
    echo ℹ️  Git 仓库已存在
)

REM 配置 Git (如果尚未配置)
git config user.name >nul 2>&1
if errorlevel 1 (
    echo 📝 配置 Git 用户信息...
    set /p name="请输入您的姓名: "
    set /p email="请输入您的邮箱: "
    git config user.name "%name%"
    git config user.email "%email%"
    echo ✅ Git 用户信息配置完成
) else (
    echo ℹ️  Git 用户信息已配置
    git config user.name
    git config user.email
)

REM 添加 .gitignore
if exist ".gitignore" (
    echo ✅ .gitignore 文件已存在
) else (
    echo ⚠️  警告: 未找到 .gitignore 文件
)

REM 添加所有文件
echo 📦 添加文件到暂存区...
git add .

REM 显示状态
echo 📋 当前状态:
git status --short

REM 提交代码
echo 💾 提交代码...
set /p commit_message="请输入提交信息 (默认: 'feat: Initial release v1.0.0'): "
if "%commit_message%"=="" set commit_message="feat: Initial release v1.0.0"

git commit -m "%commit_message%"

echo ✅ 代码提交完成

REM 显示提交信息
echo 📝 提交信息:
git log --oneline -1

echo.
echo 🎉 Git 仓库初始化完成！
echo ========================
echo.
echo 📋 下一步操作:
echo 1. 创建 GitHub 仓库:
echo    gh repo create bilingual-product-cms --public
echo.
echo 2. 添加远程仓库:
echo    git remote add origin https://github.com/your-username/bilingual-product-cms.git
echo.
echo 3. 推送代码:
echo    git push -u origin main
echo.
echo 4. 创建版本标签:
echo    git tag -a v1.0.0 -m "Release v1.0.0"
echo    git push origin v1.0.0
echo.
echo 📚 详细指南请查看: GITHUB_UPLOAD_GUIDE.md
echo.
echo 📞 获取帮助:
echo   - GitHub CLI: gh --help
echo   - Git 文档: https://git-scm.com/doc
echo.
echo 感谢使用跨境产品资料中英对照系统！

pause