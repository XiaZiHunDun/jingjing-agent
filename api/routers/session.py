"""
会话管理 API 路由

提供对话历史的管理接口。
"""

import os
import sys
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.schemas import (
    SessionInfo,
    SessionListResponse,
    SessionDetailResponse,
    SessionDeleteResponse,
    MessageInfo
)
from api.auth import verify_api_key
from src.db.chat_history import (
    get_all_sessions,
    load_session,
    delete_session,
    get_session_count
)

router = APIRouter(prefix="/api/sessions", tags=["会话管理"])


@router.get(
    "",
    response_model=SessionListResponse,
    summary="获取会话列表",
    description="返回所有对话会话，按更新时间倒序排列",
    responses={
        401: {"description": "缺少 API Key"},
        403: {"description": "无效的 API Key"}
    }
)
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    api_key: Optional[str] = Depends(verify_api_key)
) -> SessionListResponse:
    """
    获取会话列表
    
    - **limit**: 返回数量限制，默认 20，最大 100
    """
    try:
        sessions_data = get_all_sessions(limit=limit)
        sessions = [
            SessionInfo(
                session_id=s["session_id"],
                title=s["title"],
                updated_at=s["updated_at"],
                msg_count=s["msg_count"]
            )
            for s in sessions_data
        ]
        
        total = get_session_count()
        
        return SessionListResponse(
            sessions=sessions,
            total=total
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话列表失败: {str(e)}"
        )


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="获取会话详情",
    description="返回指定会话的所有消息",
    responses={
        401: {"description": "缺少 API Key"},
        403: {"description": "无效的 API Key"},
        404: {"description": "会话不存在"}
    }
)
async def get_session(
    session_id: str,
    api_key: Optional[str] = Depends(verify_api_key)
) -> SessionDetailResponse:
    """
    获取会话详情
    
    - **session_id**: 会话 ID
    """
    try:
        messages_data = load_session(session_id)
        
        if not messages_data:
            raise HTTPException(
                status_code=404,
                detail=f"会话不存在: {session_id}"
            )
        
        messages = [
            MessageInfo(
                role=m["role"],
                content=m["content"],
                thinking_steps=m.get("thinking_steps")
            )
            for m in messages_data
        ]
        
        return SessionDetailResponse(
            session_id=session_id,
            messages=messages,
            msg_count=len(messages)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话详情失败: {str(e)}"
        )


@router.delete(
    "/{session_id}",
    response_model=SessionDeleteResponse,
    summary="删除会话",
    description="删除指定的对话会话及其所有消息",
    responses={
        401: {"description": "缺少 API Key"},
        403: {"description": "无效的 API Key"}
    }
)
async def remove_session(
    session_id: str,
    api_key: Optional[str] = Depends(verify_api_key)
) -> SessionDeleteResponse:
    """
    删除会话
    
    - **session_id**: 会话 ID
    """
    try:
        messages = load_session(session_id)
        if not messages:
            return SessionDeleteResponse(
                success=False,
                message=f"会话不存在: {session_id}"
            )
        
        delete_session(session_id)
        
        return SessionDeleteResponse(
            success=True,
            message=f"成功删除会话: {session_id}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除会话失败: {str(e)}"
        )
