#!/usr/bin/env python3
"""
===========================================
M5: LangGraph 高级工作流
===========================================

本教程介绍 LangGraph 的高级功能：
1. 状态图（StateGraph）基础
2. 自定义节点和边
3. 条件分支（Conditional Edges）
4. 循环工作流
5. 多 Agent 协作

LangGraph 核心概念：
- State（状态）：在节点之间传递的数据
- Node（节点）：执行具体操作的函数
- Edge（边）：节点之间的连接
- Conditional Edge：根据条件选择下一个节点

运行方式:
    cd /home/ailearn/projects/agent-learn-2
    conda activate agent-learn
    python examples/05_langgraph_advanced.py
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
# 第一部分：StateGraph 基础
# ============================================================

def demo_basic_graph():
    """
    基础状态图
    
    最简单的 LangGraph 示例：
    START → node_a → node_b → END
    """
    print_section("1. StateGraph 基础", "最简单的线性工作流")
    
    from typing import TypedDict
    from langgraph.graph import StateGraph, START, END
    
    # 1. 定义状态（State）
    # 状态是在节点之间传递的数据结构
    class SimpleState(TypedDict):
        input: str
        step1_result: str
        step2_result: str
        final_result: str
    
    # 2. 定义节点函数
    # 每个节点接收状态，返回更新后的状态
    def step1(state: SimpleState) -> SimpleState:
        """第一步：转换为大写"""
        console.print("  [yellow]执行 Step 1: 转换为大写[/yellow]")
        result = state["input"].upper()
        return {"step1_result": result}
    
    def step2(state: SimpleState) -> SimpleState:
        """第二步：添加前缀"""
        console.print("  [yellow]执行 Step 2: 添加前缀[/yellow]")
        result = f"[处理完成] {state['step1_result']}"
        return {"step2_result": result}
    
    def finalize(state: SimpleState) -> SimpleState:
        """最终步骤：生成结果"""
        console.print("  [yellow]执行 Finalize: 生成最终结果[/yellow]")
        return {"final_result": state["step2_result"]}
    
    # 3. 构建图
    graph = StateGraph(SimpleState)
    
    # 添加节点
    graph.add_node("step1", step1)
    graph.add_node("step2", step2)
    graph.add_node("finalize", finalize)
    
    # 添加边（定义执行顺序）
    graph.add_edge(START, "step1")
    graph.add_edge("step1", "step2")
    graph.add_edge("step2", "finalize")
    graph.add_edge("finalize", END)
    
    # 4. 编译图
    app = graph.compile()
    
    # 显示图结构
    console.print("\n[green]图结构:[/green]")
    console.print("  START → step1 → step2 → finalize → END")
    
    # 5. 执行
    console.print("\n[green]执行工作流:[/green]")
    result = app.invoke({"input": "hello world"})
    
    console.print(f"\n[green]结果:[/green]")
    console.print(f"  输入: {result.get('input', 'N/A')}")
    console.print(f"  Step1: {result.get('step1_result', 'N/A')}")
    console.print(f"  Step2: {result.get('step2_result', 'N/A')}")
    console.print(f"  最终: {result.get('final_result', 'N/A')}")
    
    return app


# ============================================================
# 第二部分：条件分支
# ============================================================

def demo_conditional_edges():
    """
    条件分支
    
    根据状态决定下一步走向：
    START → classifier → [positive/negative/neutral] → END
    """
    print_section("2. 条件分支", "根据条件选择不同路径")
    
    from typing import TypedDict, Literal
    from langgraph.graph import StateGraph, START, END
    
    # 状态定义
    class SentimentState(TypedDict):
        text: str
        sentiment: str
        response: str
    
    llm = get_llm()
    
    # 节点：分类器
    def classifier(state: SentimentState) -> SentimentState:
        """分析文本情感"""
        console.print(f"  [yellow]分析文本: {state['text'][:30]}...[/yellow]")
        
        from langchain_core.messages import HumanMessage
        
        prompt = f"""分析以下文本的情感倾向，只回答一个词：positive、negative 或 neutral

文本：{state['text']}

情感："""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        sentiment = response.content.strip().lower()
        
        # 确保是有效值
        if "positive" in sentiment or "正面" in sentiment:
            sentiment = "positive"
        elif "negative" in sentiment or "负面" in sentiment:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        console.print(f"  [green]情感分析结果: {sentiment}[/green]")
        return {"sentiment": sentiment}
    
    # 条件路由函数
    def route_by_sentiment(state: SentimentState) -> Literal["positive_handler", "negative_handler", "neutral_handler"]:
        """根据情感选择处理器"""
        sentiment = state["sentiment"]
        if sentiment == "positive":
            return "positive_handler"
        elif sentiment == "negative":
            return "negative_handler"
        else:
            return "neutral_handler"
    
    # 各情感处理器
    def positive_handler(state: SentimentState) -> SentimentState:
        console.print("  [green]→ 进入正面情感处理[/green]")
        return {"response": "😊 感谢您的积极反馈！我们会继续努力！"}
    
    def negative_handler(state: SentimentState) -> SentimentState:
        console.print("  [red]→ 进入负面情感处理[/red]")
        return {"response": "😔 非常抱歉给您带来不好的体验，我们会改进！"}
    
    def neutral_handler(state: SentimentState) -> SentimentState:
        console.print("  [blue]→ 进入中性情感处理[/blue]")
        return {"response": "📝 感谢您的反馈，我们已记录。"}
    
    # 构建图
    graph = StateGraph(SentimentState)
    
    graph.add_node("classifier", classifier)
    graph.add_node("positive_handler", positive_handler)
    graph.add_node("negative_handler", negative_handler)
    graph.add_node("neutral_handler", neutral_handler)
    
    # 添加边
    graph.add_edge(START, "classifier")
    
    # 条件边：根据情感选择下一个节点
    graph.add_conditional_edges(
        "classifier",
        route_by_sentiment,
        {
            "positive_handler": "positive_handler",
            "negative_handler": "negative_handler",
            "neutral_handler": "neutral_handler",
        }
    )
    
    graph.add_edge("positive_handler", END)
    graph.add_edge("negative_handler", END)
    graph.add_edge("neutral_handler", END)
    
    app = graph.compile()
    
    # 显示图结构
    console.print("\n[green]图结构:[/green]")
    console.print("""
                    ┌─positive→ positive_handler ─┐
    START → classifier ─neutral─→ neutral_handler ──→ END
                    └─negative→ negative_handler ─┘
    """)
    
    # 测试
    test_texts = [
        "这个产品太棒了，完全超出预期！",
        "服务太差了，再也不会来了",
        "东西收到了，还行吧",
    ]
    
    for text in test_texts:
        console.print(f"\n[cyan]测试文本:[/cyan] {text}")
        result = app.invoke({"text": text})
        console.print(f"[cyan]回复:[/cyan] {result['response']}")
    
    return app


# ============================================================
# 第三部分：循环工作流
# ============================================================

def demo_loop_workflow():
    """
    循环工作流
    
    迭代改进直到满足条件：
    START → generate → evaluate → [pass/retry] → END
    """
    print_section("3. 循环工作流", "迭代执行直到满足条件")
    
    from typing import TypedDict, Literal
    from langgraph.graph import StateGraph, START, END
    
    class IterState(TypedDict):
        task: str
        current_answer: str
        iteration: int
        max_iterations: int
        is_satisfactory: bool
    
    llm = get_llm()
    
    def generate(state: IterState) -> IterState:
        """生成答案"""
        iteration = state.get("iteration", 0) + 1
        console.print(f"  [yellow]第 {iteration} 次生成...[/yellow]")
        
        from langchain_core.messages import HumanMessage
        
        prompt = state["task"]
        if state.get("current_answer"):
            prompt += f"\n\n之前的答案不够好，请改进：\n{state['current_answer']}"
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        return {
            "current_answer": response.content,
            "iteration": iteration
        }
    
    def evaluate(state: IterState) -> IterState:
        """评估答案质量"""
        console.print(f"  [yellow]评估答案质量...[/yellow]")
        
        # 简单评估：答案长度超过 50 字符认为合格
        # 实际应用中可以用 LLM 评估
        is_good = len(state["current_answer"]) > 50
        
        if is_good:
            console.print(f"  [green]✓ 答案合格[/green]")
        else:
            console.print(f"  [red]✗ 答案不合格，需要改进[/red]")
        
        return {"is_satisfactory": is_good}
    
    def should_continue(state: IterState) -> Literal["generate", "end"]:
        """决定是继续还是结束"""
        if state.get("is_satisfactory", False):
            return "end"
        if state.get("iteration", 0) >= state.get("max_iterations", 3):
            console.print(f"  [yellow]达到最大迭代次数[/yellow]")
            return "end"
        return "generate"
    
    # 构建图
    graph = StateGraph(IterState)
    
    graph.add_node("generate", generate)
    graph.add_node("evaluate", evaluate)
    
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "evaluate")
    
    # 条件边：决定是循环还是结束
    graph.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "generate": "generate",  # 继续循环
            "end": END               # 结束
        }
    )
    
    app = graph.compile()
    
    # 显示图结构
    console.print("\n[green]图结构:[/green]")
    console.print("""
                         ┌──────────────┐
                         ↓              │
    START → generate → evaluate ──retry─┘
                         │
                         └──pass──→ END
    """)
    
    # 测试
    console.print("\n[cyan]执行循环工作流:[/cyan]")
    result = app.invoke({
        "task": "用一句话解释什么是人工智能",
        "max_iterations": 3
    })
    
    console.print(f"\n[green]最终答案 (迭代 {result['iteration']} 次):[/green]")
    console.print(Panel(result["current_answer"], border_style="green"))
    
    return app


# ============================================================
# 第四部分：多 Agent 协作
# ============================================================

def demo_multi_agent():
    """
    多 Agent 协作
    
    多个专家 Agent 协作完成任务：
    START → researcher → writer → reviewer → END
    """
    print_section("4. 多 Agent 协作", "多个专家协作完成任务")
    
    from typing import TypedDict, List
    from langgraph.graph import StateGraph, START, END
    from langchain_core.messages import HumanMessage, SystemMessage
    
    class MultiAgentState(TypedDict):
        topic: str
        research: str
        draft: str
        review: str
        final_article: str
    
    llm = get_llm()
    
    def researcher(state: MultiAgentState) -> MultiAgentState:
        """研究员：收集信息"""
        console.print("  [blue]🔍 研究员正在收集信息...[/blue]")
        
        messages = [
            SystemMessage(content="你是一个研究员，负责收集和整理主题相关的关键信息。"),
            HumanMessage(content=f"请列出关于「{state['topic']}」的 3 个关键点，每点一句话。")
        ]
        
        response = llm.invoke(messages)
        console.print(f"  [dim]研究完成[/dim]")
        return {"research": response.content}
    
    def writer(state: MultiAgentState) -> MultiAgentState:
        """写手：撰写初稿"""
        console.print("  [green]✍️ 写手正在撰写初稿...[/green]")
        
        messages = [
            SystemMessage(content="你是一个专业写手，负责将研究要点整合成流畅的文章。"),
            HumanMessage(content=f"""基于以下研究要点，写一段简短的介绍（100字以内）：

主题：{state['topic']}

研究要点：
{state['research']}""")
        ]
        
        response = llm.invoke(messages)
        console.print(f"  [dim]初稿完成[/dim]")
        return {"draft": response.content}
    
    def reviewer(state: MultiAgentState) -> MultiAgentState:
        """审稿人：审核并改进"""
        console.print("  [yellow]📝 审稿人正在审核...[/yellow]")
        
        messages = [
            SystemMessage(content="你是一个审稿人，负责改进文章质量，使其更加清晰专业。"),
            HumanMessage(content=f"""请审核并改进以下文章，使其更加专业和清晰：

{state['draft']}

改进后的文章：""")
        ]
        
        response = llm.invoke(messages)
        console.print(f"  [dim]审核完成[/dim]")
        return {
            "review": "已审核",
            "final_article": response.content
        }
    
    # 构建图
    graph = StateGraph(MultiAgentState)
    
    graph.add_node("researcher", researcher)
    graph.add_node("writer", writer)
    graph.add_node("reviewer", reviewer)
    
    graph.add_edge(START, "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", "reviewer")
    graph.add_edge("reviewer", END)
    
    app = graph.compile()
    
    # 显示图结构
    console.print("\n[green]多 Agent 协作流程:[/green]")
    console.print("""
    START → 🔍 研究员 → ✍️ 写手 → 📝 审稿人 → END
              │           │          │
              ↓           ↓          ↓
           收集信息    撰写初稿    审核改进
    """)
    
    # 测试
    console.print("\n[cyan]执行多 Agent 协作:[/cyan]")
    result = app.invoke({"topic": "LangChain 框架"})
    
    console.print(f"\n[green]研究要点:[/green]")
    console.print(result["research"])
    
    console.print(f"\n[green]初稿:[/green]")
    console.print(result["draft"])
    
    console.print(f"\n[green]最终文章:[/green]")
    console.print(Panel(result["final_article"], border_style="green"))
    
    return app


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold]M5: LangGraph 高级工作流教程[/bold]\n"
        "构建复杂的多步骤任务流程",
        border_style="blue"
    ))
    
    console.print("""
[dim]LangGraph 核心概念：

┌─────────────────────────────────────────────────────────┐
│  State（状态）：在节点间传递的数据                        │
│  Node（节点）：执行具体操作的函数                         │
│  Edge（边）：节点之间的连接                               │
│  Conditional Edge：根据条件选择下一个节点                 │
└─────────────────────────────────────────────────────────┘
[/dim]
""")
    
    input("按 Enter 开始...")
    
    # 1. 基础状态图
    demo_basic_graph()
    input("\n按 Enter 继续...")
    
    # 2. 条件分支
    demo_conditional_edges()
    input("\n按 Enter 继续...")
    
    # 3. 循环工作流
    demo_loop_workflow()
    input("\n按 Enter 继续...")
    
    # 4. 多 Agent 协作
    demo_multi_agent()
    
    # 总结
    console.print("\n" + "=" * 60)
    console.print(Panel(
        """[bold green]🎉 LangGraph 高级教程完成！[/bold green]

[bold]核心要点：[/bold]

1. [cyan]StateGraph[/cyan] - 定义状态和节点的图结构
2. [cyan]节点函数[/cyan] - 接收状态，返回更新
3. [cyan]条件边[/cyan] - add_conditional_edges 实现分支
4. [cyan]循环[/cyan] - 条件边指回之前的节点
5. [cyan]多 Agent[/cyan] - 不同角色的节点串联协作

[bold]应用场景：[/bold]
- 审批流程（多级审批）
- 内容生成（研究→写作→审核）
- 客服系统（分类→路由→处理）
- 迭代优化（生成→评估→改进）

[bold]下一步建议：[/bold]
- M7: 将 LangGraph 集成到 Web 应用
- 构建实际业务工作流
""",
        title="学习总结",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
