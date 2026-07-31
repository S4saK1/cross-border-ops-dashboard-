# Access Token短效化 + Redis黑名单实施计划

## 1. 架构设计方案

### 1.1 系统架构图
当前系统 → 改进系统：
- **前端** → 不变
- **API层** → 添加Redis检查中间件
- **业务逻辑层** → 修改Token创建和验证逻辑
- **存储层** → SQLite + Redis（新增）

### 1.2 核心组件设计
1. **Redis连接管理器**：管理Redis连接池和故障转移
2. **Token黑名单服务**：统一的黑名单操作接口
3. **Redis检查中间件**：在Token验证流程中添加Redis检查
4. **配置管理**：添加Redis相关配置参数

## 2. 具体代码修改

### 2.1 配置变更 (`backend/app/config.py`)
```python
# 在Settings类中添加Redis配置
REDIS_URL: str = "redis://localhost:6379/0"
REDIS_PASSWORD: Optional[str] = None
REDIS_MAX_CONNECTIONS: int = 20
REDIS_SOCKET_TIMEOUT: int = 5
REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
REDIS_RETRY_ON_TIMEOUT: bool = True

# Token配置调整
ACCESS_TOKEN_EXPIRE_MINUTES: int = 20  # 从1440改为20分钟
REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 保持不变
```

### 2.2 Redis连接管理 (`backend/app/core/redis_manager.py`)
```python
"""Redis连接管理器"""
import redis
from redis import ConnectionPool, Redis
from redis.exceptions import ConnectionError, TimeoutError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisManager:
    """Redis连接管理器，支持连接池和故障转移"""
    
    _instance = None
    _pool = None
    
    @classmethod
    def get_instance(cls) -> 'RedisManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._init_pool()
    
    def _init_pool(self):
        """初始化Redis连接池"""
        try:
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
                decode_responses=True
            )
            logger.info("Redis连接池初始化成功")
        except Exception as e:
            logger.error(f"Redis连接池初始化失败: {e}")
            raise
    
    def get_client(self) -> Redis:
        """获取Redis客户端"""
        if self._pool is None:
            self._init_pool()
        return Redis(connection_pool=self._pool)
    
    def health_check(self) -> bool:
        """Redis健康检查"""
        try:
            client = self.get_client()
            return client.ping()
        except Exception as e:
            logger.error(f"Redis健康检查失败: {e}")
            return False
    
    def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.disconnect()
            self._pool = None
            logger.info("Redis连接池已关闭")

# 全局Redis管理器实例
redis_manager = RedisManager.get_instance()
```

### 2.3 Token黑名单服务 (`backend/app/core/token_blacklist_service.py`)
```python
"""Token黑名单服务"""
from datetime import datetime, timedelta
from typing import Optional
import json
import logging
from app.core.redis_manager import redis_manager
from app.config import settings

logger = logging.getLogger(__name__)

class TokenBlacklistService:
    """Token黑名单服务，支持Redis存储"""
    
    @staticmethod
    def _get_key(token_id: str) -> str:
        """生成Redis键名"""
        return f"token_blacklist:{token_id}"
    
    @staticmethod
    def _get_user_key(user_id: str) -> str:
        """生成用户Token集合键名"""
        return f"user_tokens:{user_id}"
    
    @classmethod
    def add_to_blacklist(cls, token_id: str, user_id: str, expires_at: datetime) -> bool:
        """将Token加入黑名单"""
        try:
            client = redis_manager.get_client()
            key = cls._get_key(token_id)
            user_key = cls._get_user_key(user_id)
            
            # 计算TTL（秒）
            ttl = int((expires_at - datetime.utcnow()).total_seconds())
            if ttl <= 0:
                ttl = 60  # 最小1分钟TTL
            
            # 存储Token信息
            token_data = {
                "token_id": token_id,
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            # 使用pipeline保证原子性
            with client.pipeline() as pipe:
                pipe.setex(key, ttl, json.dumps(token_data))
                pipe.sadd(user_key, token_id)
                pipe.expire(user_key, ttl + 60)  # 用户集合TTL比Token多1分钟
                pipe.execute()
            
            logger.info(f"Token {token_id} 已加入黑名单")
            return True
        except Exception as e:
            logger.error(f"Token加入黑名单失败: {e}")
            return False
    
    @classmethod
    def is_blacklisted(cls, token_id: str) -> bool:
        """检查Token是否在黑名单中"""
        try:
            client = redis_manager.get_client()
            key = cls._get_key(token_id)
            return client.exists(key)
        except Exception as e:
            logger.error(f"检查Token黑名单失败: {e}")
            # 降级策略：如果Redis不可用，假设Token未被吊销
            return False
    
    @classmethod
    def remove_from_blacklist(cls, token_id: str, user_id: str) -> bool:
        """从黑名单中移除Token（可选，用于调试）"""
        try:
            client = redis_manager.get_client()
            key = cls._get_key(token_id)
            user_key = cls._get_user_key(user_id)
            
            with client.pipeline() as pipe:
                pipe.delete(key)
                pipe.srem(user_key, token_id)
                pipe.execute()
            
            logger.info(f"Token {token_id} 已从黑名单移除")
            return True
        except Exception as e:
            logger.error(f"Token从黑名单移除失败: {e}")
            return False
    
    @classmethod
    def revoke_all_user_tokens(cls, user_id: str) -> bool:
        """撤销用户的所有Token"""
        try:
            client = redis_manager.get_client()
            user_key = cls._get_user_key(user_id)
            
            # 获取用户的所有Token ID
            token_ids = client.smembers(user_key)
            
            if not token_ids:
                return True
            
            # 批量删除Token
            with client.pipeline() as pipe:
                for token_id in token_ids:
                    key = cls._get_key(token_id)
                    pipe.delete(key)
                pipe.delete(user_key)
                pipe.execute()
            
            logger.info(f"用户 {user_id} 的所有Token已撤销")
            return True
        except Exception as e:
            logger.error(f"撤销用户Token失败: {e}")
            return False
    
    @classmethod
    def cleanup_expired_tokens(cls) -> int:
        """清理过期的Token（可选，Redis会自动清理）"""
        # Redis的TTL机制会自动清理过期Token
        # 此方法主要用于监控和统计
        try:
            client = redis_manager.get_client()
            # 扫描所有token_blacklist键
            cursor = 0
            cleaned = 0
            while True:
                cursor, keys = client.scan(cursor, match="token_blacklist:*", count=100)
                for key in keys:
                    ttl = client.ttl(key)
                    if ttl == -2:  # 键不存在
                        cleaned += 1
                if cursor == 0:
                    break
            
            logger.info(f"清理了 {cleaned} 个过期Token")
            return cleaned
        except Exception as e:
            logger.error(f"清理过期Token失败: {e}")
            return 0
```

### 2.4 修改安全模块 (`backend/app/core/security.py`)
```python
# 在现有函数基础上添加以下修改：

# 1. 修改create_access_token函数，缩短有效期
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # 修改：默认有效期从24小时改为20分钟
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# 2. 修改is_token_blacklisted函数，使用Redis
def is_token_blacklisted(token_id: str, db: Session = None) -> bool:
    """检查令牌是否在黑名单中（使用Redis）"""
    from app.core.token_blacklist_service import TokenBlacklistService
    return TokenBlacklistService.is_blacklisted(token_id)

# 3. 修改blacklist_refresh_token函数，使用Redis
def blacklist_refresh_token(token_id: str, user_id: str, expires_at: datetime, db: Session = None) -> None:
    """将刷新令牌加入黑名单（使用Redis）"""
    from app.core.token_blacklist_service import TokenBlacklistService
    TokenBlacklistService.add_to_blacklist(token_id, user_id, expires_at)

# 4. 修改revoke_all_user_tokens函数，使用Redis
def revoke_all_user_tokens(user_id: str, db: Session = None) -> None:
    """撤销用户的所有刷新令牌（使用Redis）"""
    from app.core.token_blacklist_service import TokenBlacklistService
    TokenBlacklistService.revoke_all_user_tokens(user_id)

# 5. 修改cleanup_expired_blacklist_entries函数，使用Redis
def cleanup_expired_blacklist_entries(db: Session = None) -> None:
    """清理过期的黑名单条目（使用Redis）"""
    from app.core.token_blacklist_service import TokenBlacklistService
    TokenBlacklistService.cleanup_expired_tokens()
```

### 2.5 添加Redis检查中间件 (`backend/app/middleware/redis_blacklist_middleware.py`)
```python
"""Redis黑名单检查中间件"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from app.core.token_blacklist_service import TokenBlacklistService
from app.core.security import decode_token

logger = logging.getLogger(__name__)

class RedisBlacklistMiddleware(BaseHTTPMiddleware):
    """Redis黑名单检查中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 跳过不需要认证的端点
        skip_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/docs",
            "/openapi.json",
            "/health",
            "/metrics"
        ]
        
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # 检查Authorization头
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)
        
        token = auth_header.split(" ")[1]
        
        try:
            # 解码Token
            payload = decode_token(token)
            token_id = payload.get("token_id")
            
            # 如果是Refresh Token，检查黑名单
            if payload.get("type") == "refresh" and token_id:
                if TokenBlacklistService.is_blacklisted(token_id):
                    logger.warning(f"已吊销的Token被访问: {token_id}")
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Token has been revoked"}
                    )
        except Exception as e:
            logger.error(f"Token黑名单检查失败: {e}")
            # 降级策略：如果Redis不可用，继续处理请求
            pass
        
        return await call_next(request)
```

### 2.6 更新主应用 (`backend/app/main.py`)
```python
# 在现有中间件配置中添加Redis黑名单中间件
from app.middleware.redis_blacklist_middleware import RedisBlacklistMiddleware

# 在应用初始化后添加
app.add_middleware(RedisBlacklistMiddleware)
```

### 2.7 更新依赖项 (`backend/requirements.txt`)
```
# 添加Redis依赖
redis>=4.0.0
```

## 3. 配置变更

### 3.1 环境变量配置
```env
# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=20
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_RETRY_ON_TIMEOUT=true

# Token配置
ACCESS_TOKEN_EXPIRE_MINUTES=20
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3.2 Docker Compose配置
```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    container_name: cms-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  redis_data:
```

## 4. 测试验证方案

### 4.1 单元测试
```python
# tests/test_token_blacklist_service.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.core.token_blacklist_service import TokenBlacklistService

class TestTokenBlacklistService:
    """Token黑名单服务测试"""
    
    @patch('app.core.token_blacklist_service.redis_manager')
    def test_add_to_blacklist_success(self, mock_redis):
        """测试成功添加Token到黑名单"""
        mock_client = MagicMock()
        mock_redis.get_client.return_value = mock_client
        
        token_id = "test-token-123"
        user_id = "user-123"
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        result = TokenBlacklistService.add_to_blacklist(token_id, user_id, expires_at)
        
        assert result == True
        mock_client.setex.assert_called_once()
        mock_client.sadd.assert_called_once()
    
    @patch('app.core.token_blacklist_service.redis_manager')
    def test_is_blacklisted_success(self, mock_redis):
        """测试检查Token是否在黑名单中"""
        mock_client = MagicMock()
        mock_redis.get_client.return_value = mock_client
        mock_client.exists.return_value = True
        
        token_id = "test-token-123"
        
        result = TokenBlacklistService.is_blacklisted(token_id)
        
        assert result == True
        mock_client.exists.assert_called_once_with(f"token_blacklist:{token_id}")
    
    @patch('app.core.token_blacklist_service.redis_manager')
    def test_revoke_all_user_tokens(self, mock_redis):
        """测试撤销用户的所有Token"""
        mock_client = MagicMock()
        mock_redis.get_client.return_value = mock_client
        mock_client.smembers.return_value = {"token1", "token2"}
        
        user_id = "user-123"
        
        result = TokenBlacklistService.revoke_all_user_tokens(user_id)
        
        assert result == True
        assert mock_client.delete.call_count == 3  # 2个token + 1个用户集合
```

### 4.2 集成测试
```python
# tests/test_redis_integration.py
import pytest
import redis
from app.core.redis_manager import redis_manager

class TestRedisIntegration:
    """Redis集成测试"""
    
    def test_redis_connection(self):
        """测试Redis连接"""
        assert redis_manager.health_check() == True
    
    def test_redis_operations(self):
        """测试Redis基本操作"""
        client = redis_manager.get_client()
        
        # 测试设置和获取
        client.set("test_key", "test_value")
        assert client.get("test_key") == "test_value"
        
        # 测试删除
        client.delete("test_key")
        assert client.get("test_key") is None
```

### 4.3 API端点测试
```python
# tests/test_auth_with_redis.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestAuthWithRedis:
    """带Redis的认证API测试"""
    
    def test_login_and_logout(self, client: TestClient):
        """测试登录和登出流程"""
        # 登录
        login_response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "StrongPassword123!"
        })
        
        assert login_response.status_code == 200
        tokens = login_response.json()
        
        # 登出
        logout_response = client.post("/api/v1/auth/logout", json={
            "token": tokens["refresh_token"]
        })
        
        assert logout_response.status_code == 200
        
        # 尝试使用已吊销的refresh token
        refresh_response = client.post("/api/v1/auth/refresh", json={
            "token": tokens["refresh_token"]
        })
        
        assert refresh_response.status_code == 401
```

## 5. 风险评估和回滚方案

### 5.1 风险评估
1. **Redis不可用风险**：Redis服务故障会导致黑名单检查失败
   - **缓解措施**：实现降级策略，Redis不可用时假设Token未被吊销
   - **监控**：添加Redis健康检查和告警

2. **数据一致性风险**：Redis和SQLite数据不一致
   - **缓解措施**：优先使用Redis，SQLite作为备份
   - **迁移策略**：逐步迁移现有黑名单数据到Redis

3. **性能影响风险**：Redis操作增加API延迟
   - **缓解措施**：使用连接池和批量操作
   - **监控**：监控Redis响应时间和连接数

### 5.2 回滚方案
1. **配置回滚**：将`ACCESS_TOKEN_EXPIRE_MINUTES`改回1440
2. **代码回滚**：恢复`security.py`中的原有函数
3. **中间件移除**：移除Redis黑名单中间件
4. **数据清理**：清理Redis中的黑名单数据

### 5.3 部署策略
1. **灰度发布**：先在小范围用户中测试
2. **监控指标**：监控Token验证成功率、Redis连接数、API响应时间
3. **回滚触发条件**：
   - Token验证失败率超过5%
   - Redis连接失败率超过10%
   - API平均响应时间增加超过200ms

## 6. 实施步骤时间表

1. **第1天**：配置Redis环境，添加依赖
2. **第2天**：实现Redis连接管理和Token黑名单服务
3. **第3天**：修改安全模块，添加中间件
4. **第4天**：编写测试用例，验证功能
5. **第5天**：文档更新，部署准备

## 7. 监控和运维

### 7.1 监控指标
- Redis连接数和健康状态
- Token黑名单操作成功率
- API认证延迟
- Token吊销事件计数

### 7.2 日志记录
- Token加入/移除黑名单事件
- Redis连接异常
- 降级策略触发事件

### 7.3 运维工具
- Redis监控脚本
- 黑名单数据清理工具
- 性能分析工具