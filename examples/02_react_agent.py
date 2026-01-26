#!/usr/bin/env python3
"""
===========================================
B1: ReAct Agent 入门
===========================================

本教程介绍如何创建一个能调用工具的 ReAct Agent：
1. ReAct 模式介绍（Reasoning + Acting）
2. 使用 @tool 装饰器定义工具
3. 创建 ReAct Agent
4. 使用 AgentExecutor 执行任务

ReAct 工作流程：
    思考(Thought) → 行动(Action) → 观察(Observation) → 循环...

运行方式:
    cd /home/ailearn/projects/agent-learn-2
    conda activate agent-learn
    python examples/02_react_agent.py
"""

import os
import sys
import math
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# 加载环境变量
load_dotenv()

console = Console()

# 配置代理
proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
if proxy:
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy


def get_llm():
    """获取配置好的 LLM 实例"""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model="moonshot-v1-8k",
        openai_api_key=os.getenv("KIMI_API_KEY"),
        openai_api_base=os.getenv("KIMI_BASE_URL"),
        temperature=0,  # Agent 场景建议用 0，更稳定
    )


def print_section(title: str, description: str = ""):
    """打印章节标题"""
    console.print(f"\n{'='*60}")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    if description:
        console.print(f"[dim]{description}[/dim]")
    console.print('='*60)


# ============================================================
# 第一部分：定义工具
# ============================================================

def create_tools():
    """
    创建 Agent 可以使用的工具集
    
    工具是 Agent 与外部世界交互的方式。
    每个工具都有：
    - name: 工具名称
    - description: 工具描述（LLM 根据这个决定是否使用）
    - 函数实现
    """
    from langchain_core.tools import tool
    
    @tool
    def calculator(expression: str) -> str:
        """
        计算数学表达式。支持加减乘除、幂运算、开方等。
        
        Args:
            expression: 数学表达式，如 "2 + 3 * 4" 或 "sqrt(16)"
        
        Returns:
            计算结果
        """
        try:
            # 安全地评估数学表达式
            # 替换常用函数名
            expr = expression.replace("^", "**")
            expr = expr.replace("sqrt", "math.sqrt")
            expr = expr.replace("sin", "math.sin")
            expr = expr.replace("cos", "math.cos")
            expr = expr.replace("pi", "math.pi")
            
            result = eval(expr, {"__builtins__": {}, "math": math})
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    @tool
    def get_current_time() -> str:
        """
        获取当前日期和时间。
        
        Returns:
            当前的日期时间字符串
        """
        now = datetime.datetime.now()
        return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')} (星期{['一','二','三','四','五','六','日'][now.weekday()]})"
    
    @tool
    def search_knowledge(query: str) -> str:
        """
        搜索知识库获取信息。（模拟）
        
        Args:
            query: 搜索关键词
        
        Returns:
            搜索结果
        """
        # 模拟知识库
        knowledge_base = {
            "python": "Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年发布。特点是简洁易读，广泛用于 Web 开发、数据科学、AI 等领域。",
            "langchain": "LangChain 是一个用于构建 LLM 应用的框架，提供了链、Agent、记忆等组件，简化了 AI 应用开发。",
            "react": "ReAct (Reasoning + Acting) 是一种让 LLM 交替进行推理和行动的方法，能有效解决复杂任务。",
            "agent": "Agent（智能体）是一种能够自主决策和行动的 AI 系统，可以理解目标、规划步骤、调用工具来完成任务。",
        }
        
        query_lower = query.lower()
        for key, value in knowledge_base.items():
            if key in query_lower:
                return f"找到相关信息: {value}"
        
        return f"未找到 '{query}' 的相关信息。请尝试其他关键词。"
    
    @tool
    def string_length(text: str) -> str:
        """
        计算字符串的长度（字符数）。
        
        Args:
            text: 要计算长度的字符串
        
        Returns:
            字符串长度
        """
        return f"字符串 '{text[:20]}{'...' if len(text) > 20 else ''}' 的长度是 {len(text)} 个字符"
    
    return [calculator, get_current_time, search_knowledge, string_length]


# ============================================================
# 第二部分：创建 ReAct Agent
# ============================================================

def create_react_agent_demo():
    """
    创建一个 ReAct Agent
    
    ReAct = Reasoning + Acting
    Agent 会交替进行：
    1. 思考：分析当前情况，决定下一步
    2. 行动：选择并调用工具
    3. 观察：查看工具返回结果
    4. 重复直到得出最终答案
    
    注意：LangChain 1.2+ 推荐使用 langchain.agents 的 create_agent
    """
    from langchain.agents import create_agent as create_react_agent
    
    print_section("创建 ReAct Agent", "使用 LangGraph 构建")
    
    # 获取工具
    tools = create_tools()
    
    console.print("\n[yellow]已注册的工具:[/yellow]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("工具名", style="cyan")
    table.add_column("描述", style="green")
    
    for tool in tools:
        desc = tool.description.split('\n')[0][:50] + "..."
        table.add_row(tool.name, desc)
    
    console.print(table)
    
    # 获取 LLM
    llm = get_llm()
    
    console.print("\n[yellow]ReAct 工作流程:[/yellow]")
    console.print(Panel(
        "用户输入 → 思考 → 选择工具 → 执行 → 观察结果 → 继续/结束",
        title="ReAct 循环",
        border_style="blue"
    ))
    
    # 使用 LangGraph 创建 ReAct Agent
    # 新版 API 更简洁：只需要 model 和 tools
    agent = create_react_agent(
        model=llm,
        tools=tools,
        system_prompt="你是一个有帮助的助手。请使用提供的工具来回答用户的问题。回答时请使用中文。",
    )
    
    console.print("\n[green]✓ ReAct Agent 创建成功！[/green]")
    console.print("[dim]使用 LangGraph 的 create_react_agent 构建[/dim]")
    
    return agent


# ============================================================
# 第三部分：运行 Agent 示例
# ============================================================

def run_agent_examples(agent):
    """运行 Agent 示例，展示工具调用能力"""
    from langchain_core.messages import HumanMessage
    
    examples = [
        {
            "question": "现在几点了？",
            "description": "测试时间获取工具"
        },
        {
            "question": "计算 (15 + 27) * 3 等于多少？",
            "description": "测试计算器工具"
        },
        {
            "question": "什么是 LangChain？",
            "description": "测试知识搜索工具"
        },
        {
            "question": "计算 256 的平方根，然后告诉我现在的时间",
            "description": "测试多工具组合调用"
        },
    ]
    
    for i, example in enumerate(examples, 1):
        print_section(
            f"示例 {i}: {example['description']}", 
            f"问题: {example['question']}"
        )
        
        try:
            # LangGraph Agent 使用 messages 格式
            result = agent.invoke({
                "messages": [HumanMessage(content=example["question"])]
            })
            
            # 获取最后一条 AI 消息作为回答
            final_message = result["messages"][-1]
            
            console.print(Panel(
                final_message.content,
                title="[green]Agent 最终回答[/green]",
                border_style="green"
            ))
            
            # 显示工具调用过程
            tool_calls = [m for m in result["messages"] if hasattr(m, 'tool_calls') and m.tool_calls]
            if tool_calls:
                console.print("[dim]调用的工具:[/dim]")
                for msg in tool_calls:
                    for tc in msg.tool_calls:
                        console.print(f"  [cyan]→ {tc['name']}[/cyan]({tc['args']})")
            
        except Exception as e:
            console.print(f"[red]执行出错: {e}[/red]")
            import traceback
            traceback.print_exc()
        
        if i < len(examples):
            input("\n按 Enter 继续下一个示例...")


# ============================================================
# 第四部分：交互式对话
# ============================================================

def interactive_chat(agent):
    """交互式对话模式"""
    from langchain_core.messages import HumanMessage
    
    print_section("交互式对话", "输入 'quit' 或 'exit' 退出")
    
    console.print("""
[dim]你可以尝试以下问题：
- 计算 123 * 456
- 现在是什么时间？
- 什么是 Agent？
- "Hello World" 有多少个字符？
- 计算圆周率乘以 10 的平方
[/dim]
""")
    
    while True:
        try:
            user_input = input("\n👤 你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                console.print("[yellow]再见！[/yellow]")
                break
            
            console.print("\n[dim]Agent 思考中...[/dim]")
            result = agent.invoke({
                "messages": [HumanMessage(content=user_input)]
            })
            
            final_message = result["messages"][-1]
            console.print(f"\n🤖 Agent: {final_message.content}")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]已中断[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold]B1: ReAct Agent 入门教程[/bold]\n"
        "创建能调用工具的智能体",
        border_style="blue"
    ))
    
    console.print("""
[dim]ReAct 模式 (Reasoning + Acting):

┌─────────────────────────────────────────────────┐
│  Question: 用户问题                              │
│      ↓                                          │
│  Thought: 我需要先...（推理）                    │
│      ↓                                          │
│  Action: calculator                             │
│  Action Input: 2 + 3                            │
│      ↓                                          │
│  Observation: 计算结果: 5（工具返回）            │
│      ↓                                          │
│  Thought: 现在我知道答案了                       │
│      ↓                                          │
│  Final Answer: 2 + 3 等于 5                     │
└─────────────────────────────────────────────────┘
[/dim]
""")
    
    input("按 Enter 键开始创建 Agent...")
    
    # 创建 Agent
    agent = create_react_agent_demo()
    
    input("\n按 Enter 键运行示例...")
    
    # 运行示例
    run_agent_examples(agent)
    
    # 询问是否进入交互模式
    console.print("\n" + "=" * 60)
    choice = input("是否进入交互式对话模式？(y/n): ").strip().lower()
    
    if choice == 'y':
        interactive_chat(agent)
    
    # 总结
    console.print("\n" + "=" * 60)
    console.print(Panel(
        """[bold green]🎉 教程完成！[/bold green]

[bold]核心要点回顾：[/bold]

1. [cyan]@tool 装饰器[/cyan] - 快速定义工具
2. [cyan]create_react_agent[/cyan] - 创建 ReAct Agent
3. [cyan]AgentExecutor[/cyan] - 执行 Agent 并管理循环
4. [cyan]ReAct 循环[/cyan] - Thought → Action → Observation

[bold]工具定义关键点：[/bold]
- 描述要清晰（LLM 根据描述选择工具）
- 参数要明确（类型、含义）
- 返回值要有意义

[bold]下一步建议：[/bold]
- B2: 开发更多自定义工具（文件、Shell、网络）
- 或 A2: 添加对话记忆功能
""",
        title="学习总结",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
