"""
指标采集器模块

提供各类指标的采集函数。
"""

import time
import socket
from typing import Optional, Dict, Any
from datetime import datetime

from .client import get_metrics_client, metrics_enabled


def record_api_request(
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    client_id: str = "unknown",
    request_size: int = 0,
    response_size: int = 0
) -> bool:
    """
    记录 API 请求指标
    
    Args:
        endpoint: 接口路径
        method: HTTP 方法
        status_code: 状态码
        duration_ms: 响应时间（毫秒）
        client_id: 客户端标识
        request_size: 请求大小（字节）
        response_size: 响应大小（字节）
    """
    if not metrics_enabled():
        return False
    
    client = get_metrics_client()
    if not client or not client.is_connected():
        return False
    
    return client.write_point(
        measurement="api_requests",
        tags={
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code),
            "client": client_id
        },
        fields={
            "duration_ms": float(duration_ms),
            "request_size": int(request_size),
            "response_size": int(response_size),
            "success": 1 if status_code < 400 else 0
        }
    )


def record_chat_metrics(
    session_id: str,
    input_length: int,
    output_length: int,
    total_duration_ms: float,
    tool_count: int = 0,
    has_error: bool = False
) -> bool:
    """
    记录对话指标
    
    Args:
        session_id: 会话 ID
        input_length: 输入长度
        output_length: 输出长度
        total_duration_ms: 总响应时间
        tool_count: 工具调用次数
        has_error: 是否有错误
    """
    if not metrics_enabled():
        return False
    
    client = get_metrics_client()
    if not client or not client.is_connected():
        return False
    
    return client.write_point(
        measurement="chat_metrics",
        tags={
            "session_id": session_id,
            "has_error": str(has_error).lower()
        },
        fields={
            "input_length": int(input_length),
            "output_length": int(output_length),
            "total_duration_ms": float(total_duration_ms),
            "tool_count": int(tool_count)
        }
    )


def record_tool_call(
    tool_name: str,
    session_id: str,
    duration_ms: float,
    success: bool = True,
    error_message: str = ""
) -> bool:
    """
    记录工具调用指标
    
    Args:
        tool_name: 工具名称
        session_id: 会话 ID
        duration_ms: 执行时间
        success: 是否成功
        error_message: 错误信息
    """
    if not metrics_enabled():
        return False
    
    client = get_metrics_client()
    if not client or not client.is_connected():
        return False
    
    return client.write_point(
        measurement="tool_calls",
        tags={
            "tool_name": tool_name,
            "session_id": session_id,
            "success": str(success).lower()
        },
        fields={
            "duration_ms": float(duration_ms),
            "error": error_message if not success else ""
        }
    )


def record_system_metrics() -> bool:
    """
    记录系统资源指标
    
    记录 CPU、内存、磁盘使用率等系统指标。
    """
    if not metrics_enabled():
        return False
    
    client = get_metrics_client()
    if not client or not client.is_connected():
        return False
    
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        hostname = socket.gethostname()
        
        return client.write_point(
            measurement="system_metrics",
            tags={
                "host": hostname
            },
            fields={
                "cpu_percent": float(cpu_percent),
                "memory_percent": float(memory.percent),
                "memory_used_gb": float(memory.used / (1024**3)),
                "memory_available_gb": float(memory.available / (1024**3)),
                "disk_percent": float(disk.percent),
                "disk_used_gb": float(disk.used / (1024**3)),
                "disk_free_gb": float(disk.free / (1024**3))
            }
        )
        
    except ImportError:
        return False
    except Exception:
        return False


class MetricsTimer:
    """指标计时器上下文管理器"""
    
    def __init__(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time = None
        self.duration_ms = 0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.time() - self.start_time) * 1000
        
        if metrics_enabled():
            client = get_metrics_client()
            if client and client.is_connected():
                client.write_point(
                    measurement=self.metric_name,
                    tags=self.tags,
                    fields={
                        "duration_ms": self.duration_ms,
                        "success": 1 if exc_type is None else 0
                    }
                )
        
        return False
