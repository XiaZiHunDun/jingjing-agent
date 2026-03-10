"""
Ollama 本地模型配置模块

封装 Ollama API 的调用配置，提供本地 LLM 实例。
"""

import os
from functools import lru_cache
from typing import Optional

from langchain_ollama import ChatOllama

from src.utils.logger import app_logger


def get_ollama_base_url() -> str:
    """获取 Ollama 服务地址"""
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def get_ollama_model() -> str:
    """获取 Ollama 模型名称"""
    return os.getenv("OLLAMA_MODEL", "modelscope.cn/Qwen/Qwen3-8B-GGUF:latest")


def get_ollama_llm(temperature: float = 0.7) -> ChatOllama:
    """
    获取 Ollama LLM 实例
    
    Args:
        temperature: 生成温度
        
    Returns:
        ChatOllama 实例
    """
    return ChatOllama(
        model=get_ollama_model(),
        base_url=get_ollama_base_url(),
        temperature=temperature,
    )


def get_ollama_agent_llm() -> ChatOllama:
    """获取 Agent 专用的 Ollama LLM 实例"""
    return ChatOllama(
        model=get_ollama_model(),
        base_url=get_ollama_base_url(),
        temperature=0,
    )


def get_ollama_chat_llm(temperature: float = 0.7) -> ChatOllama:
    """获取对话专用的 Ollama LLM 实例"""
    return ChatOllama(
        model=get_ollama_model(),
        base_url=get_ollama_base_url(),
        temperature=temperature,
    )


def _get_no_proxy_client(timeout: int = 5):
    """获取不使用代理的 httpx 客户端"""
    import httpx
    # 使用自定义 transport 来绕过环境变量中的代理配置
    transport = httpx.HTTPTransport()
    return httpx.Client(timeout=timeout, transport=transport)


def check_ollama_available() -> bool:
    """检查 Ollama 服务是否可用"""
    try:
        base_url = get_ollama_base_url()
        with _get_no_proxy_client() as client:
            response = client.get(f"{base_url}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


def list_ollama_models() -> list:
    """列出 Ollama 可用的模型"""
    try:
        base_url = get_ollama_base_url()
        with _get_no_proxy_client() as client:
            response = client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        app_logger.error(f"获取 Ollama 模型列表失败: {str(e)}")
    
    return []
