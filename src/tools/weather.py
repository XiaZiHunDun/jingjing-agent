"""
天气查询工具

使用 Open-Meteo 免费 API 查询天气信息（无需 API Key）。
当 API 不可用时，提示 LLM 根据自身知识提供参考信息。
"""

import os
from datetime import datetime
import httpx
from langchain_core.tools import tool


def _get_fallback_hint(city: str) -> str:
    """当 API 不可用时，返回提示让 LLM 根据自身知识回答"""
    month = datetime.now().month
    if month in [12, 1, 2]:
        season = "冬季"
    elif month in [3, 4, 5]:
        season = "春季"
    elif month in [6, 7, 8]:
        season = "夏季"
    else:
        season = "秋季"
    
    return f"""[天气API暂时不可用]
请根据你的知识，提供 {city} 在 {season}（{month}月）的典型天气情况作为参考。
说明这是基于历史气候数据的一般性描述，而非实时天气。
包括：典型温度范围、常见天气状况、穿衣建议等。"""


CITY_COORDS = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "杭州": (30.2741, 120.1551),
    "成都": (30.5728, 104.0668),
    "武汉": (30.5928, 114.3055),
    "西安": (34.3416, 108.9398),
    "南京": (32.0603, 118.7969),
    "重庆": (29.4316, 106.9123),
    "天津": (39.3434, 117.3616),
    "苏州": (31.2990, 120.5853),
    "郑州": (34.7466, 113.6254),
    "长沙": (28.2282, 112.9388),
    "青岛": (36.0671, 120.3826),
    "东京": (35.6762, 139.6503),
    "tokyo": (35.6762, 139.6503),
    "纽约": (40.7128, -74.0060),
    "new york": (40.7128, -74.0060),
    "伦敦": (51.5074, -0.1278),
    "london": (51.5074, -0.1278),
}

WEATHER_CODE_MAP = {
    0: ("晴朗", "☀️"),
    1: ("大部晴朗", "🌤️"),
    2: ("多云", "⛅"),
    3: ("阴天", "☁️"),
    45: ("有雾", "🌫️"),
    48: ("雾凇", "🌫️"),
    51: ("小毛毛雨", "🌧️"),
    53: ("毛毛雨", "🌧️"),
    55: ("大毛毛雨", "🌧️"),
    61: ("小雨", "🌧️"),
    63: ("中雨", "🌧️"),
    65: ("大雨", "🌧️"),
    71: ("小雪", "🌨️"),
    73: ("中雪", "🌨️"),
    75: ("大雪", "🌨️"),
    80: ("阵雨", "🌦️"),
    81: ("中阵雨", "🌦️"),
    82: ("大阵雨", "🌦️"),
    95: ("雷暴", "⛈️"),
    96: ("雷暴伴小冰雹", "⛈️"),
    99: ("雷暴伴大冰雹", "⛈️"),
}


def _get_http_client():
    """获取 HTTP 客户端，自动配置代理"""
    proxy = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
    if proxy:
        return httpx.Client(timeout=30, follow_redirects=True, proxy=proxy)
    return httpx.Client(timeout=30, follow_redirects=True)


def _get_weather_desc(code: int) -> tuple:
    """根据天气代码获取描述和图标"""
    return WEATHER_CODE_MAP.get(code, ("未知", "🌡️"))


@tool
def get_weather(city: str) -> str:
    """
    查询指定城市的天气信息。
    
    Args:
        city: 城市名称，如 "北京"、"上海"、"深圳"、"东京"
        
    Returns:
        天气信息字符串
    """
    city_lower = city.lower().strip()
    coords = CITY_COORDS.get(city) or CITY_COORDS.get(city_lower)
    
    if not coords:
        return _get_fallback_hint(city)
    
    lat, lon = coords
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
    
    try:
        with _get_http_client() as client:
            response = client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                current = data.get("current", {})
                temp = current.get("temperature_2m", "N/A")
                humidity = current.get("relative_humidity_2m", "N/A")
                wind = current.get("wind_speed_10m", "N/A")
                weather_code = current.get("weather_code", 0)
                
                weather_desc, weather_icon = _get_weather_desc(weather_code)
                
                return f"""{weather_icon} {city} 当前天气:
天气: {weather_desc}
温度: {temp}°C
湿度: {humidity}%
风速: {wind} km/h"""
            else:
                return _get_fallback_hint(city)
                
    except httpx.TimeoutException:
        return _get_fallback_hint(city)
    except Exception as e:
        return _get_fallback_hint(city)


@tool
def get_weather_detail(city: str) -> str:
    """
    获取指定城市的详细天气预报（未来3天）。
    
    Args:
        city: 城市名称
        
    Returns:
        详细天气预报信息
    """
    city_lower = city.lower().strip()
    coords = CITY_COORDS.get(city) or CITY_COORDS.get(city_lower)
    
    if not coords:
        return _get_fallback_hint(city)
    
    lat, lon = coords
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=3"
    
    try:
        with _get_http_client() as client:
            response = client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                daily = data.get("daily", {})
                dates = daily.get("time", [])
                weather_codes = daily.get("weather_code", [])
                temp_max = daily.get("temperature_2m_max", [])
                temp_min = daily.get("temperature_2m_min", [])
                
                result = f"📅 {city} 未来3天天气预报:\n"
                for i in range(min(3, len(dates))):
                    weather_desc, weather_icon = _get_weather_desc(weather_codes[i] if i < len(weather_codes) else 0)
                    result += f"\n{dates[i]}: {weather_icon} {weather_desc}, {temp_min[i]}°C ~ {temp_max[i]}°C"
                
                return result
            else:
                return _get_fallback_hint(city)
                
    except Exception as e:
        return _get_fallback_hint(city)
