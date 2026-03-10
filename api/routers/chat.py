"""
聊天 API 路由

提供与晶晶助手对话的接口。
"""

import os
import sys
import time
import json
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.schemas import (
    ChatRequest,
    ChatResponse,
    ToolCall,
    ToolListResponse,
    ToolInfo,
    ErrorResponse,
    StreamEvent
)
from api.auth import verify_api_key
from api.rate_limit import rate_limiter
from src.utils.logger import chat_logger, RequestStats
from src.metrics import record_chat_metrics, record_tool_call, metrics_enabled

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


async def _stream_chat(agent, message: str, session_id: str) -> AsyncGenerator[str, None]:
    """生成 SSE 流式响应"""
    start_time = time.time()
    thinking_steps = []
    final_answer = ""
    
    try:
        for event in agent.chat_stream(message, session_id):
            event_type = event.get("event")
            
            if event_type == "tool_start":
                if metrics_enabled():
                    record_tool_call(
                        tool_name=event.get("name", "unknown"),
                        session_id=session_id,
                        duration_ms=0,
                        success=True
                    )
            
            if event_type == "tool_end":
                thinking_steps.append({
                    "name": event.get("name"),
                    "args": event.get("args", {}),
                    "result": event.get("result")
                })
            
            if event_type == "done":
                final_answer = event.get("answer", "")
                RequestStats.record_chat(session_id, thinking_steps)
                
                if metrics_enabled():
                    duration_ms = (time.time() - start_time) * 1000
                    record_chat_metrics(
                        session_id=session_id,
                        input_length=len(message),
                        output_length=len(final_answer),
                        total_duration_ms=duration_ms,
                        tool_count=len(thinking_steps),
                        has_error=False
                    )
            
            sse_data = json.dumps(event, ensure_ascii=False)
            yield f"data: {sse_data}\n\n"
            
    except Exception as e:
        chat_logger.error(f"[{session_id}] 流式处理失败: {str(e)}")
        error_event = {"event": "error", "message": str(e)}
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"


@router.post(
    "/chat",
    summary="发送消息",
    description="向晶晶助手发送消息并获取回复（需要认证）。设置 stream=true 启用流式响应。",
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
):
    """
    与晶晶助手对话
    
    - **message**: 用户消息内容
    - **session_id**: 会话 ID，用于保持上下文（可选，默认 "default"）
    - **stream**: 是否启用流式响应（可选，默认 false）
    
    流式响应格式 (SSE):
    ```
    data: {"event": "tool_start", "name": "calculator", "args": {...}}
    data: {"event": "tool_end", "name": "calculator", "result": "..."}
    data: {"event": "token", "content": "这是"}
    data: {"event": "token", "content": "回答"}
    data: {"event": "done", "answer": "完整回答", "thinking_steps": [...]}
    ```
    """
    chat_logger.info(f"[{request.session_id}] 收到消息: {request.message[:50]}... (stream={request.stream})")
    
    agent = get_agent()
    
    if request.stream:
        return StreamingResponse(
            _stream_chat(agent, request.message, request.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    start_time = time.time()
    
    try:
        result = agent.chat(request.message, request.session_id)
        
        thinking_steps = []
        raw_steps = result.get("thinking_steps", [])
        for step in raw_steps:
            thinking_steps.append(ToolCall(
                name=step.get("name", ""),
                args=step.get("args", {}),
                result=step.get("result")
            ))
            
            if metrics_enabled():
                record_tool_call(
                    tool_name=step.get("name", "unknown"),
                    session_id=request.session_id,
                    duration_ms=0,
                    success=True
                )
        
        RequestStats.record_chat(request.session_id, raw_steps)
        
        tool_names = [s.get("name", "") for s in raw_steps]
        chat_logger.info(f"[{request.session_id}] 回复完成, 工具调用: {tool_names or '无'}")
        
        answer = result["answer"]
        
        if metrics_enabled():
            duration_ms = (time.time() - start_time) * 1000
            record_chat_metrics(
                session_id=request.session_id,
                input_length=len(request.message),
                output_length=len(answer),
                total_duration_ms=duration_ms,
                tool_count=len(raw_steps),
                has_error=False
            )
        
        return ChatResponse(
            answer=answer,
            session_id=request.session_id,
            thinking_steps=thinking_steps,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        chat_logger.error(f"[{request.session_id}] 处理失败: {str(e)}")
        
        if metrics_enabled():
            duration_ms = (time.time() - start_time) * 1000
            record_chat_metrics(
                session_id=request.session_id,
                input_length=len(request.message),
                output_length=0,
                total_duration_ms=duration_ms,
                tool_count=0,
                has_error=True
            )
        
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
