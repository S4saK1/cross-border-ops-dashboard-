"""Redis client module"""
import redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Redis connection pool
redis_pool = None
redis_client = None


def get_redis_client():
    """Get Redis client instance"""
    global redis_client, redis_pool

    if redis_client is None:
        try:
            redis_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            redis_client = redis.Redis(connection_pool=redis_pool)
            redis_client.ping()
            logger.info("Redis connection successful")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            redis_client = None
            raise

    return redis_client


def close_redis_client():
    """Close Redis client connection"""
    global redis_client, redis_pool

    if redis_client:
        try:
            redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Failed to close Redis connection: {e}")
        finally:
            redis_client = None

    if redis_pool:
        try:
            redis_pool.disconnect()
        except Exception as e:
            logger.error(f"Failed to disconnect Redis pool: {e}")
        finally:
            redis_pool = None


def is_redis_available():
    """Check if Redis is available"""
    try:
        client = get_redis_client()
        return client.ping()
    except Exception:
        return False


# Token blacklist operations
class TokenBlacklist:
    """Token blacklist management"""

    @staticmethod
    def add_to_blacklist(token_id: str, user_id: str, expires_in: int):
        """Add token to blacklist"""
        try:
            client = get_redis_client()
            key = f"token_blacklist:{token_id}"
            client.setex(key, expires_in, user_id)
            logger.info(f"Token {token_id} added to blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to add token to blacklist: {e}")
            return False

    @staticmethod
    def is_blacklisted(token_id: str) -> bool:
        """Check if token is blacklisted"""
        try:
            client = get_redis_client()
            key = f"token_blacklist:{token_id}"
            return client.exists(key)
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False

    @staticmethod
    def remove_from_blacklist(token_id: str):
        """Remove token from blacklist"""
        try:
            client = get_redis_client()
            key = f"token_blacklist:{token_id}"
            client.delete(key)
            logger.info(f"Token {token_id} removed from blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to remove token from blacklist: {e}")
            return False

    @staticmethod
    def blacklist_all_user_tokens(user_id: str, expires_in: int):
        """Blacklist all tokens for a user"""
        try:
            client = get_redis_client()
            key = f"user_blacklist:{user_id}"
            client.setex(key, expires_in, "all_tokens_blacklisted")
            logger.info(f"All tokens for user {user_id} blacklisted")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist all user tokens: {e}")
            return False

    @staticmethod
    def is_user_blacklisted(user_id: str) -> bool:
        """Check if user is blacklisted"""
        try:
            client = get_redis_client()
            key = f"user_blacklist:{user_id}"
            return client.exists(key)
        except Exception as e:
            logger.error(f"Failed to check user blacklist: {e}")
            return False


# Cross-worker rate limiter (F-33)
class RateLimiter:
    """Redis-based sliding window rate limiter, shared across workers"""

    @staticmethod
    def check(client_key: str, max_requests: int = 5, window_seconds: int = 60) -> bool:
        """Check rate limit. Returns True if request is allowed."""
        try:
            client = get_redis_client()
            key = f"ratelimit:{client_key}"
            now = __import__("time").time()
            window_start = now - window_seconds
            client.zremrangebyscore(key, 0, window_start)
            current_count = client.zcard(key)
            if current_count >= max_requests:
                return False
            client.zadd(key, {str(now): now})
            client.expire(key, window_seconds)
            return True
        except Exception:
            raise  # P0: fail-closed — let caller decide, do not silently allow all

    @staticmethod
    def remaining(client_key: str, max_requests: int = 5, window_seconds: int = 60) -> int:
        """Return remaining requests in current window"""
        try:
            client = get_redis_client()
            key = f"ratelimit:{client_key}"
            now = __import__("time").time()
            window_start = now - window_seconds
            client.zremrangebyscore(key, 0, window_start)
            current_count = client.zcard(key)
            return max(0, max_requests - current_count)
        except Exception:
            return max_requests


# Cross-worker upload cache (F-11)
class UploadCache:
    """Redis-based cross-worker upload data cache"""

    PREFIX = "upload_cache:"

    @staticmethod
    def set(file_id: str, data: dict, ttl_seconds: int = 3600) -> bool:
        """Cache upload parse results"""
        try:
            client = get_redis_client()
            import json
            client.setex(f"{UploadCache.PREFIX}{file_id}", ttl_seconds, json.dumps(data))
            return True
        except Exception:
            return False

    @staticmethod
    def get(file_id: str) -> dict | None:
        """Get cached upload parse results"""
        try:
            client = get_redis_client()
            import json
            raw = client.get(f"{UploadCache.PREFIX}{file_id}")
            if raw:
                return json.loads(raw)
            return None
        except Exception:
            return None

    @staticmethod
    def delete(file_id: str) -> bool:
        """Delete cache entry"""
        try:
            client = get_redis_client()
            client.delete(f"{UploadCache.PREFIX}{file_id}")
            return True
        except Exception:
            return False

    @staticmethod
    def exists(file_id: str) -> bool:
        """Check if cache entry exists"""
        try:
            client = get_redis_client()
            return client.exists(f"{UploadCache.PREFIX}{file_id}") > 0
        except Exception:
            return False


# Cross-worker metrics aggregation (F-19)
class MetricsAggregator:
    """Redis-based cross-worker metrics aggregation"""

    @staticmethod
    def increment_counter(name: str, amount: int = 1, ttl: int = 86400) -> None:
        """Increment a counter"""
        try:
            client = get_redis_client()
            key = f"metrics:{name}"
            client.incrby(key, amount)
            client.expire(key, ttl)
        except Exception:
            pass

    @staticmethod
    def get_counter(name: str) -> int:
        """Get counter value"""
        try:
            client = get_redis_client()
            val = client.get(f"metrics:{name}")
            return int(val) if val else 0
        except Exception:
            return 0

    @staticmethod
    def record_timing(name: str, value_seconds: float) -> None:
        """Record timing value (stored in list, periodically aggregated)"""
        try:
            client = get_redis_client()
            key = f"metrics_timing:{name}"
            import json
            client.rpush(key, json.dumps({"v": value_seconds, "t": __import__("time").time()}))
            client.ltrim(key, -1000, -1)  # Keep last 1000 entries
            client.expire(key, 3600)
        except Exception:
            pass
