"""Performance monitoring and metrics collection module"""
import time
import psutil
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# F-19: Redis cross-worker metrics aggregator
_metrics_aggregator = None
try:
    from app.core.redis import MetricsAggregator
    _metrics_aggregator = MetricsAggregator
except ImportError:
    logging.getLogger(__name__).error("Redis not available, metrics aggregation disabled")

logger = logging.getLogger(__name__)

# Simple in-memory cache for metrics
_metrics_cache = {
    "request_count": 0,
    "error_count": 0,
    "total_response_time": 0.0,
    "start_time": datetime.now(),
    "endpoints": {},
    "status_codes": {},
    "response_time_buckets": {"0.1": 0, "0.5": 0, "1.0": 0, "2.0": 0, "5.0": 0, "+Inf": 0},
}


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Performance monitoring middleware"""

    async def dispatch(self, request: Request, call_next):  # noqa: C901
        start_time = time.time()

        _metrics_cache["request_count"] += 1
        if _metrics_aggregator is not None:
            try:
                _metrics_aggregator.increment_counter("request_count")
            except Exception:
                pass

        endpoint = f"{request.method} {request.url.path}"

        try:
            response = await call_next(request)
        except Exception as e:
            _metrics_cache["error_count"] += 1
            if _metrics_aggregator is not None:
                try:
                    _metrics_aggregator.increment_counter("error_count")
                except Exception:
                    pass
            logger.error(f"Request failed: {endpoint} - {str(e)}")
            raise

        process_time = time.time() - start_time
        _metrics_cache["total_response_time"] += process_time
        if _metrics_aggregator is not None:
            try:
                _metrics_aggregator.record_timing("response_time", process_time)
            except Exception:
                pass

        if endpoint not in _metrics_cache["endpoints"]:
            _metrics_cache["endpoints"][endpoint] = {
                "count": 0,
                "total_time": 0.0,
                "max_time": 0.0,
                "min_time": float("inf"),
            }

        endpoint_stats = _metrics_cache["endpoints"][endpoint]
        endpoint_stats["count"] += 1
        endpoint_stats["total_time"] += process_time
        endpoint_stats["max_time"] = max(endpoint_stats["max_time"], process_time)
        endpoint_stats["min_time"] = min(endpoint_stats["min_time"], process_time)

        for threshold in _metrics_cache["response_time_buckets"]:
            if threshold != "+Inf" and process_time <= float(threshold):
                _metrics_cache["response_time_buckets"][threshold] += 1
                break
        else:
            _metrics_cache["response_time_buckets"]["+Inf"] += 1

        status_code = response.status_code
        if status_code not in _metrics_cache["status_codes"]:
            _metrics_cache["status_codes"][status_code] = 0
        _metrics_cache["status_codes"][status_code] += 1

        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = str(id(request))

        return response


def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent": cpu_percent,
            "memory_total": memory.total,
            "memory_used": memory.used,
            "memory_percent": memory.percent,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "disk_percent": disk.percent,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}")
        return {}


def get_application_metrics() -> Dict[str, Any]:
    """Get application metrics"""
    uptime = (datetime.now() - _metrics_cache["start_time"]).total_seconds()

    return {
        "uptime_seconds": uptime,
        "total_requests": _metrics_cache["request_count"],
        "error_count": _metrics_cache["error_count"],
        "error_rate": _metrics_cache["error_count"] / max(_metrics_cache["request_count"], 1),
        "average_response_time": _metrics_cache["total_response_time"] / max(_metrics_cache["request_count"], 1),
        "endpoints": _metrics_cache["endpoints"],
        "status_codes": _metrics_cache["status_codes"],
        "timestamp": datetime.now().isoformat(),
    }


def get_all_metrics() -> Dict[str, Any]:
    """Get all metrics"""
    return {
        "system": get_system_metrics(),
        "application": get_application_metrics(),
        "timestamp": datetime.now().isoformat(),
    }


# Prometheus format metrics
def get_prometheus_metrics() -> str:
    """Generate Prometheus format metrics"""
    metrics = get_all_metrics()

    lines = []
    lines.append("# HELP app_requests_total Total number of requests")
    lines.append("# TYPE app_requests_total counter")
    lines.append(f"app_requests_total {metrics['application']['total_requests']}")

    lines.append("# HELP app_errors_total Total number of errors")
    lines.append("# TYPE app_errors_total counter")
    lines.append(f"app_errors_total {metrics['application']['error_count']}")

    lines.append("# HELP app_response_time_seconds Average response time")
    lines.append("# TYPE app_response_time_seconds gauge")
    lines.append(f"app_response_time_seconds {metrics['application']['average_response_time']}")

    lines.append("# HELP app_uptime_seconds Application uptime")
    lines.append("# TYPE app_uptime_seconds gauge")
    lines.append(f"app_uptime_seconds {metrics['application']['uptime_seconds']}")

    lines.append("# HELP system_cpu_percent CPU usage percentage")
    lines.append("# TYPE system_cpu_percent gauge")
    lines.append(f"system_cpu_percent {metrics['system'].get('cpu_percent', 0)}")

    lines.append("# HELP system_memory_percent Memory usage percentage")
    lines.append("# TYPE system_memory_percent gauge")
    lines.append(f"system_memory_percent {metrics['system'].get('memory_percent', 0)}")

    lines.append("# HELP system_disk_percent Disk usage percentage")
    lines.append("# TYPE system_disk_percent gauge")
    lines.append(f"system_disk_percent {metrics['system'].get('disk_percent', 0)}")

    # F-45: Histogram metrics
    lines.append("# HELP app_response_time_duration_ms Response time histogram")
    lines.append("# TYPE app_response_time_duration_ms histogram")
    buckets = _metrics_cache.get("response_time_buckets", {})
    cumulative = 0
    for threshold in ["0.1", "0.5", "1.0", "2.0", "5.0"]:
        cumulative += buckets.get(threshold, 0)
        le_ms = str(int(float(threshold) * 1000))
        lines.append(f"app_response_time_duration_ms_bucket{{le=\"{le_ms}\"}} {cumulative}")
    cumulative += buckets.get("+Inf", 0)
    lines.append(f"app_response_time_duration_ms_bucket{{le=\"+Inf\"}} {cumulative}")
    lines.append(f"app_response_time_duration_ms_count {cumulative}")
    lines.append(f"app_response_time_duration_ms_sum {_metrics_cache['total_response_time']}")

    return "\n".join(lines)
