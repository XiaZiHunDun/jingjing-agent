#!/usr/bin/env python3
"""
===========================================
D2: RAG 检索增强生成
===========================================

本教程介绍如何构建 RAG（Retrieval-Augmented Generation）系统：
1. 文档加载与分割
2. 向量化（Embedding）
3. 存储到向量数据库
4. 检索相关内容
5. 结合 LLM 生成回答
6. 集成为 Agent 工具

RAG 工作流程：
    文档 → 分割 → 向量化 → 存储
    查询 → 向量化 → 检索 → LLM 生成回答

运行方式:
    cd /home/ailearn/projects/agent-learn-2
    conda activate agent-learn
    python examples/03_rag_basics.py
"""

import os
import sys

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

# 项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(PROJECT_ROOT, "data", "docs")
CHROMA_DIR = os.path.join(PROJECT_ROOT, "data", "chroma_db")


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
# 第一部分：文档加载
# ============================================================

def load_documents():
    """
    加载文档
    
    LangChain 支持多种文档格式：
    - TextLoader: 纯文本文件
    - PyPDFLoader: PDF 文件
    - Docx2txtLoader: Word 文档
    - UnstructuredMarkdownLoader: Markdown 文件
    - DirectoryLoader: 批量加载目录下的文件
    """
    print_section("1. 文档加载", f"从 {DOCS_DIR} 加载文档")
    
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    
    # 使用 DirectoryLoader 加载目录下的所有 .md 文件
    loader = DirectoryLoader(
        DOCS_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    
    documents = loader.load()
    
    console.print(f"\n[green]✓ 成功加载 {len(documents)} 个文档[/green]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("文件名", style="cyan")
    table.add_column("字符数", style="green")
    table.add_column("预览", style="yellow")
    
    for doc in documents:
        filename = os.path.basename(doc.metadata.get("source", "unknown"))
        char_count = len(doc.page_content)
        preview = doc.page_content[:50].replace("\n", " ") + "..."
        table.add_row(filename, str(char_count), preview)
    
    console.print(table)
    
    return documents


# ============================================================
# 第二部分：文档分割
# ============================================================

def split_documents(documents):
    """
    将文档分割成小块（chunks）
    
    为什么需要分割？
    1. LLM 有 token 限制
    2. 小块更容易精确匹配
    3. 检索效果更好
    
    常用分割器：
    - RecursiveCharacterTextSplitter: 递归字符分割（推荐）
    - CharacterTextSplitter: 简单字符分割
    - MarkdownTextSplitter: Markdown 结构分割
    - TokenTextSplitter: 按 token 分割
    """
    print_section("2. 文档分割", "将长文档分割成小块")
    
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    # 创建分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,        # 每块最大字符数
        chunk_overlap=50,      # 块之间的重叠字符数（保持上下文连贯）
        length_function=len,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""]  # 分割优先级
    )
    
    # 分割文档
    chunks = text_splitter.split_documents(documents)
    
    console.print(f"\n[green]✓ 分割成 {len(chunks)} 个文本块[/green]")
    
    # 展示前几个块
    console.print("\n[yellow]示例文本块:[/yellow]")
    for i, chunk in enumerate(chunks[:3]):
        source = os.path.basename(chunk.metadata.get("source", "unknown"))
        console.print(Panel(
            chunk.page_content[:200] + "...",
            title=f"[cyan]块 {i+1}[/cyan] (来自 {source})",
            border_style="blue"
        ))
    
    return chunks


# ============================================================
# 第三部分：向量化与存储
# ============================================================

def create_vector_store(chunks):
    """
    创建向量存储
    
    流程：
    1. 使用 Embedding 模型将文本转为向量
    2. 将向量存储到向量数据库（ChromaDB）
    
    Embedding 模型选择：
    - OpenAI Embeddings: 效果好，需付费
    - HuggingFace: 免费，本地运行
    - Sentence Transformers: 专门针对语义相似度优化
    """
    print_section("3. 向量化与存储", "将文本转为向量并存储")
    
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    
    console.print("\n[yellow]正在加载 Embedding 模型...[/yellow]")
    console.print("[dim]首次运行需要下载模型，请耐心等待...[/dim]")
    
    # 使用 HuggingFace 的多语言模型
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    console.print("[green]✓ Embedding 模型加载成功[/green]")
    
    # 创建向量存储
    console.print("\n[yellow]正在创建向量数据库...[/yellow]")
    
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name="knowledge_base"
    )
    
    console.print(f"[green]✓ 向量数据库创建成功[/green]")
    console.print(f"[dim]存储位置: {CHROMA_DIR}[/dim]")
    
    return vector_store, embeddings


def load_existing_vector_store():
    """加载已存在的向量存储"""
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    vector_store = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name="knowledge_base"
    )
    
    return vector_store, embeddings


# ============================================================
# 第四部分：检索测试
# ============================================================

def test_retrieval(vector_store):
    """
    测试检索功能
    
    检索方式：
    - similarity_search: 相似度搜索
    - similarity_search_with_score: 带分数的搜索
    - max_marginal_relevance_search: MMR 搜索（多样性）
    """
    print_section("4. 检索测试", "测试向量检索效果")
    
    test_queries = [
        "Python 有哪些数据类型？",
        "什么是 LangChain？",
        "ReAct 模式是什么？",
        "如何定义 Python 函数？",
    ]
    
    for query in test_queries:
        console.print(f"\n[yellow]查询:[/yellow] {query}")
        
        # 检索相关文档
        results = vector_store.similarity_search_with_score(query, k=2)
        
        console.print("[green]检索结果:[/green]")
        for i, (doc, score) in enumerate(results, 1):
            source = os.path.basename(doc.metadata.get("source", "unknown"))
            content = doc.page_content[:100].replace("\n", " ")
            console.print(f"  {i}. [dim](相似度: {1-score:.2f})[/dim] [{source}]")
            console.print(f"     {content}...")


# ============================================================
# 第五部分：RAG 问答
# ============================================================

def create_rag_chain(vector_store):
    """
    创建 RAG 问答链
    
    RAG 流程：
    1. 用户提问
    2. 检索相关文档
    3. 将文档和问题一起发给 LLM
    4. LLM 基于文档生成回答
    """
    print_section("5. RAG 问答", "结合检索和 LLM 生成回答")
    
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    
    # 创建检索器
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}  # 返回最相关的 3 个文档
    )
    
    # RAG 提示词模板
    rag_prompt = ChatPromptTemplate.from_template("""
你是一个知识助手。请根据以下参考资料回答用户的问题。

参考资料：
{context}

用户问题：{question}

请基于参考资料回答，如果资料中没有相关信息，请明确说明。回答要简洁准确。
""")
    
    # 格式化检索结果
    def format_docs(docs):
        return "\n\n---\n\n".join([
            f"[来源: {os.path.basename(doc.metadata.get('source', 'unknown'))}]\n{doc.page_content}"
            for doc in docs
        ])
    
    # 创建 RAG 链
    llm = get_llm()
    
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | rag_prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain, retriever


def test_rag_qa(rag_chain, retriever):
    """测试 RAG 问答"""
    
    questions = [
        "Python 有哪些数据类型？请列举说明。",
        "LangChain 的核心组件有哪些？",
        "什么是 ReAct 模式？它是如何工作的？",
    ]
    
    for question in questions:
        console.print(f"\n[bold yellow]问题:[/bold yellow] {question}")
        
        # 显示检索到的文档
        docs = retriever.invoke(question)
        console.print(f"[dim]检索到 {len(docs)} 个相关文档块[/dim]")
        
        # 生成回答
        console.print("[yellow]生成回答中...[/yellow]")
        answer = rag_chain.invoke(question)
        
        console.print(Panel(
            answer,
            title="[green]RAG 回答[/green]",
            border_style="green"
        ))


# ============================================================
# 第六部分：创建 RAG 工具
# ============================================================

def create_rag_tool(vector_store):
    """
    将 RAG 封装为 Agent 工具
    
    这样 Agent 就可以使用知识库来回答问题了！
    """
    print_section("6. 创建 RAG 工具", "将 RAG 封装为 Agent 可调用的工具")
    
    from langchain_core.tools import tool
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    # 创建检索器
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    
    # RAG 提示词
    rag_prompt = ChatPromptTemplate.from_template("""
根据以下参考资料回答问题：

参考资料：
{context}

问题：{question}

请简洁准确地回答。
""")
    
    llm = get_llm()
    
    @tool
    def search_knowledge_base(query: str) -> str:
        """
        在本地知识库中搜索信息。可以搜索 Python、LangChain、Agent 等相关知识。
        
        Args:
            query: 搜索问题或关键词
        
        Returns:
            从知识库中检索到的相关信息和回答
        """
        # 检索相关文档
        docs = retriever.invoke(query)
        
        if not docs:
            return "未找到相关信息"
        
        # 格式化文档
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # 使用 LLM 生成回答
        chain = rag_prompt | llm | StrOutputParser()
        answer = chain.invoke({"context": context, "question": query})
        
        return answer
    
    console.print("[green]✓ RAG 工具创建成功[/green]")
    console.print(f"[dim]工具名称: {search_knowledge_base.name}[/dim]")
    console.print(f"[dim]工具描述: {search_knowledge_base.description[:60]}...[/dim]")
    
    return search_knowledge_base


# ============================================================
# 第七部分：Agent + RAG
# ============================================================

def create_agent_with_rag(rag_tool):
    """创建带有 RAG 工具的 Agent"""
    print_section("7. Agent + RAG", "将 RAG 工具集成到 Agent")
    
    import math
    import datetime
    from langchain_core.tools import tool
    from langchain.agents import create_agent
    from langchain_core.messages import HumanMessage
    
    # 添加其他工具
    @tool
    def calculator(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression, {"__builtins__": {}, "math": math})
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {e}"
    
    @tool
    def get_current_time() -> str:
        """获取当前时间"""
        now = datetime.datetime.now()
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    # 工具列表
    tools = [rag_tool, calculator, get_current_time]
    
    console.print("\n[yellow]已注册的工具:[/yellow]")
    for t in tools:
        console.print(f"  - [cyan]{t.name}[/cyan]: {t.description.split(chr(10))[0][:40]}...")
    
    # 创建 Agent
    llm = get_llm()
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="你是一个知识助手，可以使用知识库搜索、计算器等工具来回答问题。请使用中文回答。"
    )
    
    console.print("\n[green]✓ Agent + RAG 创建成功！[/green]")
    
    return agent


def test_agent_with_rag(agent):
    """测试带 RAG 的 Agent"""
    from langchain_core.messages import HumanMessage
    
    test_questions = [
        "Python 的列表和元组有什么区别？",
        "LangChain 中的 Memory 组件有什么作用？",
        "计算 15 * 24，然后告诉我现在几点",
    ]
    
    for question in test_questions:
        console.print(f"\n[bold yellow]问题:[/bold yellow] {question}")
        
        result = agent.invoke({"messages": [HumanMessage(content=question)]})
        answer = result["messages"][-1].content
        
        console.print(Panel(answer, title="[green]Agent 回答[/green]", border_style="green"))
        
        # 显示调用的工具
        for msg in result["messages"]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    console.print(f"  [dim]→ 调用工具: {tc['name']}[/dim]")


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold]D2: RAG 检索增强生成教程[/bold]\n"
        "构建本地知识库搜索系统",
        border_style="blue"
    ))
    
    console.print("""
[dim]RAG (Retrieval-Augmented Generation) 工作流程：

┌─────────────────────────────────────────────────────────┐
│  准备阶段                                                │
│  文档 ──→ 分割 ──→ 向量化 ──→ 存储到向量数据库          │
│                                                         │
│  查询阶段                                                │
│  问题 ──→ 向量化 ──→ 检索相似文档 ──→ LLM生成回答       │
└─────────────────────────────────────────────────────────┘
[/dim]
""")
    
    # 检查是否已有向量库
    if os.path.exists(CHROMA_DIR):
        console.print(f"[yellow]发现已存在的向量库: {CHROMA_DIR}[/yellow]")
        choice = input("是否重新构建？(y/n，默认 n): ").strip().lower()
        rebuild = choice == 'y'
    else:
        rebuild = True
    
    if rebuild:
        input("\n按 Enter 开始构建知识库...")
        
        # 1. 加载文档
        documents = load_documents()
        input("\n按 Enter 继续...")
        
        # 2. 分割文档
        chunks = split_documents(documents)
        input("\n按 Enter 继续...")
        
        # 3. 向量化与存储
        vector_store, embeddings = create_vector_store(chunks)
    else:
        console.print("\n[yellow]加载已有向量库...[/yellow]")
        vector_store, embeddings = load_existing_vector_store()
        console.print("[green]✓ 向量库加载成功[/green]")
    
    input("\n按 Enter 继续测试检索...")
    
    # 4. 测试检索
    test_retrieval(vector_store)
    
    input("\n按 Enter 继续测试 RAG 问答...")
    
    # 5. 创建并测试 RAG 链
    rag_chain, retriever = create_rag_chain(vector_store)
    test_rag_qa(rag_chain, retriever)
    
    input("\n按 Enter 继续创建 Agent 工具...")
    
    # 6. 创建 RAG 工具
    rag_tool = create_rag_tool(vector_store)
    
    input("\n按 Enter 继续测试 Agent + RAG...")
    
    # 7. 创建并测试 Agent
    agent = create_agent_with_rag(rag_tool)
    test_agent_with_rag(agent)
    
    # 总结
    console.print("\n" + "=" * 60)
    console.print(Panel(
        """[bold green]🎉 RAG 教程完成！[/bold green]

[bold]核心要点回顾：[/bold]

1. [cyan]文档加载[/cyan] - DirectoryLoader 批量加载文档
2. [cyan]文档分割[/cyan] - RecursiveCharacterTextSplitter 智能分割
3. [cyan]向量化[/cyan] - HuggingFace Embeddings 本地模型
4. [cyan]向量存储[/cyan] - ChromaDB 持久化存储
5. [cyan]检索[/cyan] - similarity_search 相似度搜索
6. [cyan]RAG 链[/cyan] - 检索 + LLM 生成回答
7. [cyan]RAG 工具[/cyan] - 封装为 Agent 可调用的工具

[bold]现在你的 Agent 拥有了真正的知识库搜索能力！[/bold]

[bold]下一步建议：[/bold]
- 添加更多文档到知识库
- D1: 添加对话记忆功能
- C1: 构建 Streamlit Web 界面
""",
        title="学习总结",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
