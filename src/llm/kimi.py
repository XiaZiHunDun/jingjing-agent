"""
Kimi LLM 配置模块

封装 Kimi API 的调用配置，提供统一的 LLM 实例获取方法。
"""

from functools import lru_cache
from langchain_openai import ChatOpenAI

from src.utils.config import Config


@lru_cache(maxsize=1)
def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """
    获取配置好的 Kimi LLM 实例
    
    Args:
        temperature: 生成温度，0 更稳定，1 更随机
        
    Returns:
        ChatOpenAI 实例
    """
    return ChatOpenAI(
        model=Config.KIMI_MODEL,
        openai_api_key=Config.KIMI_API_KEY,
        openai_api_base=Config.KIMI_BASE_URL,
        temperature=temperature,
    )


def get_agent_llm() -> ChatOpenAI:
    """
    获取 Agent 专用的 LLM 实例（temperature=0 更稳定）
    """
    return ChatOpenAI(
        model=Config.KIMI_MODEL,
        openai_api_key=Config.KIMI_API_KEY,
        openai_api_base=Config.KIMI_BASE_URL,
        temperature=0,
    )


def get_chat_llm(temperature: float = 0.7) -> ChatOpenAI:
    """
    获取对话专用的 LLM 实例
    """
    return ChatOpenAI(
        model=Config.KIMI_MODEL,
        openai_api_key=Config.KIMI_API_KEY,
        openai_api_base=Config.KIMI_BASE_URL,
        temperature=temperature,
    )
