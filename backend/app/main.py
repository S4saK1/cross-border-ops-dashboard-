from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from app.config import settings
from app.database import engine
from app.api import auth, products, terms, export, audit, import_, users
from app.monitoring import PerformanceMonitoringMiddleware, get_all_metrics, get_prometheus_metrics
from app.middleware.exception_handler import GlobalExceptionHandlerMiddleware
from app.middleware.csrf import CSRFTokenMiddleware
from app.core.deps import require_admin
from logging_config import setup_logging
import time
import logging
import signal
import asyncio
from contextlib import asynccontextmanager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create tables

# Graceful shutdown handling
shutdown_event = asyncio.Event()
active_requests = 0

# P0-6: In-memory rate limiter for login + register endpoints (now delegated to Redis RateLimiter)


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: C901
    logger.info("Application starting up...")
    # ── 清理过期黑名单条目（F-39）──
    try:
        from app.database import SessionLocal
        from app.core.security import cleanup_expired_blacklist_entries
        db = SessionLocal()
        try:
            cleanup_expired_blacklist_entries(db)
            logger.info("Expired blacklist entries cleaned up on startup")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to cleanup blacklist entries: {e}")

    # ── 验证一致性规则文件 ──
    try:
        import json
        import os as _os
        _data_dir = _os.path.join(_os.path.dirname(__file__), "data")
        rules_path = _os.path.join(_data_dir, "consistency-rules.json")
        synonyms_path = _os.path.join(_data_dir, "synonyms.json")

        rules = {}
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Consistency rules file not found: {rules_path} — consistency checker will produce empty results")

        synonyms = {}
        try:
            with open(synonyms_path, "r", encoding="utf-8") as f:
                synonyms = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Consistency synonyms file not found: {synonyms_path} — synonym matching will not work")

        num_rules = (
            len(rules.get("rules", {}))
            + len(rules.get("standardization", []))
            + len(rules.get("auto_fix_rules", []))
        )
        num_synonym_groups = len(synonyms.get("synonym_groups", []))

        logger.info(
            "Consistency rules loaded: %d total (rules: %d, standardization: %d, auto_fix: %d)",
            num_rules,
            len(rules.get("rules", {})),
            len(rules.get("standardization", [])),
            len(rules.get("auto_fix_rules", [])),
        )
        logger.info("Consistency synonyms loaded: %d synonym groups", num_synonym_groups)

        if num_rules == 0 and synonyms:
            logger.warning("Consistency rules loaded 0 rules — consistency checker may produce empty results")
        if num_synonym_groups == 0 and rules:
            logger.warning("Consistency synonyms loaded 0 synonym groups — synonym matching will not work")
    except Exception as e:
        logger.warning(f"Failed to verify consistency rules on startup: {e}")

    yield
    logger.info("Application shutting down...")

    timeout = 30
    start_time = time.time()

    while active_requests > 0 and (time.time() - start_time) < timeout:
        logger.info(f"Waiting for {active_requests} active requests to complete...")
        await asyncio.sleep(1)

    if active_requests > 0:
        logger.warning(f"Forcefully shutting down with {active_requests} active requests remaining")
    else:
        logger.info("All requests completed, shutting down gracefully")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="not a translation tool, a consistency management system for cross-border sellers",
    version="2.1.0",
    lifespan=lifespan,
)

if settings.ENABLE_MONITORING:
    app.add_middleware(PerformanceMonitoringMiddleware)

app.add_middleware(GlobalExceptionHandlerMiddleware)
app.add_middleware(CSRFTokenMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)


@app.middleware("http")
async def login_rate_limiter(request: Request, call_next):
    if request.url.path in ("/api/v1/auth/login", "/api/v1/auth/register") and request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        window = 60
        max_req = 5

        from app.core.redis import RateLimiter
        allowed = RateLimiter.check(client_ip, max_requests=max_req, window_seconds=window)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": True,
                    "message": f"Too many requests. Try again in {window} seconds.",
                    "status_code": 429,
                },
            )

    response = await call_next(request)
    return response


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    global active_requests

    active_requests += 1

    try:
        if shutdown_event.is_set():
            return JSONResponse(
                status_code=503,
                content={"error": True, "message": "Service is shutting down", "status_code": 503}
            )

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"Path: {request.url.path} Method: {request.method} Status: {response.status_code} Duration: {process_time:.4f}s")
        return response
    finally:
        active_requests -= 1

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(terms.router, prefix="/api/v1/terms", tags=["terms"])
app.include_router(export.router, prefix="/api/v1/export", tags=["export"])
app.include_router(audit.router, prefix="/api/v1/audit-logs", tags=["audit"])
app.include_router(import_.router, prefix="/api/v1/import", tags=["import"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

app_start_time = time.time()


@app.get("/")
async def root():
    return {"message": "Bilingual Product CMS API", "docs": "/docs"}


@app.get("/health")
async def health():
    from fastapi.responses import JSONResponse
    health_status = {"status": "healthy", "timestamp": time.time()}

    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"
        logger.error(f"Health check failed - database error: {e}")
        return JSONResponse(content=health_status, status_code=503)

    return health_status


@app.get("/health/db")
async def health_db():
    """数据库健康检查端点（供运维脚本使用）"""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "database": "error", "timestamp": time.time()},
            status_code=503,
        )


@app.get("/metrics")
async def metrics(current_user=Depends(require_admin)):
    return get_all_metrics()


@app.get("/metrics/prometheus", response_class=PlainTextResponse)
async def prometheus_metrics_public():
    """Prometheus metrics endpoint (unauthenticated for scraping)"""
    metrics_text = get_prometheus_metrics()
    return PlainTextResponse(content=metrics_text, media_type="text/plain")


@app.get("/shutdown-status")
async def shutdown_status(current_user=Depends(require_admin)):
    return {
        "shutdown_requested": shutdown_event.is_set(),
        "active_requests": active_requests,
        "status": "shutting_down" if shutdown_event.is_set() else "running"
    }
