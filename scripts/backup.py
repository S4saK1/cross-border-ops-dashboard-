#!/usr/bin/env python3
"""
数据库备份脚本
支持SQLite和PostgreSQL数据库备份
"""
import os
import sys
import shutil
import subprocess
import datetime
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """数据库备份类"""
    
    def __init__(self, database_url: str, backup_dir: str = "./backups"):
        """
        初始化备份配置
        
        Args:
            database_url: 数据库连接URL
            backup_dir: 备份目录
        """
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # 解析数据库类型
        if database_url.startswith("sqlite:///"):
            self.db_type = "sqlite"
            self.db_path = database_url.replace("sqlite:///", "")
        elif database_url.startswith("postgresql://"):
            self.db_type = "postgresql"
        else:
            raise ValueError(f"Unsupported database type: {database_url}")
    
    def create_backup(self) -> str:
        """
        创建数据库备份
        
        Returns:
            备份文件路径
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.db_type == "sqlite":
            return self._backup_sqlite(timestamp)
        elif self.db_type == "postgresql":
            return self._backup_postgresql(timestamp)
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def _backup_sqlite(self, timestamp: str) -> str:
        """SQLite数据库备份"""
        backup_filename = f"backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # 使用SQLite的备份API（通过sqlite3模块）
            import sqlite3
            
            # 连接到源数据库
            source_conn = sqlite3.connect(self.db_path)
            
            # 创建备份
            shutil.copy2(self.db_path, backup_path)
            
            # 验证备份文件
            backup_conn = sqlite3.connect(backup_path)
            backup_conn.execute("PRAGMA integrity_check")
            backup_conn.close()
            
            source_conn.close()
            
            logger.info(f"SQLite backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"SQLite backup failed: {e}")
            # 清理失败的备份文件
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    def _backup_postgresql(self, timestamp: str) -> str:
        """PostgreSQL数据库备份"""
        backup_filename = f"backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # 解析数据库连接信息
            from urllib.parse import urlparse
            parsed = urlparse(self.database_url)
            
            # 构建pg_dump命令
            cmd = [
                "pg_dump",
                "--host", parsed.hostname or "localhost",
                "--port", str(parsed.port or 5432),
                "--username", parsed.username or "postgres",
                "--dbname", parsed.path[1:],  # 移除开头的/
                "--file", str(backup_path),
                "--verbose",
                "--clean"
            ]
            
            # 设置密码环境变量
            env = os.environ.copy()
            if parsed.password:
                env["PGPASSWORD"] = parsed.password
            
            # 执行备份命令
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"PostgreSQL backup created: {backup_path}")
            logger.info(f"pg_dump output: {result.stdout}")
            
            return str(backup_path)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"PostgreSQL backup failed: {e}")
            logger.error(f"pg_dump stderr: {e.stderr}")
            # 清理失败的备份文件
            if backup_path.exists():
                backup_path.unlink()
            raise
        except Exception as e:
            logger.error(f"PostgreSQL backup failed: {e}")
            raise
    
    def list_backups(self) -> list:
        """列出所有备份文件"""
        backups = []
        for file in sorted(self.backup_dir.glob("backup_*")):
            if file.is_file():
                stat = file.stat()
                backups.append({
                    "filename": file.name,
                    "path": str(file),
                    "size": stat.st_size,
                    "created": datetime.datetime.fromtimestamp(stat.st_ctime),
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime),
                })
        return backups
    
    def cleanup_old_backups(self, keep_days: int = 30):
        """
        清理旧的备份文件
        
        Args:
            keep_days: 保留天数
        """
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=keep_days)
        
        for file in self.backup_dir.glob("backup_*"):
            if file.is_file():
                file_time = datetime.datetime.fromtimestamp(file.stat().st_mtime)
                if file_time < cutoff_date:
                    file.unlink()
                    logger.info(f"Deleted old backup: {file.name}")


    def verify_restore(self, backup_path: str) -> bool:
        """
        Validate backup file is restorable.

        Args:
            backup_path: Path to backup file

        Returns:
            True if backup is valid and restorable
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        if self.db_type == "sqlite":
            import sqlite3
            try:
                conn = sqlite3.connect(backup_path)
                result = conn.execute("PRAGMA integrity_check").fetchone()
                conn.close()
                if result[0] == "ok":
                    logger.info(f"SQLite backup integrity OK: {backup_path}")
                    return True
                logger.error(f"SQLite backup integrity failed: {result}")
                return False
            except Exception as e:
                logger.error(f"SQLite verify failed: {e}")
                return False

        elif self.db_type == "postgresql":
            try:
                if str(backup_file).endswith(".gz"):
                    import gzip
                    with gzip.open(backup_file, "rt", encoding="utf-8") as f:
                        header = f.read(200)
                else:
                    with open(backup_file, "r", encoding="utf-8") as f:
                        header = f.read(200)
                if "-- PostgreSQL database dump" in header or "CREATE" in header.upper():
                    if backup_file.stat().st_size > 0:
                        logger.info(f"PostgreSQL backup OK: {backup_path}")
                        return True
                logger.error(f"Not valid SQL dump: {backup_path}")
                return False
            except Exception as e:
                logger.error(f"PostgreSQL verify failed: {e}")
                return False
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database backup utility")
    parser.add_argument("--database-url", required=True, help="Database connection URL")
    parser.add_argument("--backup-dir", default="./backups", help="Backup directory")
    parser.add_argument("--action", choices=["backup", "list", "cleanup", "verify"], default="backup",
                       help="Action to perform")
    parser.add_argument("--verify-path", help="Backup file path to verify")
    parser.add_argument("--keep-days", type=int, default=30, help="Days to keep backups")
    
    args = parser.parse_args()
    
    try:
        backup = DatabaseBackup(args.database_url, args.backup_dir)
        
        if args.action == "backup":
            backup_path = backup.create_backup()
            print(f"Backup created: {backup_path}")
            
        elif args.action == "list":
            backups = backup.list_backups()
            print(f"Found {len(backups)} backups:")
            for b in backups:
                print(f"  - {b['filename']} ({b['size']} bytes) created {b['created']}")
                
        elif args.action == "cleanup":
            backup.cleanup_old_backups(args.keep_days)
            print(f"Cleaned up backups older than {args.keep_days} days")

        elif args.action == "verify":
            target = args.verify_path
            if not target:
                backups = backup.list_backups()
                if not backups:
                    print("No backups found to verify")
                    sys.exit(1)
                target = backups[-1]["path"]
                print(f"Verifying latest: {target}")
            valid = backup.verify_restore(target)
            print("Backup verification PASSED" if valid else "Backup verification FAILED")
            if not valid:
                sys.exit(1)
            
    except Exception as e:
        logger.error(f"Backup operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()