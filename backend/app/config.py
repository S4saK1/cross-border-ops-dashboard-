import secrets
import os
import json
import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import List

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    PROJECT_NAME: str = "跨境产品资料中英对照系统"
    DATABASE_URL: str = "sqlite:///./bilingual_cms.db"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False  # auto-set to True when ENVIRONMENT=production
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str = ""  # Empty = current domain
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    ENABLE_MONITORING: bool = True
    MONITORING_INTERVAL: int = 60

    UPLOAD_CACHE_TTL: int = 3600
    UPLOAD_CACHE_MAX_SIZE: int = 100

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    API_BASE_URL: str = "http://localhost:8000"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if os.getenv("ENVIRONMENT") == "production" and v.startswith("sqlite"):
            raise ValueError(
                "SQLite is not allowed in production. "
                "Set DATABASE_URL to a PostgreSQL connection string."
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v and len(v) >= 32:
            return v

        # Only fall back to .env in development; never in production (A-N1)
        if os.getenv("ENVIRONMENT", "development") != "production":
            env_file = Path(".env")
            if env_file.exists():
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("SECRET_KEY="):
                            key_value = line.split("=", 1)[1].strip()
                            if key_value and len(key_value) >= 32:
                                return key_value

        # Generate a new key for this session - DO NOT write to .env (F-43/F-64)
        new_key = secrets.token_urlsafe(32)
        logger.warning(
            "No valid SECRET_KEY found in environment or .env. "
            "Generated ephemeral key for this session. "
            "Set SECRET_KEY in environment for production."
        )
        return new_key

    @model_validator(mode='before')
    @classmethod
    def parse_allowed_origins(cls, values):
        if isinstance(values.get('ALLOWED_ORIGINS'), str):
            try:
                values['ALLOWED_ORIGINS'] = json.loads(values['ALLOWED_ORIGINS'])
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON in ALLOWED_ORIGINS: {values['ALLOWED_ORIGINS']}")
        # Auto-set COOKIE_SECURE in production
        if values.get('ENVIRONMENT') == 'production':
            values['COOKIE_SECURE'] = True

        return values

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
