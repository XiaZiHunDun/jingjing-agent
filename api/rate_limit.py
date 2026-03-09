"""
速率限制模块

提供 API 请求速率限制功能，防止滥用。
支持基于 API Key 或 IP 地址的限制。
"""

import os
import time
from typing import Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from fastapi import Request, HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    enabled: bool = True


DEFAULT_CONFIG = RateLimitConfig(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
    burst_limit=int(os.getenv("RATE_LIMIT_BURST", "10")),
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
)


@dataclass
class ClientRateInfo:
    """客户端速率信息"""
    minute_requests: list = field(default_factory=list)
    hour_requests: list = field(default_factory=list)
    last_request: float = 0


class RateLimiter:
    """速率限制器（滑动窗口算法）"""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or DEFAULT_CONFIG
        self._clients: Dict[str, ClientRateInfo] = defaultdict(ClientRateInfo)
    
    def _get_client_key(self, request: Request, api_key: Optional[str] = None) -> str:
        """获取客户端标识"""
        if api_key:
            return f"key:{api_key}"
        
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _cleanup_old_requests(self, info: ClientRateInfo, now: float):
        """清理过期的请求记录"""
        minute_ago = now - 60
        hour_ago = now - 3600
        
        info.minute_requests = [t for t in info.minute_requests if t > minute_ago]
        info.hour_requests = [t for t in info.hour_requests if t > hour_ago]
    
    def check_rate_limit(
        self, 
        request: Request, 
        api_key: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Dict]:
        """
        检查是否超过速率限制
        
        Returns:
            (是否允许, 错误消息, 限制信息)
        """
        if not self.config.enabled:
            return True, None, {}
        
        now = time.time()
        client_key = self._get_client_key(request, api_key)
        info = self._clients[client_key]
        
        self._cleanup_old_requests(info, now)
        
        minute_count = len(info.minute_requests)
        hour_count = len(info.hour_requests)
        
        rate_info = {
            "client": client_key,
            "minute_count": minute_count,
            "minute_limit": self.config.requests_per_minute,
            "hour_count": hour_count,
            "hour_limit": self.config.requests_per_hour,
            "retry_after": 0
        }
        
        if info.last_request > 0:
            time_since_last = now - info.last_request
            if time_since_last < 0.1 and minute_count >= self.config.burst_limit:
                rate_info["retry_after"] = 1
                return False, "请求过于频繁，请稍后再试", rate_info
        
        if minute_count >= self.config.requests_per_minute:
            oldest = min(info.minute_requests) if info.minute_requests else now
            rate_info["retry_after"] = int(60 - (now - oldest)) + 1
            return False, f"超过每分钟请求限制 ({self.config.requests_per_minute}/分钟)", rate_info
        
        if hour_count >= self.config.requests_per_hour:
            oldest = min(info.hour_requests) if info.hour_requests else now
            rate_info["retry_after"] = int(3600 - (now - oldest)) + 1
            return False, f"超过每小时请求限制 ({self.config.requests_per_hour}/小时)", rate_info
        
        info.minute_requests.append(now)
        info.hour_requests.append(now)
        info.last_request = now
        
        return True, None, rate_info
    
    def get_client_stats(self, request: Request, api_key: Optional[str] = None) -> Dict:
        """获取客户端的速率统计"""
        now = time.time()
        client_key = self._get_client_key(request, api_key)
        info = self._clients[client_key]
        
        self._cleanup_old_requests(info, now)
        
        return {
            "client": client_key,
            "minute_used": len(info.minute_requests),
            "minute_limit": self.config.requests_per_minute,
            "minute_remaining": max(0, self.config.requests_per_minute - len(info.minute_requests)),
            "hour_used": len(info.hour_requests),
            "hour_limit": self.config.requests_per_hour,
            "hour_remaining": max(0, self.config.requests_per_hour - len(info.hour_requests))
        }
    
    def reset_client(self, client_key: str):
        """重置客户端的速率限制"""
        if client_key in self._clients:
            del self._clients[client_key]
    
    def get_all_clients(self) -> Dict:
        """获取所有客户端的统计（用于监控）"""
        now = time.time()
        result = {}
        
        for key, info in self._clients.items():
            self._cleanup_old_requests(info, now)
            result[key] = {
                "minute_count": len(info.minute_requests),
                "hour_count": len(info.hour_requests)
            }
        
        return result


rate_limiter = RateLimiter()


async def check_rate_limit(request: Request, api_key: Optional[str] = None):
    """
    FastAPI 依赖：检查速率限制
    
    用法：
        @router.get("/api/endpoint")
        async def endpoint(
            request: Request,
            _: None = Depends(check_rate_limit)
        ):
            ...
    """
    allowed, message, info = rate_limiter.check_rate_limit(request, api_key)
    
    if not allowed:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail={
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
