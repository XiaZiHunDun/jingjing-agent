"""
LLM 工厂模块

提供统一的 LLM 实例管理，支持在 Kimi API 和 Ollama 本地模型之间切换。
"""

import os
from typing import Optional, Literal, Union
from enum import Enum

from langchain_core.language_models import BaseChatModel

from src.utils.logger import app_logger


class LLMProvider(Enum):
    """LLM 提供者"""
    KIMI = "kimi"
    OLLAMA = "ollama"


# 全局当前使用的 provider
_current_provider: Optional[LLMProvider] = None


def get_default_provider() -> LLMProvider:
    """获取默认的 LLM 提供者"""
    provider = os.getenv("LLM_PROVIDER", "kimi").lower()
    if provider == "ollama":
        return LLMProvider.OLLAMA
    return LLMProvider.KIMI


def get_current_provider() -> LLMProvider:
    """获取当前使用的 LLM 提供者"""
    global _current_provider
    if _current_provider is None:
        _current_provider = get_default_provider()
    return _current_provider


def set_provider(provider: Union[LLMProvider, str]) -> bool:
    """
    设置当前 LLM 提供者
    
    Args:
        provider: 提供者名称或枚举值
        
    Returns:
        是否设置成功
    """
    global _current_provider
    
    if isinstance(provider, str):
        provider = provider.lower()
        if provider == "kimi":
            _current_provider = LLMProvider.KIMI
        elif provider == "ollama":
            # 检查 Ollama 是否可用
            from src.llm.ollama import check_ollama_available
            if not check_ollama_available():
                app_logger.error("无法切换到 Ollama: 服务不可用")
                return False
            _current_provider = LLMProvider.OLLAMA
        else:
            app_logger.error(f"未知的 LLM 提供者: {provider}")
            return False
    else:
        _current_provider = provider
    
    app_logger.info(f"LLM 提供者已切换为: {_current_provider.value}")
    return True


def get_llm(temperature: float = 0.7) -> BaseChatModel:
    """
    获取 LLM 实例（根据当前 provider）
    
    Args:
        temperature: 生成温度
        
    Returns:
        LLM 实例
    """
    provider = get_current_provider()
    
    if provider == LLMProvider.OLLAMA:
        from src.llm.ollama import get_ollama_llm
        return get_ollama_llm(temperature)
    else:
        from src.llm.kimi import get_llm as get_kimi_llm
        return get_kimi_llm(temperature)


def get_agent_llm() -> BaseChatModel:
    """获取 Agent 专用的 LLM 实例"""
    provider = get_current_provider()
    
    if provider == LLMProvider.OLLAMA:
        from src.llm.ollama import get_ollama_agent_llm
        return get_ollama_agent_llm()
    else:
        from src.llm.kimi import get_agent_llm as get_kimi_agent_llm
        return get_kimi_agent_llm()


def get_chat_llm(temperature: float = 0.7) -> BaseChatModel:
    """获取对话专用的 LLM 实例"""
    provider = get_current_provider()
    
    if provider == LLMProvider.OLLAMA:
        from src.llm.ollama import get_ollama_chat_llm
        return get_ollama_chat_llm(temperature)
    else:
        from src.llm.kimi import get_chat_llm as get_kimi_chat_llm
        return get_kimi_chat_llm(temperature)


def get_provider_info() -> dict:
    """获取当前 LLM 提供者信息"""
    provider = get_current_provider()
    
    info = {
        "provider": provider.value,
        "available_providers": ["kimi", "ollama"]
    }
    
    if provider == LLMProvider.KIMI:
        from src.utils.config import Config
        info["model"] = Config.KIMI_MODEL
        info["base_url"] = Config.KIMI_BASE_URL
    else:
        from src.llm.ollama import get_ollama_model, get_ollama_base_url, list_ollama_models
        info["model"] = get_ollama_model()
        info["base_url"] = get_ollama_base_url()
        info["available_models"] = list_ollama_models()
    
    return info
