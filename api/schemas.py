"""
API 数据模型定义

使用 Pydantic 定义请求和响应的数据结构。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================
# 聊天相关模型
# ============================================================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=10000)
    session_id: Optional[str] = Field(default="default", description="会话 ID")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "北京天气怎么样？",
                    "session_id": "user_001"
                }
            ]
        }
    }


class ToolCall(BaseModel):
    """工具调用信息"""
    name: str = Field(..., description="工具名称")
    args: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    result: Optional[str] = Field(default=None, description="工具返回结果")


class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str = Field(..., description="助手回复")
    session_id: str = Field(..., description="会话 ID")
    thinking_steps: List[ToolCall] = Field(default_factory=list, description="思考过程（工具调用）")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "北京今天天气晴朗，气温 15°C。",
                    "session_id": "user_001",
                    "thinking_steps": [
                        {
                            "name": "get_weather",
                            "args": {"city": "北京"},
                            "result": "晴朗, 15°C"
                        }
                    ],
                    "timestamp": "2026-02-27T10:30:00"
                }
            ]
        }
    }


# ============================================================
# 知识库相关模型
# ============================================================

class DocumentInfo(BaseModel):
    """文档信息"""
    source: str = Field(..., description="文档名称/来源")
    chunk_count: int = Field(..., description="分块数量")


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: List[DocumentInfo] = Field(default_factory=list, description="文档列表")
    total: int = Field(..., description="文档总数")


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    source: Optional[str] = Field(default=None, description="文档名称")
    chunk_count: Optional[int] = Field(default=None, description="分块数量")


class DocumentDeleteResponse(BaseModel):
    """文档删除响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")


# ============================================================
# 工具相关模型
# ============================================================

class ToolInfo(BaseModel):
    """工具信息"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")


class ToolListResponse(BaseModel):
    """工具列表响应"""
    tools: List[ToolInfo] = Field(default_factory=list, description="可用工具列表")
    total: int = Field(..., description="工具总数")


# ============================================================
# 健康检查模型
# ============================================================

class HealthStatus(BaseModel):
    """健康状态"""
    status: str = Field(..., description="服务状态: healthy/unhealthy")
    version: str = Field(..., description="API 版本")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    components: Dict[str, str] = Field(default_factory=dict, description="组件状态")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "version": "1.0.0",
                    "timestamp": "2026-02-27T10:30:00",
                    "components": {
                        "llm": "connected",
                        "vector_store": "loaded",
                        "database": "connected"
                    }
                }
            ]
        }
    }


# ============================================================
# 通用响应模型
# ============================================================

class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")
