"""
模型管理 API 路由

提供 LLM 模型查询和切换功能。
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import verify_api_key
from src.llm import get_provider_info, set_provider, get_current_provider
from src.llm.ollama import check_ollama_available, list_ollama_models


router = APIRouter(prefix="/api/models", tags=["模型管理"])


class SwitchModelRequest(BaseModel):
    """切换模型请求"""
    provider: str  # "kimi" or "ollama"


class ProviderInfoResponse(BaseModel):
    """提供者信息响应"""
    provider: str
    model: str
    base_url: str
    available_providers: List[str]
    available_models: Optional[List[str]] = None


@router.get("/current", response_model=ProviderInfoResponse)
async def get_current_model():
    """
    获取当前使用的模型信息
    
    返回当前 LLM 提供者和模型配置（无需认证）。
    """
    return get_provider_info()


@router.get("/providers")
async def list_providers():
    """
    列出所有可用的 LLM 提供者
    
    返回已配置的提供者及其状态。
    """
    providers = [
        {
            "name": "kimi",
            "display_name": "Kimi API",
            "description": "月之暗面 Kimi 云端大模型",
            "available": True,
            "is_current": get_current_provider().value == "kimi"
        },
        {
            "name": "ollama",
            "display_name": "Ollama (本地)",
            "description": "本地部署的 Ollama 模型",
            "available": check_ollama_available(),
            "is_current": get_current_provider().value == "ollama"
        }
    ]
    
    return {"providers": providers}


@router.get("/ollama/models")
async def get_ollama_models():
    """
    获取 Ollama 可用的模型列表
    
    返回本地 Ollama 已下载的模型。
    """
    if not check_ollama_available():
        raise HTTPException(status_code=503, detail="Ollama 服务不可用")
    
    models = list_ollama_models()
    return {"models": models}


@router.post("/switch")
async def switch_model(
    request: SwitchModelRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    切换 LLM 提供者
    
    在 Kimi API 和 Ollama 本地模型之间切换。
    切换后立即生效，下次对话将使用新的模型。
    """
    from api.routers.chat import refresh_agent
    
    provider = request.provider.lower()
    
    if provider not in ["kimi", "ollama"]:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的提供者: {provider}，可选: kimi, ollama"
        )
    
    if provider == "ollama" and not check_ollama_available():
        raise HTTPException(status_code=503, detail="Ollama 服务不可用，无法切换")
    
    success = set_provider(provider)
    
    if not success:
        raise HTTPException(status_code=500, detail="切换模型失败")
    
    # 重置 Agent 缓存，下次请求时会用新 provider 创建
    refresh_agent()
    
    return {
        "message": f"已切换到 {provider}",
        "current": get_provider_info()
    }


@router.get("/status")
async def get_model_status():
    """
    获取模型服务状态
    
    返回各提供者的可用状态和当前配置。
    """
    current = get_current_provider().value
    ollama_available = check_ollama_available()
    
    status = {
        "current_provider": current,
        "kimi": {
            "available": True,
            "is_current": current == "kimi"
        },
        "ollama": {
            "available": ollama_available,
            "is_current": current == "ollama"
        }
    }
    
    if ollama_available:
        status["ollama"]["models"] = list_ollama_models()
    
    return status
