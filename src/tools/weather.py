"""
天气查询工具

使用 wttr.in 免费 API 查询天气信息。
"""

import httpx
from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """
    查询指定城市的天气信息。
    
    Args:
        city: 城市名称，如 "北京"、"上海"、"深圳"、"Tokyo"
        
    Returns:
        天气信息字符串
    """
    # 使用 wttr.in 免费天气 API (HTTP 更稳定)
    url = f"http://wttr.in/{city}?format=%l:+%c+%t+%h+%w&lang=zh"
    
    try:
        # 直接请求，不使用代理（wttr.in 可以直连）
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url)
            
            if response.status_code == 200:
                return f"🌤️ 天气查询结果:\n{response.text.strip()}"
            else:
                return f"天气查询失败: HTTP {response.status_code}"
                
    except httpx.TimeoutException:
        return f"天气查询超时，请稍后重试"
    except Exception as e:
        return f"天气查询错误: {str(e)}"


@tool
def get_weather_detail(city: str) -> str:
    """
    获取指定城市的详细天气预报。
    
    Args:
        city: 城市名称
        
    Returns:
        详细天气预报信息
    """
    url = f"http://wttr.in/{city}?format=3&lang=zh"
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url)
            
            if response.status_code == 200:
                return f"🌤️ {response.text.strip()}"
            else:
                return f"天气查询失败: HTTP {response.status_code}"
                
    except Exception as e:
        return f"天气查询错误: {str(e)}"
