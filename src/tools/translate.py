"""
翻译工具

支持多语言翻译。
"""

from langchain_core.tools import tool

from src.llm.kimi import get_llm


@tool
def translate(text: str, target_language: str = "英文") -> str:
    """
    翻译文本到目标语言。
    
    Args:
        text: 要翻译的文本
        target_language: 目标语言，默认为"英文"，也可以是"中文"、"日文"、"法文"等
        
    Returns:
        翻译结果
    """
    try:
        llm = get_llm()
        
        prompt = f"请将以下文本翻译成{target_language}，只返回翻译结果，不要添加解释:\n\n{text}"
        response = llm.invoke(prompt)
        
        return f"🌐 翻译结果 ({target_language}):\n{response.content}"
        
    except Exception as e:
        return f"翻译错误: {str(e)}"


@tool
def detect_language(text: str) -> str:
    """
    检测文本的语言。
    
    Args:
        text: 要检测的文本
        
    Returns:
        检测到的语言
    """
    try:
        llm = get_llm()
        
        prompt = f"请检测以下文本的语言，只返回语言名称（如：中文、英文、日文等）:\n\n{text}"
        response = llm.invoke(prompt)
        
        return f"检测结果: {response.content}"
        
    except Exception as e:
        return f"语言检测错误: {str(e)}"
