#!/usr/bin/env python3
"""
Kimi API 连接测试脚本
验证环境配置是否正确，API 是否可用
"""

import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def test_env_config():
    """测试环境变量配置"""
    console.print("\n[bold blue]1. 检查环境变量配置[/bold blue]")
    
    # 加载 .env 文件
    load_dotenv()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("配置项", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("值", style="yellow")
    
    # 检查必要的环境变量
    configs = {
        "KIMI_API_KEY": os.getenv("KIMI_API_KEY"),
        "KIMI_BASE_URL": os.getenv("KIMI_BASE_URL"),
        "HTTP_PROXY": os.getenv("HTTP_PROXY"),
        "HTTPS_PROXY": os.getenv("HTTPS_PROXY"),
    }
    
    all_ok = True
    for key, value in configs.items():
        if value:
            # 隐藏 API Key 的中间部分
            if "KEY" in key and len(value) > 10:
                display_value = value[:8] + "..." + value[-4:]
            else:
                display_value = value
            table.add_row(key, "✓ 已配置", display_value)
        else:
            table.add_row(key, "✗ 未配置", "-")
            if key in ["KIMI_API_KEY", "KIMI_BASE_URL"]:
                all_ok = False
    
    console.print(table)
    return all_ok


def test_network():
    """测试网络连通性"""
    console.print("\n[bold blue]2. 测试网络连通性[/bold blue]")
    
    import httpx
    
    load_dotenv()
    
    proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    base_url = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    
    # 移除 /v1 后缀来测试根 URL
    test_url = base_url.replace("/v1", "")
    
    try:
        proxy_mounts = {
            "http://": httpx.HTTPTransport(proxy=proxy),
            "https://": httpx.HTTPTransport(proxy=proxy),
        } if proxy else None
        with httpx.Client(mounts=proxy_mounts, timeout=10) as client:
            response = client.get(test_url)
            console.print(f"  访问 {test_url}: [green]HTTP {response.status_code}[/green]")
            return True
    except Exception as e:
        console.print(f"  访问 {test_url}: [red]失败 - {e}[/red]")
        return False


def test_kimi_api():
    """测试 Kimi API 调用"""
    console.print("\n[bold blue]3. 测试 Kimi API 调用[/bold blue]")
    
    load_dotenv()
    
    api_key = os.getenv("KIMI_API_KEY")
    base_url = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    
    if not api_key:
        console.print("  [red]✗ KIMI_API_KEY 未配置[/red]")
        return False
    
    try:
        from langchain_openai import ChatOpenAI
        
        # 配置代理
        proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        if proxy:
            os.environ["HTTP_PROXY"] = proxy
            os.environ["HTTPS_PROXY"] = proxy
        
        llm = ChatOpenAI(
            model="moonshot-v1-8k",
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.7,
        )
        
        console.print("  发送测试消息: [cyan]'你好，请用一句话介绍自己'[/cyan]")
        response = llm.invoke("你好，请用一句话介绍自己")
        
        console.print(Panel(
            response.content,
            title="[green]Kimi 回复[/green]",
            border_style="green"
        ))
        
        return True
        
    except Exception as e:
        console.print(f"  [red]✗ API 调用失败: {e}[/red]")
        return False


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold]Kimi API 连接测试[/bold]\n验证开发环境配置是否正确",
        border_style="blue"
    ))
    
    results = []
    
    # 测试环境变量
    results.append(("环境变量配置", test_env_config()))
    
    # 测试网络连通性
    results.append(("网络连通性", test_network()))
    
    # 测试 API 调用
    results.append(("Kimi API 调用", test_kimi_api()))
    
    # 汇总结果
    console.print("\n" + "=" * 50)
    console.print("[bold]测试结果汇总[/bold]")
    
    all_passed = True
    for name, passed in results:
        status = "[green]✓ 通过[/green]" if passed else "[red]✗ 失败[/red]"
        console.print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        console.print("\n[bold green]🎉 所有测试通过！开发环境配置正确。[/bold green]")
    else:
        console.print("\n[bold red]⚠️ 部分测试失败，请检查配置。[/bold red]")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
