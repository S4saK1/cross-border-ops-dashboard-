FROM python:3.12-slim

WORKDIR /app

# 构建参数
ARG ENVIRONMENT=development

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 启动脚本（运行时初始化数据库并启动服务）
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# 健康检查 - 使用curl替代Python解释器
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# 容器启动时：初始化数据库 + 启动服务
CMD ["./docker-entrypoint.sh"]
