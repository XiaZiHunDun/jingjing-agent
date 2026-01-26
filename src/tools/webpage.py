"""
网页摘要工具

获取网页内容并生成摘要。
"""

import os
import re
import httpx
from langchain_core.tools import tool

from src.llm.kimi import get_llm


@tool
def fetch_webpage_summary(url: str) -> str:
    """
    获取网页内容并生成摘要。
    
    Args:
        url: 网页地址，如 "https://example.com"
        
    Returns:
        网页内容的摘要
    """
    try:
        # 配置代理
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; JingjingBot/1.0)"
        }
        
        # 获取网页内容
        with httpx.Client(
            proxy=proxy, 
            timeout=15, 
            follow_redirects=True, 
            headers=headers
        ) as client:
            response = client.get(url)
        
        if response.status_code != 200:
            return f"网页获取失败: HTTP {response.status_code}"
        
        # 提取文本内容
        html = response.text
        
        # 移除 script 和 style 标签
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # 清理空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 截取前 2000 字符
        text = text[:2000] if len(text) > 2000 else text
        
        if not text:
            return "无法提取网页内容"
        
        # 使用 LLM 生成摘要
        llm = get_llm()
        summary_response = llm.invoke(
            f"请用中文简洁地总结以下网页内容（100-200字）:\n\n{text}"
        )
        
        return f"📄 网页摘要:\n{summary_response.content}"
        
    except httpx.TimeoutException:
        return "网页获取超时，请稍后重试"
    except Exception as e:
        return f"网页摘要错误: {str(e)}"
