"""
日志模块

提供统一的日志配置和记录功能。
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler

from src.utils.config import Config


LOG_DIR = Config.PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> logging.Logger:
    """
    创建并配置 logger
    
    Args:
        name: logger 名称
        level: 日志级别
        log_file: 日志文件名（可选）
        max_bytes: 单个日志文件最大大小（默认 10MB）
        backup_count: 保留的日志文件数量
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        file_path = LOG_DIR / log_file
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


app_logger = setup_logger("jingjing", log_file="app.log")
api_logger = setup_logger("jingjing.api", log_file="api.log")
chat_logger = setup_logger("jingjing.chat", log_file="chat.log")


class RequestStats:
    """请求统计管理器"""
    
    _stats_file = LOG_DIR / "stats.json"
    _stats: Dict[str, Any] = {}
    
    @classmethod
    def _load_stats(cls) -> Dict[str, Any]:
        """加载统计数据"""
        if cls._stats_file.exists():
            try:
                with open(cls._stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return cls._get_default_stats()
    
    @classmethod
    def _get_default_stats(cls) -> Dict[str, Any]:
        """获取默认统计结构"""
        return {
            "start_time": datetime.now().isoformat(),
            "total_requests": 0,
            "total_chats": 0,
            "total_errors": 0,
            "endpoints": {},
            "tools_usage": {},
            "avg_response_time_ms": 0,
            "response_times": []
        }
    
    @classmethod
    def _save_stats(cls):
        """保存统计数据"""
        try:
            stats_copy = cls._stats.copy()
            if "response_times" in stats_copy:
                stats_copy["response_times"] = stats_copy["response_times"][-100:]
            
            with open(cls._stats_file, "w", encoding="utf-8") as f:
                json.dump(stats_copy, f, ensure_ascii=False, indent=2)
        except Exception as e:
            app_logger.error(f"保存统计数据失败: {e}")
    
    @classmethod
    def init(cls):
        """初始化统计"""
        cls._stats = cls._load_stats()
    
    @classmethod
    def record_request(cls, endpoint: str, method: str, status_code: int, duration_ms: float):
        """记录请求"""
        if not cls._stats:
            cls.init()
        
        cls._stats["total_requests"] += 1
        
        endpoint_key = f"{method} {endpoint}"
        if endpoint_key not in cls._stats["endpoints"]:
            cls._stats["endpoints"][endpoint_key] = {
                "count": 0,
                "errors": 0,
                "avg_ms": 0
            }
        
        ep = cls._stats["endpoints"][endpoint_key]
        ep["count"] += 1
        ep["avg_ms"] = (ep["avg_ms"] * (ep["count"] - 1) + duration_ms) / ep["count"]
        
        if status_code >= 400:
            ep["errors"] += 1
            cls._stats["total_errors"] += 1
        
        cls._stats["response_times"].append(duration_ms)
        if len(cls._stats["response_times"]) > 100:
            cls._stats["response_times"] = cls._stats["response_times"][-100:]
        
        if cls._stats["response_times"]:
            cls._stats["avg_response_time_ms"] = sum(cls._stats["response_times"]) / len(cls._stats["response_times"])
        
        if cls._stats["total_requests"] % 10 == 0:
            cls._save_stats()
    
    @classmethod
    def record_chat(cls, session_id: str, tool_calls: list):
        """记录聊天"""
        if not cls._stats:
            cls.init()
        
        cls._stats["total_chats"] += 1
        
        for tool in tool_calls:
            tool_name = tool.get("name", "unknown")
            if tool_name not in cls._stats["tools_usage"]:
                cls._stats["tools_usage"][tool_name] = 0
            cls._stats["tools_usage"][tool_name] += 1
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """获取统计数据"""
        if not cls._stats:
            cls.init()
        
        stats = cls._stats.copy()
        stats.pop("response_times", None)
        stats["uptime_seconds"] = (
            datetime.now() - datetime.fromisoformat(stats["start_time"])
        ).total_seconds()
        
        return stats
    
    @classmethod
    def reset(cls):
        """重置统计"""
        cls._stats = cls._get_default_stats()
        cls._save_stats()


RequestStats.init()
