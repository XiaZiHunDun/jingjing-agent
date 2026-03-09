"""
聊天 API 路由

提供与晶晶助手对话的接口。
"""

import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.schemas import (
    ChatRequest,
    ChatResponse,
    ToolCall,
    ToolListResponse,
    ToolInfo,
    ErrorResponse
)
from api.auth import verify_api_key

router = APIRouter(prefix="/api", tags=["聊天"])

_agent_instance = None
_agent_tools = None


def get_agent():
    """获取或创建 Agent 实例"""
    global _agent_instance, _agent_tools
    
    if _agent_instance is None:
        from src.agent.jingjing import create_jingjing_agent
        _agent_instance = create_jingjing_agent()
        _agent_tools = _agent_instance.tools
    
    return _agent_instance


def refresh_agent():
    """刷新 Agent 实例（知识库更新后调用）"""
    global _agent_instance, _agent_tools
    _agent_instance = None
    _agent_tools = None


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="发送消息",
    description="向晶晶助手发送消息并获取回复（需要认证）",
    responses={
        200: {"description": "成功获取回复"},
        401: {"description": "缺少 API Key"},
        403: {"description": "无效的 API Key"},
        500: {"description": "服务器错误", "model": ErrorResponse}
    }
)
async def chat(
    request: ChatRequest,
    api_key: Optional[str] = Depends(verify_api_key)
) -> ChatResponse:
    """
    与晶晶助手对话
    
    - **message**: 用户消息内容
    - **session_id**: 会话 ID，用于保持上下文（可选，默认 "default"）
    """
    try:
        agent = get_agent()
        result = agent.chat(request.message, request.session_id)
        
        thinking_steps = []
        for step in result.get("thinking_steps", []):
            thinking_steps.append(ToolCall(
                name=step.get("name", ""),
                args=step.get("args", {}),
                result=step.get("result")
            ))
        
        return ChatResponse(
            answer=result["answer"],
            session_id=request.session_id,
            thinking_steps=thinking_steps,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理消息失败: {str(e)}"
        )


@router.get(
    "/tools",
    response_model=ToolListResponse,
    summary="获取可用工具列表",
    description="返回当前可用的所有工具及其描述（需要认证）",
    responses={
        401: {"description": "缺少 API Key"},
        403: {"description": "无效的 API Key"}
    }
)
async def list_tools(
    api_key: Optional[str] = Depends(verify_api_key)
) -> ToolListResponse:
    """获取晶晶助手可用的工具列表"""
    try:
        agent = get_agent()
        tools = []
        
        for tool in agent.tools:
            tools.append(ToolInfo(
                name=tool.name,
                description=tool.description or ""
            ))
        
        return ToolListResponse(
            tools=tools,
            total=len(tools)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取工具列表失败: {str(e)}"
        )
