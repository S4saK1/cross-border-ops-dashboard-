"""数据库初始化脚本 - 导入术语词典"""
import json
import os
import sys
import secrets
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, SessionLocal, Base
from app.models import UserProfile, Product, TermDictionary, AuditLog, RefreshTokenBlacklist
from app.core.security import get_password_hash
from app.utils.password_validator import validate_password_strength


def get_admin_credentials():
    """从环境变量获取管理员凭证，如果未设置则生成安全默认值"""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@bilingual-product-cms.com")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    
    # 如果未设置密码，生成一个安全的随机密码
    if not admin_password:
        admin_password = secrets.token_urlsafe(16)  # 生成24字符的安全密码
        print(f"[WARNING] ADMIN_PASSWORD not set. Generated secure password: {admin_password}")
        print("[SECURITY] Please save this password securely and change it on first login.")
        print("[SECURITY] Set ADMIN_PASSWORD environment variable for production use.")
    
    return admin_email, admin_password


def init_database(skip_create_tables: bool = False):
    """创建表并导入初始数据"""
    print("Creating database tables...")
    if not skip_create_tables:
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. 创建默认管理员（使用环境变量或安全默认值）
        admin_email, admin_password = get_admin_credentials()
        
        # 验证密码强度
        is_valid, errors = validate_password_strength(admin_password)
        if not is_valid:
            print(f"[ERROR] Admin password does not meet security requirements:")
            for error in errors:
                print(f"  - {error.message}")
            print("[SECURITY] Please set a strong ADMIN_PASSWORD environment variable.")
            # 使用生成的安全密码作为后备
            admin_password = secrets.token_urlsafe(16)
            print(f"[FALLBACK] Using generated secure password: {admin_password}")
        
        admin = db.query(UserProfile).filter(UserProfile.email == admin_email).first()
        if not admin:
            admin = UserProfile(
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                display_name="管理员",
                role="admin",
                force_password_change=True,  # 强制首次登录修改密码
            )
            db.add(admin)
            db.commit()
            print(f"Created default admin: {admin_email}")
            print(f"[SECURITY] Admin password set. First login will require password change.")
        else:
            print("Admin user already exists")

        # 2. 导入术语词典
        existing_count = db.query(TermDictionary).filter(TermDictionary.is_builtin == True).count()
        if existing_count == 0:
            # 支持 Docker 环境：/app/data 或 本地 ../data
            dict_path = os.path.join(os.path.dirname(__file__), "..", "data", "dictionary.json")
            if not os.path.exists(dict_path):
                dict_path = "/app/data/dictionary.json"
            with open(dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            terms = data.get("entries", [])
            print(f"Importing {len(terms)} terms...")
            for term in terms:
                db_term = TermDictionary(
                    zh=term["zh"],
                    en=term["en"],
                    category=term["category"],
                    note=term.get("note", ""),
                    synonyms=term.get("synonyms", []),
                    platform_amazon=term.get("platform_specific", {}).get("amazon"),
                    platform_alibaba=term.get("platform_specific", {}).get("alibaba"),
                    is_builtin=True,
                )
                db.add(db_term)

            db.commit()
            print(f"Imported {len(terms)} builtin terms")
        else:
            print(f"Builtin terms already exist ({existing_count} entries)")

        # 3. 统计
        user_count = db.query(UserProfile).count()
        term_count = db.query(TermDictionary).count()
        product_count = db.query(Product).count()
        print(f"\nDatabase initialized:")
        print(f"  Users: {user_count}")
        print(f"  Terms: {term_count}")
        print(f"  Products: {product_count}")

    finally:
        db.close()


if __name__ == "__main__":
    import sys
    skip = "--skip-create-tables" in sys.argv
    init_database(skip_create_tables=skip)
