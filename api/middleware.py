"""
FastAPI 中间件

提供请求日志、性能监控、速率限制等功能。
"""

import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import api_logger, RequestStats
from api.rate_limit import rate_limiter
from src.metrics import record_api_request, metrics_enabled


RATE_LIMITED_PATHS = ["/api/chat", "/api/knowledge/upload"]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        
        if not any(path.startswith(p) for p in RATE_LIMITED_PATHS):
            return await call_next(request)
        
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        
        allowed, message, info = rate_limiter.check_rate_limit(request, api_key)
        
        if not allowed:
            api_logger.warning(f"速率限制: {info.get('client')} - {message}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": message,
                    "retry_after": info.get("retry_after", 60),
                    "limit_info": {
                        "minute_used": info.get("minute_count", 0),
                        "minute_limit": info.get("minute_limit", 0),
                        "hour_used": info.get("hour_count", 0),
                        "hour_limit": info.get("hour_limit", 0)
                    }
                },
                headers={"Retry-After": str(info.get("retry_after", 60))}
            )
        
        response = await call_next(request)
        
        stats = rate_limiter.get_client_stats(request, api_key)
        response.headers["X-RateLimit-Limit"] = str(stats["minute_limit"])
        response.headers["X-RateLimit-Remaining"] = str(stats["minute_remaining"])
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            api_logger.error(f"请求处理异常: {method} {path} - {str(e)}")
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            final_status = status_code if 'status_code' in dir() else 500
            
            RequestStats.record_request(
                endpoint=path,
                method=method,
                status_code=final_status,
                duration_ms=duration_ms
            )
            
            if metrics_enabled():
                api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
                record_api_request(
                    endpoint=path,
                    method=method,
                    status_code=final_status,
                    duration_ms=duration_ms,
                    client_id=api_key or client_ip
                )
        
        log_msg = f"{client_ip} | {method} {path} | {status_code} | {duration_ms:.1f}ms"
        
        if status_code >= 500:
            api_logger.error(log_msg)
        elif status_code >= 400:
            api_logger.warning(log_msg)
        else:
            api_logger.info(log_msg)
        
        return response
