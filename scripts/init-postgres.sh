#!/bin/bash
# PostgreSQL初始化脚本

set -e

# 创建数据库和用户
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 确保数据库存在
    SELECT 'CREATE DATABASE $POSTGRES_DB'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$POSTGRES_DB');
    
    -- 创建扩展
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    
    -- 设置数据库参数
    ALTER DATABASE $POSTGRES_DB SET timezone TO 'UTC';
    ALTER DATABASE $POSTGRES_DB SET default_text_search_config TO 'english';
    
    -- 创建索引（如果需要）
    -- CREATE INDEX IF NOT EXISTS idx_products_name ON products USING gin (name gin_trgm_ops);
    
    -- 授权
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
EOSQL

echo "PostgreSQL initialization completed successfully."