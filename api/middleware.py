"""
FastAPI 中间件

提供请求日志、性能监控等功能。
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import api_logger, RequestStats


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
            
            RequestStats.record_request(
                endpoint=path,
                method=method,
                status_code=status_code if 'status_code' in dir() else 500,
                duration_ms=duration_ms
            )
        
        log_msg = f"{client_ip} | {method} {path} | {status_code} | {duration_ms:.1f}ms"
        
        if status_code >= 500:
            api_logger.error(log_msg)
        elif status_code >= 400:
            api_logger.warning(log_msg)
        else:
            api_logger.info(log_msg)
        
        return response
