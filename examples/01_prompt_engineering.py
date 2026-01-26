#!/usr/bin/env python3
"""
===========================================
A1: Prompt 工程基础
===========================================

本教程涵盖 LangChain 中 Prompt 工程的核心概念：
1. PromptTemplate - 基础字符串模板
2. ChatPromptTemplate - 聊天消息模板
3. Few-shot Prompting - 少样本学习
4. 高级技巧 - 条件逻辑、输出解析

运行方式:
    cd /home/ailearn/projects/agent-learn-2
    conda activate agent-learn
    python examples/01_prompt_engineering.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

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


def example_1_basic_prompt_template():
    """
    示例 1: 基础 PromptTemplate
    
    PromptTemplate 是最简单的模板类型，用于创建带变量的字符串模板。
    """
    print_section("1. 基础 PromptTemplate", "创建带变量的字符串模板")
    
    from langchain_core.prompts import PromptTemplate
    
    # 方式 1: 使用 from_template 创建
    console.print("\n[yellow]方式 1: from_template()[/yellow]")
    template1 = PromptTemplate.from_template(
        "请用简单的语言解释什么是 {concept}，并给出一个实际例子。"
    )
    
    # 格式化模板
    prompt = template1.format(concept="机器学习")
    console.print(f"[green]模板变量:[/green] {template1.input_variables}")
    console.print(f"[green]格式化结果:[/green]\n{prompt}")
    
    # 方式 2: 显式指定变量
    console.print("\n[yellow]方式 2: 显式指定变量[/yellow]")
    template2 = PromptTemplate(
        input_variables=["topic", "audience"],
        template="请为 {audience} 写一段关于 {topic} 的简短介绍，不超过50字。"
    )
    
    prompt = template2.format(topic="Python编程", audience="初学者")
    console.print(f"[green]模板变量:[/green] {template2.input_variables}")
    console.print(f"[green]格式化结果:[/green]\n{prompt}")
    
    # 实际调用 LLM
    console.print("\n[yellow]调用 LLM 生成回复:[/yellow]")
    llm = get_llm()
    response = llm.invoke(prompt)
    console.print(Panel(response.content, title="Kimi 回复", border_style="green"))
    
    return template2


def example_2_chat_prompt_template():
    """
    示例 2: ChatPromptTemplate
    
    ChatPromptTemplate 用于构建多角色对话消息，更适合聊天模型。
    包含 system(系统)、human(用户)、ai(助手) 三种角色。
    """
    print_section("2. ChatPromptTemplate", "构建多角色对话消息")
    
    from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    
    # 方式 1: 使用元组列表创建（推荐）
    console.print("\n[yellow]方式 1: 元组列表（推荐）[/yellow]")
    chat_template1 = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的 {role}，请用专业但易懂的方式回答问题。"),
        ("human", "{question}")
    ])
    
    messages = chat_template1.format_messages(
        role="Python 教师",
        question="什么是列表推导式？"
    )
    
    console.print("[green]生成的消息:[/green]")
    for msg in messages:
        console.print(f"  [{msg.type}]: {msg.content}")
    
    # 方式 2: 使用 Message 对象
    console.print("\n[yellow]方式 2: Message 对象[/yellow]")
    chat_template2 = ChatPromptTemplate.from_messages([
        SystemMessage(content="你是一个友好的助手，回答要简洁。"),
        HumanMessagePromptTemplate.from_template("请解释：{term}")
    ])
    
    messages = chat_template2.format_messages(term="装饰器")
    for msg in messages:
        console.print(f"  [{msg.type}]: {msg.content}")
    
    # 方式 3: 包含历史对话
    console.print("\n[yellow]方式 3: 包含历史对话[/yellow]")
    chat_template3 = ChatPromptTemplate.from_messages([
        ("system", "你是一个编程助手。"),
        ("human", "Python 有哪些数据类型？"),
        ("ai", "Python 主要有：int, float, str, list, dict, tuple, set, bool 等。"),
        ("human", "{followup}")
    ])
    
    messages = chat_template3.format_messages(
        followup="详细说说 dict 的用法"
    )
    
    console.print("[green]生成的对话历史:[/green]")
    for msg in messages:
        role = {"system": "🔧", "human": "👤", "ai": "🤖"}.get(msg.type, "❓")
        console.print(f"  {role} [{msg.type}]: {msg.content[:50]}...")
    
    # 调用 LLM
    console.print("\n[yellow]调用 LLM 继续对话:[/yellow]")
    llm = get_llm()
    response = llm.invoke(messages)
    console.print(Panel(response.content, title="Kimi 回复", border_style="green"))
    
    return chat_template3


def example_3_few_shot_prompting():
    """
    示例 3: Few-shot Prompting（少样本学习）
    
    通过提供几个示例，让模型学习期望的输出格式或风格。
    这是提升 LLM 输出质量的重要技巧。
    """
    print_section("3. Few-shot Prompting", "通过示例教会模型输出格式")
    
    from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
    
    # 定义示例
    examples = [
        {
            "question": "Python 中如何反转字符串？",
            "answer": "使用切片 [::-1]，例如：'hello'[::-1] 返回 'olleh'"
        },
        {
            "question": "如何检查列表是否为空？",
            "answer": "使用 if not my_list: 或 if len(my_list) == 0:"
        },
        {
            "question": "如何合并两个字典？",
            "answer": "Python 3.9+ 使用 | 运算符：dict1 | dict2，或使用 {**dict1, **dict2}"
        }
    ]
    
    # 定义示例的格式模板
    example_template = PromptTemplate(
        input_variables=["question", "answer"],
        template="问：{question}\n答：{answer}"
    )
    
    # 创建 Few-shot 模板
    few_shot_template = FewShotPromptTemplate(
        examples=examples,
        example_prompt=example_template,
        prefix="你是一个 Python 专家，请用简洁的方式回答问题。以下是一些示例：\n",
        suffix="\n问：{input}\n答：",
        input_variables=["input"]
    )
    
    # 格式化查看效果
    prompt = few_shot_template.format(input="如何交换两个变量的值？")
    
    console.print("[green]生成的完整 Prompt:[/green]")
    console.print(Panel(prompt, border_style="blue"))
    
    # 调用 LLM
    console.print("\n[yellow]调用 LLM:[/yellow]")
    llm = get_llm()
    response = llm.invoke(prompt)
    console.print(Panel(response.content, title="Kimi 回复", border_style="green"))
    
    return few_shot_template


def example_4_chat_few_shot():
    """
    示例 4: 聊天模式的 Few-shot
    
    在聊天场景中使用 Few-shot，通过 human/ai 消息对提供示例。
    """
    print_section("4. 聊天模式 Few-shot", "在对话中嵌入示例")
    
    from langchain_core.prompts import ChatPromptTemplate
    
    # 使用对话历史作为 few-shot 示例
    chat_few_shot = ChatPromptTemplate.from_messages([
        ("system", """你是一个情感分析助手。
请分析用户输入文本的情感，并按以下格式输出：
- 情感：正面/负面/中性
- 置信度：高/中/低
- 关键词：[影响判断的关键词]"""),
        
        # Few-shot 示例 1
        ("human", "这个产品太棒了，完全超出预期！"),
        ("ai", """- 情感：正面
- 置信度：高
- 关键词：[太棒了, 超出预期]"""),
        
        # Few-shot 示例 2
        ("human", "服务态度一般，价格还行吧"),
        ("ai", """- 情感：中性
- 置信度：中
- 关键词：[一般, 还行]"""),
        
        # Few-shot 示例 3
        ("human", "等了一个小时，体验很差"),
        ("ai", """- 情感：负面
- 置信度：高
- 关键词：[等了一个小时, 很差]"""),
        
        # 用户实际输入
        ("human", "{user_input}")
    ])
    
    # 格式化
    messages = chat_few_shot.format_messages(
        user_input="东西收到了，包装完好，就是物流有点慢"
    )
    
    console.print("[green]生成的消息序列:[/green]")
    for i, msg in enumerate(messages):
        role = {"system": "🔧 系统", "human": "👤 用户", "ai": "🤖 助手"}.get(msg.type, "❓")
        content = msg.content[:40] + "..." if len(msg.content) > 40 else msg.content
        console.print(f"  {i+1}. {role}: {content}")
    
    # 调用 LLM
    console.print("\n[yellow]调用 LLM 分析新文本:[/yellow]")
    llm = get_llm()
    response = llm.invoke(messages)
    console.print(Panel(response.content, title="情感分析结果", border_style="green"))
    
    return chat_few_shot


def example_5_output_parser():
    """
    示例 5: 输出解析器
    
    使用 OutputParser 将 LLM 输出解析为结构化数据。
    """
    print_section("5. 输出解析器", "将 LLM 输出解析为结构化数据")
    
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import PydanticOutputParser
    from pydantic import BaseModel, Field
    from typing import List
    
    # 定义输出结构
    class BookRecommendation(BaseModel):
        title: str = Field(description="书名")
        author: str = Field(description="作者")
        reason: str = Field(description="推荐理由，一句话")
    
    class BookList(BaseModel):
        topic: str = Field(description="主题")
        books: List[BookRecommendation] = Field(description="推荐书籍列表")
    
    # 创建解析器
    parser = PydanticOutputParser(pydantic_object=BookList)
    
    # 创建包含格式说明的模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个图书推荐助手。
请根据用户的需求推荐书籍。

{format_instructions}"""),
        ("human", "请推荐 2 本关于 {topic} 的书")
    ])
    
    # 获取格式说明
    format_instructions = parser.get_format_instructions()
    console.print("[green]格式说明（发送给 LLM）:[/green]")
    console.print(Panel(format_instructions[:500] + "...", border_style="blue"))
    
    # 格式化消息
    messages = prompt.format_messages(
        topic="Python 编程入门",
        format_instructions=format_instructions
    )
    
    # 调用 LLM
    console.print("\n[yellow]调用 LLM:[/yellow]")
    llm = get_llm()
    response = llm.invoke(messages)
    console.print(Panel(response.content, title="LLM 原始输出", border_style="yellow"))
    
    # 解析输出
    console.print("\n[yellow]解析为结构化数据:[/yellow]")
    try:
        result = parser.parse(response.content)
        console.print(f"[green]主题:[/green] {result.topic}")
        console.print(f"[green]推荐书籍:[/green]")
        for i, book in enumerate(result.books, 1):
            console.print(f"  {i}. 《{book.title}》- {book.author}")
            console.print(f"     推荐理由: {book.reason}")
    except Exception as e:
        console.print(f"[red]解析失败: {e}[/red]")
        console.print("[dim]提示: LLM 输出可能不符合 JSON 格式，实际应用中需要重试机制[/dim]")
    
    return parser


def example_6_prompt_composition():
    """
    示例 6: Prompt 组合与复用
    
    展示如何组合多个模板，构建复杂的 Prompt。
    """
    print_section("6. Prompt 组合与复用", "构建模块化的 Prompt 系统")
    
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import HumanMessage, AIMessage
    
    # 创建带有消息占位符的模板（用于动态插入对话历史）
    prompt_with_history = ChatPromptTemplate.from_messages([
        ("system", "你是一个有帮助的助手。记住用户之前说过的话。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    
    # 模拟对话历史
    chat_history = [
        HumanMessage(content="我叫小明"),
        AIMessage(content="你好小明！很高兴认识你。有什么我可以帮助你的吗？"),
        HumanMessage(content="我在学习 Python"),
        AIMessage(content="太棒了！Python 是一门很好的编程语言，非常适合初学者。你目前学到哪里了？"),
    ]
    
    # 格式化消息
    messages = prompt_with_history.format_messages(
        chat_history=chat_history,
        input="你还记得我叫什么名字吗？我在学什么？"
    )
    
    console.print("[green]带历史记录的消息序列:[/green]")
    for msg in messages:
        role = {"system": "🔧", "human": "👤", "ai": "🤖"}.get(msg.type, "❓")
        content = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
        console.print(f"  {role} {content}")
    
    # 调用 LLM
    console.print("\n[yellow]调用 LLM（测试记忆能力）:[/yellow]")
    llm = get_llm()
    response = llm.invoke(messages)
    console.print(Panel(response.content, title="Kimi 回复", border_style="green"))
    
    return prompt_with_history


def main():
    """主函数 - 运行所有示例"""
    console.print(Panel.fit(
        "[bold]A1: Prompt 工程基础教程[/bold]\n"
        "学习 LangChain 中的 Prompt 模板系统",
        border_style="blue"
    ))
    
    console.print("""
[dim]本教程包含以下内容：
1. 基础 PromptTemplate - 简单字符串模板
2. ChatPromptTemplate - 多角色对话模板
3. Few-shot Prompting - 少样本学习
4. 聊天模式 Few-shot - 对话中的示例
5. 输出解析器 - 结构化输出
6. Prompt 组合与复用 - 模块化设计
[/dim]
""")
    
    input("按 Enter 键开始...")
    
    # 运行所有示例
    example_1_basic_prompt_template()
    input("\n按 Enter 继续下一个示例...")
    
    example_2_chat_prompt_template()
    input("\n按 Enter 继续下一个示例...")
    
    example_3_few_shot_prompting()
    input("\n按 Enter 继续下一个示例...")
    
    example_4_chat_few_shot()
    input("\n按 Enter 继续下一个示例...")
    
    example_5_output_parser()
    input("\n按 Enter 继续下一个示例...")
    
    example_6_prompt_composition()
    
    # 总结
    console.print("\n" + "=" * 60)
    console.print(Panel(
        """[bold green]🎉 教程完成！[/bold green]

[bold]核心要点回顾：[/bold]

1. [cyan]PromptTemplate[/cyan] - 简单场景，纯文本模板
2. [cyan]ChatPromptTemplate[/cyan] - 聊天场景，支持多角色
3. [cyan]Few-shot[/cyan] - 通过示例引导输出格式
4. [cyan]OutputParser[/cyan] - 将输出解析为结构化数据
5. [cyan]MessagesPlaceholder[/cyan] - 动态插入对话历史

[bold]下一步建议：[/bold]
- 尝试修改示例中的模板和参数
- 在 Jupyter Notebook 中交互式实验
- 进入 B1: 创建 ReAct Agent
""",
        title="学习总结",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
