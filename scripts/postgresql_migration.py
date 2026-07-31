#!/usr/bin/env python3
"""
SQLite到PostgreSQL迁移脚本
用于将现有SQLite数据库迁移到PostgreSQL
"""
import os
import sys
import sqlite3
import psycopg2
import argparse
from pathlib import Path
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """数据库迁移类"""
    
    def __init__(self, sqlite_path: str, postgres_url: str):
        """
        初始化迁移配置
        
        Args:
            sqlite_path: SQLite数据库路径
            postgres_url: PostgreSQL连接URL
        """
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        
        # 验证SQLite数据库存在
        if not os.path.exists(sqlite_path):
            raise FileNotFoundError(f"SQLite数据库文件不存在: {sqlite_path}")
        
        logger.info(f"源数据库: {sqlite_path}")
        logger.info(f"目标数据库: {postgres_url}")
    
    def migrate(self):
        """执行迁移"""
        logger.info("开始数据库迁移...")
        
        # 1. 创建PostgreSQL数据库和表结构
        self._create_postgresql_tables()
        
        # 2. 迁移数据
        self._migrate_data()
        
        # 3. 验证迁移结果
        self._verify_migration()
        
        logger.info("数据库迁移完成！")
    
    def _create_postgresql_tables(self):
        """创建PostgreSQL表结构"""
        logger.info("创建PostgreSQL表结构...")
        
        # 连接到PostgreSQL
        conn = psycopg2.connect(self.postgres_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        try:
            # 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    last_login_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建产品表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id VARCHAR(36) PRIMARY KEY,
                    sku VARCHAR(100) UNIQUE NOT NULL,
                    product_name_zh VARCHAR(255) NOT NULL,
                    product_name_en VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    brand VARCHAR(100),
                    description_zh TEXT,
                    description_en TEXT,
                    price DECIMAL(10, 2),
                    currency VARCHAR(3) DEFAULT 'USD',
                    stock INTEGER DEFAULT 0,
                    color_zh VARCHAR(100),
                    color_en VARCHAR(100),
                    material_zh VARCHAR(100),
                    material_en VARCHAR(100),
                    size VARCHAR(50),
                    weight DECIMAL(10, 2),
                    weight_unit VARCHAR(10) DEFAULT 'kg',
                    length DECIMAL(10, 2),
                    width DECIMAL(10, 2),
                    height DECIMAL(10, 2),
                    dimension_unit VARCHAR(10) DEFAULT 'cm',
                    origin VARCHAR(100),
                    model_number VARCHAR(100),
                    extra_fields JSONB,
                    consistency_status VARCHAR(20) DEFAULT 'unchecked',
                    consistency_issues JSONB,
                    created_by VARCHAR(36) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            
            # 创建术语表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS terms (
                    id VARCHAR(36) PRIMARY KEY,
                    zh VARCHAR(255) NOT NULL,
                    en VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    note TEXT,
                    synonyms TEXT[],
                    platform_amazon VARCHAR(255),
                    platform_alibaba VARCHAR(255),
                    is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建审计日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    resource_type VARCHAR(50) NOT NULL,
                    resource_id VARCHAR(36),
                    details JSONB,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建刷新令牌黑名单表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS refresh_token_blacklist (
                    token_id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_terms_category ON terms(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_token_blacklist_user_id ON refresh_token_blacklist(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_token_blacklist_expires_at ON refresh_token_blacklist(expires_at)")
            
            logger.info("PostgreSQL表结构创建完成")
            
        except Exception as e:
            logger.error(f"创建表结构失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def _migrate_data(self):
        """迁移数据"""
        logger.info("开始迁移数据...")
        
        # 连接到SQLite
        sqlite_conn = sqlite3.connect(self.sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        
        # 连接到PostgreSQL
        postgres_conn = psycopg2.connect(self.postgres_url)
        postgres_cursor = postgres_conn.cursor()
        
        try:
            # 迁移用户数据
            self._migrate_table(sqlite_cursor, postgres_cursor, "users", "users")
            
            # 迁移产品数据
            self._migrate_table(sqlite_cursor, postgres_cursor, "products", "products")
            
            # 迁移术语数据
            self._migrate_table(sqlite_cursor, postgres_cursor, "terms", "terms")
            
            # 迁移审计日志数据
            self._migrate_table(sqlite_cursor, postgres_cursor, "audit_logs", "audit_logs")
            
            postgres_conn.commit()
            logger.info("数据迁移完成")
            
        except Exception as e:
            postgres_conn.rollback()
            logger.error(f"数据迁移失败: {e}")
            raise
        finally:
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()
    
    def _migrate_table(self, sqlite_cursor, postgres_cursor, sqlite_table: str, postgres_table: str):
        """迁移单个表"""
        logger.info(f"迁移表: {sqlite_table} -> {postgres_table}")
        
        # 获取SQLite表结构
        sqlite_cursor.execute(f"PRAGMA table_info({sqlite_table})")
        columns = [row[1] for row in sqlite_cursor.fetchall()]
        
        # 获取SQLite数据
        sqlite_cursor.execute(f"SELECT * FROM {sqlite_table}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            logger.info(f"表 {sqlite_table} 为空，跳过迁移")
            return
        
        # 构建插入语句
        placeholders = ', '.join(['%s'] * len(columns))
        insert_sql = f"INSERT INTO {postgres_table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # 插入数据
        postgres_cursor.executemany(insert_sql, rows)
        
        logger.info(f"迁移 {len(rows)} 行数据到 {postgres_table}")
    
    def _verify_migration(self):
        """验证迁移结果"""
        logger.info("验证迁移结果...")
        
        # 连接到SQLite
        sqlite_conn = sqlite3.connect(self.sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        
        # 连接到PostgreSQL
        postgres_conn = psycopg2.connect(self.postgres_url)
        postgres_cursor = postgres_conn.cursor()
        
        try:
            # 验证每个表的行数
            tables = ["users", "products", "terms", "audit_logs"]
            
            for table in tables:
                # SQLite行数
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                # PostgreSQL行数
                postgres_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                postgres_count = postgres_cursor.fetchone()[0]
                
                if sqlite_count == postgres_count:
                    logger.info(f"✓ 表 {table}: SQLite({sqlite_count}) == PostgreSQL({postgres_count})")
                else:
                    logger.warning(f"✗ 表 {table}: SQLite({sqlite_count}) != PostgreSQL({postgres_count})")
            
            logger.info("迁移验证完成")
            
        except Exception as e:
            logger.error(f"迁移验证失败: {e}")
            raise
        finally:
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="SQLite到PostgreSQL迁移工具")
    parser.add_argument("--sqlite-path", required=True, help="SQLite数据库文件路径")
    parser.add_argument("--postgres-url", required=True, help="PostgreSQL连接URL")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际执行迁移")
    
    args = parser.parse_args()
    
    try:
        migrator = DatabaseMigrator(args.sqlite_path, args.postgres_url)
        
        if args.dry_run:
            logger.info("模拟运行模式，不执行实际迁移")
            return
        
        migrator.migrate()
        
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()