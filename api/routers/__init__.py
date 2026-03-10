"""
API 路由模块
"""

from .chat import router as chat_router
from .knowledge import router as knowledge_router
from .session import router as session_router
from .metrics import router as metrics_router

__all__ = ["chat_router", "knowledge_router", "session_router", "metrics_router"]
