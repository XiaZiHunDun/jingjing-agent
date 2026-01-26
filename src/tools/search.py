"""
网络搜索工具

使用 DuckDuckGo 搜索引擎获取实时网络信息。
"""

import os
from typing import Optional
from langchain_core.tools import tool

from src.llm.kimi import get_llm


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    在互联网上搜索信息。用于获取实时新闻、最新资讯、人物信息、事件等。
    
    Args:
        query: 搜索关键词，如 "今天的新闻"、"Python 最新版本"
        max_results: 返回结果数量，默认 5 条
        
    Returns:
        搜索结果摘要
    """
    try:
        from ddgs import DDGS
        
        results = []
        with DDGS(timeout=30) as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "href": r.get("href", "")
                })
        
        if not results:
            return f"未找到关于 '{query}' 的搜索结果"
        
        # 格式化结果
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"{i}. **{r['title']}**\n   {r['body']}\n   链接: {r['href']}")
        
        return f"搜索结果 ({len(results)} 条):\n\n" + "\n\n".join(formatted)
        
    except Exception as e:
        return f"搜索失败: {str(e)}"


@tool
def web_search_news(query: str, max_results: int = 5) -> str:
    """
    搜索最新新闻。用于获取时事新闻、热点事件等。
    
    Args:
        query: 新闻关键词
        max_results: 返回结果数量
        
    Returns:
        新闻搜索结果
    """
    try:
        from ddgs import DDGS
        
        results = []
        with DDGS(timeout=30) as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "date": r.get("date", ""),
                    "source": r.get("source", ""),
                    "url": r.get("url", "")
                })
        
        if not results:
            return f"未找到关于 '{query}' 的新闻"
        
        # 格式化结果
        formatted = []
        for i, r in enumerate(results, 1):
            date_str = f" ({r['date']})" if r['date'] else ""
            source_str = f" - {r['source']}" if r['source'] else ""
            formatted.append(f"{i}. **{r['title']}**{source_str}{date_str}\n   {r['body']}")
        
        return f"新闻搜索结果 ({len(results)} 条):\n\n" + "\n\n".join(formatted)
        
    except Exception as e:
        return f"新闻搜索失败: {str(e)}"


@tool  
def web_search_with_summary(query: str) -> str:
    """
    搜索互联网并使用 AI 总结结果。适合需要综合答案的问题。
    
    Args:
        query: 搜索问题，如 "2024年最流行的编程语言是什么"
        
    Returns:
        AI 总结的搜索结果
    """
    try:
        from ddgs import DDGS
        
        # 搜索
        results = []
        with DDGS(timeout=30) as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(f"标题: {r.get('title', '')}\n内容: {r.get('body', '')}")
        
        if not results:
            return f"未找到关于 '{query}' 的搜索结果"
        
        # 使用 LLM 总结
        context = "\n\n---\n\n".join(results)
        llm = get_llm()
        
        summary_prompt = f"""根据以下搜索结果，回答用户的问题。

搜索结果:
{context}

用户问题: {query}

请给出简洁准确的回答，如果搜索结果中没有相关信息，请说明。"""
        
        response = llm.invoke(summary_prompt)
        return f"搜索总结:\n\n{response.content}"
        
    except Exception as e:
        return f"搜索总结失败: {str(e)}"
