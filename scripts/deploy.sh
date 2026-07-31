#!/bin/bash

# CI/CD 部署脚本
# 用法: ./scripts/deploy.sh [环境] [操作]
# 示例: ./scripts/deploy.sh test deploy
#       ./scripts/deploy.sh production deploy
#       ./scripts/deploy.sh test rollback

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数：打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
ENVIRONMENT=${1:-"test"}
ACTION=${2:-"deploy"}

print_info "开始部署流程..."
print_info "环境: $ENVIRONMENT"
print_info "操作: $ACTION"

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    print_error "Docker 未运行，请先启动 Docker"
    exit 1
fi

# 检查docker-compose文件
case $ENVIRONMENT in
    "test")
        COMPOSE_FILE="docker-compose.test.yml"
        ;;
    "production")
        COMPOSE_FILE="docker-compose.prod.yml"
        ;;
    *)
        print_error "不支持的环境: $ENVIRONMENT"
        print_info "支持的环境: test, production"
        exit 1
        ;;
esac


# P0-2: 生产环境使用显式 env-file，防止自动读取根 .env
if [ "$ENVIRONMENT" = "production" ]; then
    ENV_FILE_ARG="--env-file .env.production"
else
    ENV_FILE_ARG=""
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "找不到 docker-compose 文件: $COMPOSE_FILE"
    exit 1
fi

# 执行操作
case $ACTION in
    "deploy")
        print_info "部署到 $ENVIRONMENT 环境..."
        
        # 停止现有容器
        print_info "停止现有容器..."
        docker-compose $ENV_FILE_ARG -f $COMPOSE_FILE down
        
        # 构建新镜像
        print_info "构建新镜像..."
        docker-compose $ENV_FILE_ARG -f $COMPOSE_FILE build --no-cache
        

        # P0-1: TLS 证书预检（生产环境必须）
        if [ "$ENVIRONMENT" = "production" ]; then
            if [ ! -f "deploy/nginx/ssl/fullchain.pem" ]; then
                print_error "FATAL: TLS 证书缺失 (deploy/nginx/ssl/fullchain.pem)"
                print_info "请先将正式证书放入 deploy/nginx/ssl/ 目录"
                print_info "开发/测试可用自签名证书: 参见 deploy/nginx/ssl/README.md"
                exit 1
            fi
            if [ ! -f "deploy/nginx/ssl/privkey.pem" ]; then
                print_error "FATAL: TLS 私钥缺失 (deploy/nginx/ssl/privkey.pem)"
                exit 1
            fi
            print_success "TLS 证书预检通过"
        fi
        # 启动服务
        print_info "启动服务..."
        docker-compose $ENV_FILE_ARG -f $COMPOSE_FILE up -d
        
        # 等待服务启动
        print_info "等待服务启动..."
        sleep 10
        
        # 健康检查
        print_info "执行健康检查..."
        if [ "$ENVIRONMENT" = "test" ]; then
            HEALTH_URL="http://localhost:8001/health"
        else
            HEALTH_URL="http://localhost:8000/health"
        fi
        
        for i in {1..30}; do
            if curl -f $HEALTH_URL > /dev/null 2>&1; then
                print_success "服务启动成功！"
                break
            fi
            if [ $i -eq 30 ]; then
                print_error "服务启动超时，请检查日志"
                docker-compose $ENV_FILE_ARG -f $COMPOSE_FILE logs
                exit 1
            fi
            sleep 2
        done
        
        print_success "部署完成！"
        ;;
        
    "rollback")
        print_warning "回滚到上一个版本..."
        
        # 这里可以添加回滚逻辑
        # 例如：使用上一个版本的镜像标签
        print_info "回滚功能待实现"
        ;;
        
    "status")
        print_info "检查服务状态..."
        docker-compose $ENV_FILE_ARG -f $COMPOSE_FILE ps
        ;;
        
    "logs")
        print_info "查看服务日志..."
        docker-compose $ENV_FILE_ARG -f $COMPOSE_FILE logs -f
        ;;
        
    *)
        print_error "不支持的操作: $ACTION"
        print_info "支持的操作: deploy, rollback, status, logs"
        exit 1
        ;;
esac

print_success "操作完成！"
