#!/usr/bin/env python3
"""
===========================================
D1: 对话记忆系统
===========================================

本教程介绍如何为 Agent 添加记忆功能：
1. 为什么需要记忆？
2. 手动管理对话历史
3. 使用 LangGraph 的检查点（Checkpointer）
4. 构建有记忆的 Agent

记忆让 Agent 能够：
- 记住用户说过的话
- 保持对话连贯性
- 引用之前的信息

运行方式:
    cd /home/ailearn/projects/agent-learn-2
    conda activate agent-learn
    python examples/04_memory_system.py
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

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
        temperature=0.7,
    )


def print_section(title: str, description: str = ""):
    """打印章节标题"""
    console.print(f"\n{'='*60}")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    if description:
        console.print(f"[dim]{description}[/dim]")
    console.print('='*60)


# ============================================================
# 第一部分：为什么需要记忆？
# ============================================================

def demo_without_memory():
    """
    演示没有记忆的问题
    
    默认情况下，每次 LLM 调用都是独立的，
    LLM 不会记住之前的对话内容。
    """
    print_section("1. 没有记忆的问题", "每次对话都是独立的")
    
    from langchain_core.messages import HumanMessage
    
    llm = get_llm()
    
    # 对话 1
    console.print("\n[yellow]对话 1:[/yellow]")
    response1 = llm.invoke([HumanMessage(content="我叫小明，我在学习 Python")])
    console.print(f"👤 用户: 我叫小明，我在学习 Python")
    console.print(f"🤖 AI: {response1.content}")
    
    # 对话 2 - LLM 不会记住之前说的话
    console.print("\n[yellow]对话 2:[/yellow]")
    response2 = llm.invoke([HumanMessage(content="你还记得我叫什么名字吗？")])
    console.print(f"👤 用户: 你还记得我叫什么名字吗？")
    console.print(f"🤖 AI: {response2.content}")
    
    console.print("\n[red]问题：LLM 无法记住之前的对话！[/red]")


# ============================================================
# 第二部分：手动管理对话历史
# ============================================================

def demo_manual_history():
    """
    手动管理对话历史
    
    最简单的方法：把所有对话历史都发给 LLM
    """
    print_section("2. 手动管理对话历史", "将完整历史发送给 LLM")
    
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    
    llm = get_llm()
    
    # 维护对话历史
    chat_history = [
        SystemMessage(content="你是一个友好的助手，请记住用户告诉你的信息。")
    ]
    
    def chat(user_input: str) -> str:
        """带历史的对话"""
        # 添加用户消息
        chat_history.append(HumanMessage(content=user_input))
        
        # 发送完整历史给 LLM
        response = llm.invoke(chat_history)
        
        # 保存 AI 回复
        chat_history.append(AIMessage(content=response.content))
        
        return response.content
    
    # 测试对话
    conversations = [
        "我叫小明，今年 25 岁",
        "我在学习 Python 和 LangChain",
        "你还记得我叫什么？我在学什么？我多大了？",
    ]
    
    for user_input in conversations:
        console.print(f"\n👤 用户: {user_input}")
        response = chat(user_input)
        console.print(f"🤖 AI: {response}")
    
    console.print(f"\n[green]✓ 现在 LLM 能记住对话了！[/green]")
    console.print(f"[dim]当前历史消息数: {len(chat_history)}[/dim]")
    
    return chat_history


# ============================================================
# 第三部分：使用 MessagesPlaceholder
# ============================================================

def demo_messages_placeholder():
    """
    使用 ChatPromptTemplate 和 MessagesPlaceholder
    
    更优雅的方式管理对话历史
    """
    print_section("3. MessagesPlaceholder", "模板化的历史管理")
    
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.output_parsers import StrOutputParser
    
    # 创建带历史占位符的模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个有帮助的助手。请记住用户告诉你的所有信息。"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()
    
    # 对话历史
    history = []
    
    def chat(user_input: str) -> str:
        """对话函数"""
        response = chain.invoke({
            "history": history,
            "input": user_input
        })
        
        # 更新历史
        history.append(HumanMessage(content=user_input))
        history.append(AIMessage(content=response))
        
        return response
    
    # 测试
    console.print("\n[yellow]开始对话:[/yellow]")
    
    test_inputs = [
        "我的名字是张三，我是一名程序员",
        "我最喜欢的编程语言是 Python",
        "请总结一下你知道的关于我的信息",
    ]
    
    for user_input in test_inputs:
        console.print(f"\n👤 用户: {user_input}")
        response = chat(user_input)
        console.print(f"🤖 AI: {response}")
    
    console.print(f"\n[green]✓ MessagesPlaceholder 让代码更清晰[/green]")


# ============================================================
# 第四部分：LangGraph Agent 的记忆
# ============================================================

def demo_langgraph_memory():
    """
    LangGraph Agent 的记忆管理
    
    LangGraph 使用 Checkpointer 来管理状态和记忆
    """
    print_section("4. LangGraph Agent 记忆", "使用 MemorySaver 实现持久记忆")
    
    import math
    import datetime
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage
    from langchain.agents import create_agent
    from langgraph.checkpoint.memory import MemorySaver
    
    # 定义工具
    @tool
    def calculator(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression, {"__builtins__": {}, "math": math})
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {e}"
    
    @tool
    def get_time() -> str:
        """获取当前时间"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    tools = [calculator, get_time]
    llm = get_llm()
    
    # 创建内存检查点（记忆存储）
    memory = MemorySaver()
    
    # 创建带记忆的 Agent
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="你是一个有帮助的助手。请记住用户告诉你的信息，并在后续对话中使用。",
        checkpointer=memory,  # 启用记忆
    )
    
    console.print("\n[green]✓ 带记忆的 Agent 创建成功[/green]")
    
    # 配置（包含会话 ID）
    config = {"configurable": {"thread_id": "session_001"}}
    
    # 测试对话
    test_conversations = [
        "我叫李华，今年 30 岁，是一名数据科学家",
        "我最近在研究机器学习和 LangChain",
        "帮我计算 2 的 10 次方",
        "请总结一下你知道的关于我的所有信息",
    ]
    
    console.print("\n[yellow]开始对话（会话 ID: session_001）:[/yellow]")
    
    for user_input in test_conversations:
        console.print(f"\n👤 用户: {user_input}")
        
        result = agent.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config  # 传入配置以启用记忆
        )
        
        answer = result["messages"][-1].content
        console.print(f"🤖 AI: {answer}")
        
        # 显示工具调用
        for msg in result["messages"]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    console.print(f"  [dim]→ 调用: {tc['name']}[/dim]")
    
    console.print(f"\n[green]✓ Agent 成功记住了对话内容！[/green]")
    
    return agent, memory, config


# ============================================================
# 第五部分：多会话管理
# ============================================================

def demo_multi_session(agent, memory):
    """
    多会话管理
    
    不同的 thread_id 代表不同的对话会话，
    彼此独立，互不影响
    """
    print_section("5. 多会话管理", "不同用户/会话之间隔离")
    
    from langchain_core.messages import HumanMessage
    
    # 用户 A 的会话
    config_a = {"configurable": {"thread_id": "user_alice"}}
    
    # 用户 B 的会话
    config_b = {"configurable": {"thread_id": "user_bob"}}
    
    console.print("\n[yellow]用户 Alice 的对话:[/yellow]")
    result = agent.invoke(
        {"messages": [HumanMessage(content="我是 Alice，我喜欢喝咖啡")]},
        config=config_a
    )
    console.print(f"🔵 Alice: 我是 Alice，我喜欢喝咖啡")
    console.print(f"🤖 AI: {result['messages'][-1].content}")
    
    console.print("\n[yellow]用户 Bob 的对话:[/yellow]")
    result = agent.invoke(
        {"messages": [HumanMessage(content="我是 Bob，我喜欢喝茶")]},
        config=config_b
    )
    console.print(f"🟢 Bob: 我是 Bob，我喜欢喝茶")
    console.print(f"🤖 AI: {result['messages'][-1].content}")
    
    # 验证隔离性
    console.print("\n[yellow]验证 Alice 会话的独立性:[/yellow]")
    result = agent.invoke(
        {"messages": [HumanMessage(content="我喜欢喝什么？")]},
        config=config_a
    )
    console.print(f"🔵 Alice: 我喜欢喝什么？")
    console.print(f"🤖 AI: {result['messages'][-1].content}")
    
    console.print("\n[yellow]验证 Bob 会话的独立性:[/yellow]")
    result = agent.invoke(
        {"messages": [HumanMessage(content="我喜欢喝什么？")]},
        config=config_b
    )
    console.print(f"🟢 Bob: 我喜欢喝什么？")
    console.print(f"🤖 AI: {result['messages'][-1].content}")
    
    console.print(f"\n[green]✓ 不同会话之间完全隔离[/green]")


# ============================================================
# 第六部分：交互式对话
# ============================================================

def interactive_chat_with_memory():
    """带记忆的交互式对话"""
    print_section("6. 交互式对话", "输入 'quit' 退出，'clear' 清除历史")
    
    import math
    import datetime
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage
    from langchain.agents import create_agent
    from langgraph.checkpoint.memory import MemorySaver
    
    @tool
    def calculator(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression, {"__builtins__": {}, "math": math})
            return f"计算结果: {result}"
        except:
            return "计算错误"
    
    tools = [calculator]
    llm = get_llm()
    memory = MemorySaver()
    
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="你是一个友好的助手。记住用户说的话，在对话中引用之前的信息。",
        checkpointer=memory,
    )
    
    config = {"configurable": {"thread_id": "interactive"}}
    
    console.print("""
[dim]提示：
- Agent 会记住你说的话
- 输入 'quit' 退出
- 输入 'new' 开始新会话
[/dim]
""")
    
    session_id = 1
    
    while True:
        try:
            user_input = input("\n👤 你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                console.print("[yellow]再见！[/yellow]")
                break
            
            if user_input.lower() == 'new':
                session_id += 1
                config = {"configurable": {"thread_id": f"session_{session_id}"}}
                console.print(f"[yellow]已开始新会话 (ID: session_{session_id})[/yellow]")
                continue
            
            result = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )
            
            answer = result["messages"][-1].content
            console.print(f"🤖 AI: {answer}")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]已中断[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold]D1: 对话记忆系统教程[/bold]\n"
        "让 Agent 能够记住对话内容",
        border_style="blue"
    ))
    
    console.print("""
[dim]记忆系统解决的问题：

┌─────────────────────────────────────────────────────────┐
│  没有记忆：                                              │
│  用户: 我叫小明    →  AI: 你好小明！                     │
│  用户: 我叫什么？  →  AI: 抱歉，我不知道你叫什么        │
│                                                         │
│  有记忆：                                                │
│  用户: 我叫小明    →  AI: 你好小明！                     │
│  用户: 我叫什么？  →  AI: 你叫小明                       │
└─────────────────────────────────────────────────────────┘
[/dim]
""")
    
    input("按 Enter 开始...")
    
    # 1. 没有记忆的问题
    demo_without_memory()
    input("\n按 Enter 继续...")
    
    # 2. 手动管理历史
    demo_manual_history()
    input("\n按 Enter 继续...")
    
    # 3. MessagesPlaceholder
    demo_messages_placeholder()
    input("\n按 Enter 继续...")
    
    # 4. LangGraph 记忆
    agent, memory, config = demo_langgraph_memory()
    input("\n按 Enter 继续...")
    
    # 5. 多会话
    demo_multi_session(agent, memory)
    
    # 6. 交互模式
    console.print("\n" + "=" * 60)
    choice = input("是否进入交互式对话？(y/n): ").strip().lower()
    if choice == 'y':
        interactive_chat_with_memory()
    
    # 总结
    console.print("\n" + "=" * 60)
    console.print(Panel(
        """[bold green]🎉 记忆系统教程完成！[/bold green]

[bold]核心要点：[/bold]

1. [cyan]问题[/cyan] - 默认情况下 LLM 不记住对话
2. [cyan]手动历史[/cyan] - 将完整对话历史发给 LLM
3. [cyan]MessagesPlaceholder[/cyan] - 模板化管理历史
4. [cyan]MemorySaver[/cyan] - LangGraph 的检查点机制
5. [cyan]thread_id[/cyan] - 区分不同会话/用户

[bold]记忆类型选择：[/bold]
- 短期记忆：MemorySaver（内存中）
- 持久记忆：SqliteSaver（保存到文件）
- 分布式：PostgresSaver（数据库）

[bold]下一步建议：[/bold]
- C1: 构建 Streamlit Web 界面
- 将所有功能整合到完整应用
""",
        title="学习总结",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
