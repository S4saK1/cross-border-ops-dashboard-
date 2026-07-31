#!/bin/bash

# 健康检查脚本
# 用法: ./scripts/health-check.sh [环境]

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

print_info "开始健康检查..."
print_info "环境: $ENVIRONMENT"

# 根据环境设置URL
case $ENVIRONMENT in
    "test")
        BASE_URL="http://localhost:8001"
        ;;
    "production")
        BASE_URL="http://localhost:8000"
        ;;
    *)
        print_error "不支持的环境: $ENVIRONMENT"
        print_info "支持的环境: test, production"
        exit 1
        ;;
esac

# 检查服务是否运行
print_info "检查服务是否运行..."
if ! curl -f "$BASE_URL/health" > /dev/null 2>&1; then
    print_error "服务未运行或无法访问"
    exit 1
fi

print_success "服务正在运行"

# 检查健康端点
print_info "检查健康端点..."
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    print_success "健康检查通过"
else
    print_warning "健康检查返回非预期状态"
    echo "$HEALTH_RESPONSE"
fi

# 检查数据库连接
print_info "检查数据库连接..."
DB_RESPONSE=$(curl -s "$BASE_URL/health/db" 2>/dev/null || echo '{"status":"unknown"}')
if echo "$DB_RESPONSE" | grep -q '"status":"healthy"'; then
    print_success "数据库连接正常"
else
    print_warning "数据库连接检查失败或未配置"
fi

# 检查响应时间
print_info "检查响应时间..."
START_TIME=$(date +%s%N)
curl -f "$BASE_URL/health" > /dev/null 2>&1
END_TIME=$(date +%s%N)
RESPONSE_TIME=$(( (END_TIME - START_TIME) / 1000000 ))

if [ $RESPONSE_TIME -lt 1000 ]; then
    print_success "响应时间: ${RESPONSE_TIME}ms (优秀)"
elif [ $RESPONSE_TIME -lt 3000 ]; then
    print_warning "响应时间: ${RESPONSE_TIME}ms (一般)"
else
    print_error "响应时间: ${RESPONSE_TIME}ms (较慢)"
fi

# 检查容器状态（如果使用Docker）
if command -v docker &> /dev/null; then
    print_info "检查Docker容器状态..."
    CONTAINER_STATUS=$(docker ps --filter "name=bilingual-product-cms" --format "{{.Status}}" 2>/dev/null || echo "unknown")
    if echo "$CONTAINER_STATUS" | grep -q "Up"; then
        print_success "Docker容器运行正常"
    else
        print_warning "Docker容器状态: $CONTAINER_STATUS"
    fi
fi

# 检查系统资源
print_info "检查系统资源..."
if command -v docker &> /dev/null; then
    # 获取容器资源使用情况
    CONTAINER_ID=$(docker ps --filter "name=bilingual-product-cms" --format "{{.ID}}" 2>/dev/null | head -1)
    if [ -n "$CONTAINER_ID" ]; then
        CPU_USAGE=$(docker stats "$CONTAINER_ID" --no-stream --format "{{.CPUPerc}}" 2>/dev/null || echo "N/A")
        MEMORY_USAGE=$(docker stats "$CONTAINER_ID" --no-stream --format "{{.MemUsage}}" 2>/dev/null || echo "N/A")
        
        print_info "CPU使用率: $CPU_USAGE"
        print_info "内存使用: $MEMORY_USAGE"
    fi
fi

print_success "健康检查完成！"
