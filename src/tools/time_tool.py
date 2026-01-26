"""
时间工具

提供当前时间查询功能。
"""

import datetime
from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """
    获取当前日期和时间（北京时间）。
    
    返回格式：2026年01月26日 14:30:45 (星期一，北京时间)
    
    Returns:
        当前时间的格式化字符串
    """
    # 使用北京时区 (UTC+8)
    beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(beijing_tz)
    
    weekdays = ['一', '二', '三', '四', '五', '六', '日']
    weekday = weekdays[now.weekday()]
    
    return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')} (星期{weekday}，北京时间)"


@tool
def get_date() -> str:
    """
    获取当前日期。
    
    Returns:
        当前日期字符串
    """
    beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(beijing_tz)
    
    weekdays = ['一', '二', '三', '四', '五', '六', '日']
    weekday = weekdays[now.weekday()]
    
    return f"今天是 {now.strftime('%Y年%m月%d日')}，星期{weekday}"
