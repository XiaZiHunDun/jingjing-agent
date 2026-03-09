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
from api.routers import chat_router, knowledge_router
from api.auth import is_auth_enabled


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("=" * 50)
    print("晶晶助手 API 服务启动中...")
    print(f"版本: {__version__}")
    print("=" * 50)
    
    from src.db.chat_history import init_database
    init_database()
    print("[✓] 数据库初始化完成")
    
    from src.memory.vector_store import get_vector_store
    vs = get_vector_store()
    if vs:
        print("[✓] 向量数据库加载完成")
    else:
        print("[!] 向量数据库为空，请上传文档")
    
    if is_auth_enabled():
        print("[✓] API 认证已启用")
    else:
        print("[!] API 认证未启用（开发模式）")
    
    print("=" * 50)
    print("API 服务已就绪")
    print("  - Swagger UI: http://0.0.0.0:8000/docs")
    print("  - ReDoc: http://0.0.0.0:8000/redoc")
    print("=" * 50)
    
    yield
    
    print("API 服务关闭")


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


app.include_router(chat_router)
app.include_router(knowledge_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
