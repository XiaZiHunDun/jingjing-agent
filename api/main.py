#!/usr/bin/env python3
"""
===========================================
晶晶助手 - FastAPI 后端
===========================================

提供 RESTful API 接口，供外部系统调用。

启动方式：
    cd /home/ailearn/projects/agent-learn-2
    conda activate agent-learn
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

API 文档：
    - Swagger UI: http://<服务器IP>:8000/docs
    - ReDoc: http://<服务器IP>:8000/redoc
"""

import os
import sys
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from api import __version__
from api.schemas import HealthStatus, ErrorResponse
from api.routers import chat_router, knowledge_router, session_router
from api.auth import is_auth_enabled
from api.middleware import LoggingMiddleware, RateLimitMiddleware
from api.rate_limit import rate_limiter, DEFAULT_CONFIG as RATE_LIMIT_CONFIG
from src.utils.logger import app_logger, RequestStats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    app_logger.info("=" * 50)
    app_logger.info("晶晶助手 API 服务启动中...")
    app_logger.info(f"版本: {__version__}")
    app_logger.info("=" * 50)
    
    from src.db.chat_history import init_database
    init_database()
    app_logger.info("[✓] 数据库初始化完成")
    
    from src.memory.vector_store import get_vector_store
    vs = get_vector_store()
    if vs:
        app_logger.info("[✓] 向量数据库加载完成")
    else:
        app_logger.warning("[!] 向量数据库为空，请上传文档")
    
    if is_auth_enabled():
        app_logger.info("[✓] API 认证已启用")
    else:
        app_logger.warning("[!] API 认证未启用（开发模式）")
    
    app_logger.info("[✓] 日志和监控已启用")
    
    if RATE_LIMIT_CONFIG.enabled:
        app_logger.info(f"[✓] 速率限制已启用 ({RATE_LIMIT_CONFIG.requests_per_minute}/分钟)")
    else:
        app_logger.warning("[!] 速率限制未启用")
    
    app_logger.info("=" * 50)
    app_logger.info("API 服务已就绪")
    app_logger.info("  - Swagger UI: http://0.0.0.0:8000/docs")
    app_logger.info("  - ReDoc: http://0.0.0.0:8000/redoc")
    app_logger.info("  - 统计接口: http://0.0.0.0:8000/api/stats")
    app_logger.info("=" * 50)
    
    yield
    
    app_logger.info("API 服务关闭")


app = FastAPI(
    title="晶晶助手 API",
    description="""
## 晶晶助手 - 智能对话 API

这是晶晶助手的后端 API 服务，提供以下功能：

### 功能特性

- **智能对话**: 与 AI 助手进行多轮对话
- **工具调用**: 支持计算器、天气查询、翻译等工具
- **知识库检索**: 基于 RAG 的文档问答
- **知识库管理**: 上传、删除文档

### 认证方式

大部分接口需要 API Key 认证，支持两种传递方式：

1. **Header 方式**（推荐）:
   ```
   X-API-Key: your-api-key
   ```

2. **Query 参数方式**:
   ```
   /api/chat?api_key=your-api-key
   ```

**注意**: `/health` 和 `/` 接口为公开接口，无需认证。

如果服务端未配置 `API_KEYS` 环境变量，则认证功能自动禁用（开发模式）。
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


@app.get(
    "/",
    summary="API 根路径",
    description="返回 API 基本信息"
)
async def root():
    """API 欢迎信息"""
    return {
        "name": "晶晶助手 API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health"
    }


@app.get(
    "/health",
    response_model=HealthStatus,
    summary="健康检查",
    description="检查 API 服务及各组件的健康状态",
    tags=["系统"]
)
async def health_check() -> HealthStatus:
    """
    健康检查接口
    
    返回服务状态和各组件的连接情况：
    - **llm**: 大语言模型连接状态
    - **vector_store**: 向量数据库状态
    - **database**: SQLite 数据库状态
    """
    components = {}
    overall_healthy = True
    
    try:
        from src.llm.kimi import get_llm
        llm = get_llm()
        if llm:
            components["llm"] = "connected"
        else:
            components["llm"] = "not_configured"
            overall_healthy = False
    except Exception as e:
        components["llm"] = f"error: {str(e)[:50]}"
        overall_healthy = False
    
    try:
        from src.memory.vector_store import get_vector_store
        vs = get_vector_store()
        if vs:
            components["vector_store"] = "loaded"
        else:
            components["vector_store"] = "empty"
    except Exception as e:
        components["vector_store"] = f"error: {str(e)[:50]}"
    
    try:
        from src.db.chat_history import get_all_sessions
        sessions = get_all_sessions()
        components["database"] = "connected"
    except Exception as e:
        components["database"] = f"error: {str(e)[:50]}"
        overall_healthy = False
    
    components["auth"] = "enabled" if is_auth_enabled() else "disabled"
    
    return HealthStatus(
        status="healthy" if overall_healthy else "unhealthy",
        version=__version__,
        timestamp=datetime.now(),
        components=components
    )


@app.get(
    "/api/stats",
    summary="获取统计数据",
    description="返回 API 调用统计信息",
    tags=["系统"]
)
async def get_stats():
    """
    获取 API 统计数据
    
    返回：
    - **total_requests**: 总请求数
    - **total_chats**: 总对话数
    - **total_errors**: 错误数
    - **avg_response_time_ms**: 平均响应时间
    - **endpoints**: 各接口调用统计
    - **tools_usage**: 工具使用统计
    - **uptime_seconds**: 运行时长
    """
    return RequestStats.get_stats()


@app.post(
    "/api/stats/reset",
    summary="重置统计数据",
    description="清空所有统计数据并重新开始计数",
    tags=["系统"]
)
async def reset_stats():
    """重置统计数据"""
    RequestStats.reset()
    return {"message": "统计数据已重置", "timestamp": datetime.now().isoformat()}


@app.get(
    "/api/rate-limit",
    summary="获取速率限制状态",
    description="返回当前客户端的速率限制使用情况",
    tags=["系统"]
)
async def get_rate_limit_status(request: Request):
    """
    获取当前客户端的速率限制状态
    
    返回：
    - **minute_used/limit**: 每分钟已用/限制
    - **hour_used/limit**: 每小时已用/限制
    - **remaining**: 剩余可用次数
    """
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    stats = rate_limiter.get_client_stats(request, api_key)
    
    return {
        "enabled": RATE_LIMIT_CONFIG.enabled,
        "config": {
            "requests_per_minute": RATE_LIMIT_CONFIG.requests_per_minute,
            "requests_per_hour": RATE_LIMIT_CONFIG.requests_per_hour,
            "burst_limit": RATE_LIMIT_CONFIG.burst_limit
        },
        "current_usage": stats
    }


app.include_router(chat_router)
app.include_router(knowledge_router)
app.include_router(session_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
