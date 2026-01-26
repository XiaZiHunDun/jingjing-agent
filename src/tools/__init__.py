"""
工具模块

提供 Agent 可调用的各种工具。
"""

from src.tools.calculator import calculator
from src.tools.time_tool import get_current_time, get_date
from src.tools.weather import get_weather, get_weather_detail
from src.tools.webpage import fetch_webpage_summary
from src.tools.translate import translate, detect_language
from src.tools.search import web_search, web_search_news, web_search_with_summary


def get_basic_tools():
    """获取基础工具列表（不包含 RAG）"""
    return [
        calculator,
        get_current_time,
        get_weather,
        fetch_webpage_summary,
        translate,
        web_search,  # 新增：网络搜索
    ]


def get_all_tool_names():
    """获取所有工具名称"""
    return [
        "calculator",
        "get_current_time",
        "get_weather",
        "fetch_webpage_summary",
        "translate",
        "web_search",
        "search_knowledge_base",
    ]


__all__ = [
    # 基础工具
    "calculator",
    "get_current_time",
    "get_date",
    "get_weather",
    "get_weather_detail",
    "fetch_webpage_summary",
    "translate",
    "detect_language",
    # 搜索工具
    "web_search",
    "web_search_news",
    "web_search_with_summary",
    # 辅助函数
    "get_basic_tools",
    "get_all_tool_names",
]
