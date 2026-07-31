#!/bin/bash

# 跨境产品资料中英对照系统 - 开源项目设置脚本
# 使用方法: ./scripts/setup-open-source.sh

set -e

echo "🚀 跨境产品资料中英对照系统 - 开源项目设置"
echo "=========================================="

# 检查Git是否安装
if ! command -v git &> /dev/null; then
    echo "❌ 错误: 未找到Git，请先安装Git"
    exit 1
fi

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "⚠️  警告: 未找到Docker，将跳过Docker相关设置"
    SKIP_DOCKER=true
fi

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python 3.11+"
    exit 1
fi

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到Node.js，请先安装Node.js 18+"
    exit 1
fi

echo "✅ 环境检查通过"

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs
mkdir -p backup
mkdir -p temp

# 设置Python虚拟环境
echo "🐍 设置Python虚拟环境..."
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-cov flake8 mypy

echo "✅ Python依赖安装完成"

# 设置前端依赖
echo "📦 设置前端依赖..."
cd ../frontend
npm install

echo "✅ 前端依赖安装完成"

# 初始化数据库
echo "🗄️  初始化数据库..."
cd ../backend
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

python init_db.py

echo "✅ 数据库初始化完成"

# 运行测试
echo "🧪 运行测试..."
pytest --cov=app --cov-report=term-missing -v

echo "✅ 测试运行完成"

# 运行代码检查
echo "🔍 运行代码检查..."
flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
mypy app/ --ignore-missing-imports

echo "✅ 代码检查完成"

# 创建环境文件
echo "📝 创建环境文件..."
cd ..
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ 已创建.env文件，请根据需要修改配置"
else
    echo "ℹ️  .env文件已存在，跳过创建"
fi

# 初始化Git仓库
echo "🔧 初始化Git仓库..."
if [ ! -d .git ]; then
    git init
    git add .
    git commit -m "Initial commit: 跨境产品资料中英对照系统"
    echo "✅ Git仓库初始化完成"
else
    echo "ℹ️  Git仓库已存在，跳过初始化"
fi

# 显示项目信息
echo ""
echo "🎉 项目设置完成！"
echo "=================="
echo ""
echo "📋 项目信息:"
echo "  - 项目名称: 跨境产品资料中英对照系统"
echo "  - 版本: v1.0.0"
echo "  - 许可证: MIT"
echo ""
echo "🚀 快速开始:"
echo "  1. 后端开发:"
echo "     cd backend"
echo "     source venv/bin/activate"
echo "     uvicorn app.main:app --reload"
echo ""
echo "  2. 前端开发:"
echo "     cd frontend"
echo "     npm run dev"
echo ""
echo "  3. Docker部署:"
echo "     docker compose up -d"
echo ""
echo "📚 文档:"
echo "  - README.md: 项目说明"
echo "  - CONTRIBUTING.md: 贡献指南"
echo "  - API文档: http://localhost:8000/docs"
echo ""
echo "🔗 GitHub仓库设置:"
echo "  1. 创建GitHub仓库: bilingual-product-cms"
echo "  2. 添加远程仓库: git remote add origin <仓库地址>"
echo "  3. 推送代码: git push -u origin main"
echo ""
echo "⚠️  注意事项:"
echo "  - 请修改.env文件中的默认配置"
echo "  - 生产环境请使用强密码和密钥"
echo "  - 定期备份数据库"
echo "  - 监控系统运行状态"
echo ""
echo "📞 获取帮助:"
echo "  - GitHub Issues: 报告问题和功能请求"
echo "  - 文档: 查看项目文档"
echo "  - 社区: 参与讨论"
echo ""
echo "感谢使用跨境产品资料中英对照系统！"