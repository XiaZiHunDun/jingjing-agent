#!/usr/bin/env python3
"""
===========================================
Agent Chat - 完整版 Web 界面
===========================================

功能：
- 💬 智能对话（带记忆）
- 🔧 工具调用（计算器、时间、知识库）
- 📚 RAG 知识库搜索
- 📄 文档上传（添加到知识库）
- 🔄 会话管理

启动方式：
    cd /home/ailearn/projects/agent-learn-2
    conda activate agent-learn
    streamlit run web/app.py --server.address 0.0.0.0 --server.port 8501

Windows 访问：
    http://<服务器IP>:8501
"""

import os
import sys
import math
import datetime
import warnings
import tempfile
import sqlite3
import json
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置代理
proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
if proxy:
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy

# 项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(PROJECT_ROOT, "data", "chroma_db")
DOCS_DIR = os.path.join(PROJECT_ROOT, "data", "docs")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "chat_history.db")


# ============================================================
# 数据库操作 - 对话历史持久化
# ============================================================

def init_database():
    """初始化数据库，创建表结构"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建对话历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            thinking_steps TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
        )
    ''')
    
    conn.commit()
    conn.close()


def save_session(session_id: str, messages: list, title: str = None):
    """保存对话到数据库"""
    if not messages:
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 自动生成标题（取第一条用户消息的前20字）
    if not title:
        for msg in messages:
            if msg.get("role") == "user":
                title = msg["content"][:20] + ("..." if len(msg["content"]) > 20 else "")
                break
        title = title or f"对话 {session_id}"
    
    # 更新或插入会话
    cursor.execute('''
        INSERT OR REPLACE INTO chat_sessions (session_id, title, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (session_id, title))
    
    # 删除旧消息，重新插入
    cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
    
    for msg in messages:
        thinking_steps = json.dumps(msg.get("thinking_steps", []), ensure_ascii=False) if msg.get("thinking_steps") else None
        cursor.execute('''
            INSERT INTO chat_messages (session_id, role, content, thinking_steps)
            VALUES (?, ?, ?, ?)
        ''', (session_id, msg["role"], msg["content"], thinking_steps))
    
    conn.commit()
    conn.close()


def load_session(session_id: str) -> list:
    """从数据库加载对话"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT role, content, thinking_steps FROM chat_messages
        WHERE session_id = ? ORDER BY id
    ''', (session_id,))
    
    messages = []
    for row in cursor.fetchall():
        msg = {"role": row[0], "content": row[1]}
        if row[2]:
            msg["thinking_steps"] = json.loads(row[2])
        messages.append(msg)
    
    conn.close()
    return messages


def get_all_sessions() -> list:
    """获取所有对话会话列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT session_id, title, updated_at,
               (SELECT COUNT(*) FROM chat_messages WHERE chat_messages.session_id = chat_sessions.session_id) as msg_count
        FROM chat_sessions
        ORDER BY updated_at DESC
        LIMIT 20
    ''')
    
    sessions = []
    for row in cursor.fetchall():
        sessions.append({
            "session_id": row[0],
            "title": row[1],
            "updated_at": row[2],
            "msg_count": row[3]
        })
    
    conn.close()
    return sessions


def delete_session(session_id: str):
    """删除对话会话"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
    cursor.execute('DELETE FROM chat_sessions WHERE session_id = ?', (session_id,))
    
    conn.commit()
    conn.close()


# 初始化数据库
init_database()

# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="🤖 Agent Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 获取当前主题
def get_theme_styles():
    """根据当前主题返回对应的 CSS 样式"""
    is_dark = st.session_state.get("dark_mode", False)
    
    if is_dark:
        # 深色模式
        return """
        <style>
            /* 深色模式基础样式 */
            .stApp {
                background-color: #1a1a2e !important;
            }
            .main-header {
                font-size: 2.5rem;
                font-weight: bold;
                background: linear-gradient(90deg, #a78bfa 0%, #f472b6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-align: center;
                padding: 1rem 0;
            }
            .tool-badge {
                display: inline-block;
                padding: 0.25rem 0.5rem;
                margin: 0.1rem;
                border-radius: 0.25rem;
                font-size: 0.8rem;
                background-color: #374151;
                color: #93c5fd;
            }
            .success-box {
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: #064e3b;
                border-left: 4px solid #10b981;
                margin: 1rem 0;
                color: #d1fae5;
            }
            .info-box {
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: #1e3a5f;
                border-left: 4px solid #3b82f6;
                margin: 1rem 0;
                color: #bfdbfe;
            }
            .stChatMessage {
                padding: 1rem;
            }
            /* 深色模式侧边栏 */
            [data-testid="stSidebar"] {
                background-color: #16213e !important;
            }
            [data-testid="stSidebar"] .stMarkdown {
                color: #e2e8f0 !important;
            }
            /* 深色模式文件上传 */
            [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::after {
                content: "📁 点击或拖拽文件 (TXT/MD/PDF/Word)";
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #374151;
                border: 2px dashed #6b7280;
                border-radius: 8px;
                color: #d1d5db;
                font-size: 14px;
                pointer-events: none;
                z-index: 1;
            }
            [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover::after {
                border-color: #a78bfa;
                color: #a78bfa;
            }
            /* 深色模式输入框 */
            .stTextInput input, .stTextArea textarea {
                background-color: #374151 !important;
                color: #f3f4f6 !important;
                border-color: #4b5563 !important;
            }
            /* 深色模式按钮 */
            .stButton > button {
                background-color: #4f46e5 !important;
                color: white !important;
            }
            .stButton > button:hover {
                background-color: #6366f1 !important;
            }
        </style>
        """
    else:
        # 浅色模式
        return """
        <style>
            .main-header {
                font-size: 2.5rem;
                font-weight: bold;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-align: center;
                padding: 1rem 0;
            }
            .tool-badge {
                display: inline-block;
                padding: 0.25rem 0.5rem;
                margin: 0.1rem;
                border-radius: 0.25rem;
                font-size: 0.8rem;
                background-color: #e3f2fd;
                color: #1565c0;
            }
            .success-box {
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: #e8f5e9;
                border-left: 4px solid #4caf50;
                margin: 1rem 0;
            }
            .info-box {
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
                margin: 1rem 0;
            }
            .stChatMessage {
                padding: 1rem;
            }
            /* 浅色模式文件上传 */
            [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::after {
                content: "📁 点击或拖拽文件 (TXT/MD/PDF/Word)";
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #fafafa;
                border: 2px dashed #ccc;
                border-radius: 8px;
                color: #666;
                font-size: 14px;
                pointer-events: none;
                z-index: 1;
            }
            [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover::after {
                border-color: #667eea;
                color: #667eea;
            }
        </style>
        """

# 自定义样式（旧版兼容，实际使用 get_theme_styles）
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .tool-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        margin: 0.1rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
        background-color: #e3f2fd;
        color: #1565c0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    .stChatMessage {
        padding: 1rem;
    }
    /* 文件上传组件 - 隐藏所有英文文本 */
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
        position: relative;
    }
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::after {
        content: "📁 点击或拖拽文件 (TXT/MD/PDF/Word)";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #fafafa;
        border: 2px dashed #ccc;
        border-radius: 8px;
        color: #666;
        font-size: 14px;
        pointer-events: none;
        z-index: 1;
    }
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover::after {
        border-color: #667eea;
        color: #667eea;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 初始化组件
# ============================================================

@st.cache_resource
def init_llm():
    """初始化 LLM"""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model="moonshot-v1-8k",
        openai_api_key=os.getenv("KIMI_API_KEY"),
        openai_api_base=os.getenv("KIMI_BASE_URL"),
        temperature=0.7,
    )


@st.cache_resource
def init_embeddings():
    """初始化 Embeddings"""
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        model_kwargs={'device': 'cpu'},
    )


def init_vector_store(force_reload=False):
    """初始化向量存储"""
    if not os.path.exists(CHROMA_DIR):
        return None
    
    try:
        from langchain_community.vectorstores import Chroma
        embeddings = init_embeddings()
        
        vector_store = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name='knowledge_base'
        )
        return vector_store
    except Exception as e:
        st.warning(f"知识库加载失败: {e}")
        return None


def get_agent():
    """获取 Agent（每次调用重新创建以获取最新知识库）"""
    from langchain_core.tools import tool
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain.agents import create_agent
    from langgraph.checkpoint.memory import MemorySaver
    
    llm = init_llm()
    vector_store = init_vector_store()
    
    # 定义工具
    @tool
    def calculator(expression: str) -> str:
        """
        计算数学表达式。支持加减乘除、幂运算、开方等。
        例如：2+3, 10*5, sqrt(16), 2**10, pi*2
        """
        try:
            expr = expression.replace("^", "**")
            expr = expr.replace("sqrt", "math.sqrt")
            expr = expr.replace("pi", "math.pi")
            result = eval(expr, {"__builtins__": {}, "math": math})
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    @tool
    def get_current_time() -> str:
        """获取当前日期和时间（北京时间）"""
        # 使用北京时区 (UTC+8)
        beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
        now = datetime.datetime.now(beijing_tz)
        weekdays = ['一', '二', '三', '四', '五', '六', '日']
        return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')} (星期{weekdays[now.weekday()]}，北京时间)"
    
    @tool
    def get_weather(city: str) -> str:
        """
        查询指定城市的天气信息。
        参数 city: 城市名称，如 "北京"、"上海"、"深圳"
        """
        import httpx
        
        # 使用 wttr.in 免费天气 API (使用 HTTP 更稳定)
        url = f"http://wttr.in/{city}?format=%l:+%c+%t+%h+%w&lang=zh"
        
        try:
            # 直接请求，不使用代理（wttr.in 可以直连）
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                response = client.get(url)
                if response.status_code == 200:
                    return f"🌤️ 天气查询结果:\n{response.text.strip()}"
                else:
                    return f"天气查询失败: HTTP {response.status_code}"
        except Exception as e:
            return f"天气查询错误: {str(e)}"
    
    @tool
    def fetch_webpage_summary(url: str) -> str:
        """
        获取网页内容并生成摘要。
        参数 url: 网页地址，如 "https://example.com"
        """
        import httpx
        import re
        try:
            # 配置代理
            proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
            headers = {"User-Agent": "Mozilla/5.0 (compatible; JingjingBot/1.0)"}
            
            with httpx.Client(proxy=proxy, timeout=15, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
            
            if response.status_code != 200:
                return f"网页获取失败: HTTP {response.status_code}"
            
            # 简单提取文本内容
            html = response.text
            # 移除 script 和 style
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
            # 移除 HTML 标签
            text = re.sub(r'<[^>]+>', ' ', html)
            # 清理空白
            text = re.sub(r'\s+', ' ', text).strip()
            
            # 截取前 2000 字符
            text = text[:2000] if len(text) > 2000 else text
            
            if not text:
                return "无法提取网页内容"
            
            # 使用 LLM 生成摘要
            summary_response = llm.invoke(f"请用中文简洁地总结以下网页内容（100-200字）:\n\n{text}")
            return f"📄 网页摘要:\n{summary_response.content}"
        except Exception as e:
            return f"网页摘要错误: {str(e)}"
    
    @tool
    def translate(text: str, target_language: str = "英文") -> str:
        """
        翻译文本。
        参数 text: 要翻译的文本
        参数 target_language: 目标语言，默认为"英文"，也可以是"中文"、"日文"等
        """
        try:
            response = llm.invoke(f"请将以下文本翻译成{target_language}，只返回翻译结果，不要添加解释:\n\n{text}")
            return f"🌐 翻译结果 ({target_language}):\n{response.content}"
        except Exception as e:
            return f"翻译错误: {str(e)}"
    
    tools = [calculator, get_current_time, get_weather, fetch_webpage_summary, translate]
    
    # 如果有知识库，添加 RAG 工具
    if vector_store is not None:
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        rag_prompt = ChatPromptTemplate.from_template(
            "根据以下资料回答问题：\n\n{context}\n\n问题：{question}\n\n请基于资料回答，如果资料中没有相关信息，请说明。"
        )
        
        @tool
        def search_knowledge_base(query: str) -> str:
            """
            在本地知识库中搜索信息。知识库包含 Python、LangChain、Agent 等技术文档。
            当用户询问技术问题时，请使用此工具搜索相关信息。
            """
            try:
                docs = retriever.invoke(query)
                if not docs:
                    return "未找到相关信息"
                context = "\n\n---\n\n".join([doc.page_content for doc in docs])
                chain = rag_prompt | llm | StrOutputParser()
                return chain.invoke({"context": context, "question": query})
            except Exception as e:
                return f"搜索错误: {str(e)}"
        
        tools.append(search_knowledge_base)
    
    # 创建带记忆的 Agent
    if "memory" not in st.session_state:
        st.session_state.memory = MemorySaver()
    
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="""你是一个智能助手，名叫 "晶晶"。你可以：

1. 💬 进行友好的对话
2. 🔢 使用计算器进行数学计算
3. ⏰ 查询当前时间
4. 📚 搜索知识库获取技术信息
5. 🌤️ 查询城市天气
6. 📄 获取网页摘要
7. 🌐 翻译文本（支持多语言）

请用中文回答，保持友好和专业。如果需要使用工具，请先使用工具获取信息再回答。""",
        checkpointer=st.session_state.memory,
    )
    
    return agent, tools


# ============================================================
# 对话导出功能
# ============================================================

def export_chat_to_markdown(messages: list, session_id: str) -> str:
    """将对话导出为 Markdown 格式"""
    lines = [
        f"# 晶晶助手 - 对话记录",
        f"",
        f"**会话 ID**: {session_id}",
        f"**导出时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**消息数量**: {len(messages)}",
        f"",
        f"---",
        f"",
    ]
    
    for msg in messages:
        role = "🧑 **用户**" if msg["role"] == "user" else "🤖 **晶晶**"
        lines.append(f"{role}")
        lines.append(f"")
        lines.append(f"{msg['content']}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
    
    return "\n".join(lines)


def export_chat_to_json(messages: list, session_id: str) -> str:
    """将对话导出为 JSON 格式"""
    import json
    data = {
        "session_id": session_id,
        "export_time": datetime.datetime.now().isoformat(),
        "message_count": len(messages),
        "messages": messages
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================
# 文档上传功能
# ============================================================

def extract_text_from_pdf(file_bytes) -> str:
    """从 PDF 文件提取文本"""
    from pypdf import PdfReader
    import io
    
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise Exception(f"PDF 解析失败: {str(e)}")


def extract_text_from_docx(file_bytes) -> str:
    """从 Word 文件提取文本"""
    from docx import Document
    import io
    
    try:
        docx_file = io.BytesIO(file_bytes)
        doc = Document(docx_file)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise Exception(f"Word 文档解析失败: {str(e)}")


def add_document_to_knowledge_base(content: str, filename: str):
    """添加文档到知识库"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    from langchain_core.documents import Document
    
    try:
        embeddings = init_embeddings()
        
        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )
        
        doc = Document(page_content=content, metadata={"source": filename})
        chunks = text_splitter.split_documents([doc])
        
        # 添加到向量库
        if os.path.exists(CHROMA_DIR):
            vector_store = Chroma(
                persist_directory=CHROMA_DIR,
                embedding_function=embeddings,
                collection_name='knowledge_base'
            )
            vector_store.add_documents(chunks)
        else:
            os.makedirs(CHROMA_DIR, exist_ok=True)
            Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=CHROMA_DIR,
                collection_name='knowledge_base'
            )
        
        return True, f"成功添加 {len(chunks)} 个文档块"
    except Exception as e:
        return False, str(e)


# ============================================================
# 侧边栏
# ============================================================

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # 主题切换
        col_title, col_theme = st.columns([3, 1])
        with col_title:
            st.markdown('<p class="main-header">🤖 晶晶助手</p>', unsafe_allow_html=True)
        with col_theme:
            # 初始化深色模式状态
            if "dark_mode" not in st.session_state:
                st.session_state.dark_mode = False
            
            # 主题切换按钮
            theme_icon = "🌙" if not st.session_state.dark_mode else "☀️"
            if st.button(theme_icon, key="theme_toggle", help="切换深色/浅色模式"):
                st.session_state.dark_mode = not st.session_state.dark_mode
                st.rerun()
        
        st.markdown("---")
        
        # 会话管理
        st.subheader("💬 会话管理")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 新会话", use_container_width=True):
                st.session_state.messages = []
                st.session_state.session_id = f"s_{datetime.datetime.now().strftime('%H%M%S')}"
                if "memory" in st.session_state:
                    del st.session_state.memory
                st.rerun()
        
        with col2:
            if st.button("🗑️ 清空", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        st.caption(f"会话 ID: `{st.session_state.get('session_id', 'default')}`")
        
        # 导出对话
        if st.session_state.get("messages"):
            st.markdown("**📥 导出对话**")
            export_col1, export_col2 = st.columns(2)
            
            session_id = st.session_state.get('session_id', 'default')
            
            with export_col1:
                md_content = export_chat_to_markdown(st.session_state.messages, session_id)
                st.download_button(
                    label="📝 Markdown",
                    data=md_content,
                    file_name=f"chat_{session_id}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with export_col2:
                json_content = export_chat_to_json(st.session_state.messages, session_id)
                st.download_button(
                    label="📋 JSON",
                    data=json_content,
                    file_name=f"chat_{session_id}.json",
                    mime="application/json",
                    use_container_width=True
                )
        
        st.markdown("---")
        
        # 可用工具
        st.subheader("🛠️ 可用工具")
        
        tools_info = [
            ("🔢 计算器", "数学计算"),
            ("⏰ 时间", "获取当前时间"),
            ("🌤️ 天气", "查询城市天气"),
            ("📄 网页", "获取网页摘要"),
            ("🌐 翻译", "多语言翻译"),
            ("📚 知识库", "搜索技术文档"),
        ]
        
        for icon_name, desc in tools_info:
            st.markdown(f"<span class='tool-badge'>{icon_name}</span> {desc}", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 文档上传
        st.subheader("📄 添加知识")
        st.caption("支持 TXT、MD、PDF、Word 文件")
        
        uploaded_file = st.file_uploader(
            "选择文件",
            type=['txt', 'md', 'pdf', 'docx'],
            help="支持 .txt .md .pdf .docx 格式",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            # 显示文件信息
            file_size = len(uploaded_file.getvalue()) / 1024  # KB
            st.caption(f"📎 {uploaded_file.name} ({file_size:.1f} KB)")
            
            if st.button("📥 添加到知识库", use_container_width=True):
                with st.spinner("处理中..."):
                    try:
                        file_bytes = uploaded_file.getvalue()
                        file_ext = uploaded_file.name.lower().split('.')[-1]
                        
                        # 根据文件类型提取文本
                        if file_ext == 'pdf':
                            content = extract_text_from_pdf(file_bytes)
                        elif file_ext == 'docx':
                            content = extract_text_from_docx(file_bytes)
                        else:  # txt, md
                            content = file_bytes.decode('utf-8')
                        
                        if not content.strip():
                            st.error("❌ 文件内容为空")
                        else:
                            success, msg = add_document_to_knowledge_base(content, uploaded_file.name)
                            
                            if success:
                                st.success(f"✅ {msg}")
                                # 保存原文件到 docs 目录
                                os.makedirs(DOCS_DIR, exist_ok=True)
                                save_path = os.path.join(DOCS_DIR, uploaded_file.name)
                                with open(save_path, 'wb') as f:
                                    f.write(file_bytes)
                            else:
                                st.error(f"❌ 添加失败: {msg}")
                    except Exception as e:
                        st.error(f"❌ 文件处理失败: {str(e)}")
        
        st.markdown("---")
        
        # 历史记录
        st.subheader("📜 历史记录")
        
        sessions = get_all_sessions()
        if sessions:
            for sess in sessions[:5]:  # 只显示最近5条
                col_title, col_del = st.columns([4, 1])
                with col_title:
                    # 点击加载历史对话
                    btn_label = f"📄 {sess['title']}"
                    if st.button(btn_label, key=f"load_{sess['session_id']}", use_container_width=True):
                        # 加载历史对话
                        st.session_state.messages = load_session(sess['session_id'])
                        st.session_state.session_id = sess['session_id']
                        if "memory" in st.session_state:
                            del st.session_state.memory
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{sess['session_id']}"):
                        delete_session(sess['session_id'])
                        st.rerun()
            
            if len(sessions) > 5:
                st.caption(f"还有 {len(sessions) - 5} 条更早的记录...")
        else:
            st.caption("暂无历史记录")
        
        st.markdown("---")
        
        # 显示设置
        st.subheader("⚙️ 显示设置")
        
        # 初始化流式输出状态
        if "stream_output" not in st.session_state:
            st.session_state.stream_output = True
        
        st.session_state.stream_output = st.toggle(
            "🌊 流式输出", 
            value=st.session_state.stream_output,
            help="开启后回答将逐字显示，关闭则一次性显示"
        )
        
        st.markdown("---")
        
        # 系统信息
        st.subheader("ℹ️ 系统状态")
        
        vector_store = init_vector_store()
        kb_status = "✅ 已加载" if vector_store else "❌ 未加载"
        
        st.markdown(f"""
        - **LLM**: Kimi API
        - **知识库**: {kb_status}
        - **记忆**: ✅ 已启用
        - **历史**: ✅ 已持久化
        """)
        
        st.markdown("---")
        st.caption("Agent Learn 2 项目 | 2026")


# ============================================================
# 主聊天界面
# ============================================================

def render_chat():
    """渲染聊天界面"""
    
    # 应用主题样式
    st.markdown(get_theme_styles(), unsafe_allow_html=True)
    
    # 根据主题调整标题颜色
    is_dark = st.session_state.get("dark_mode", False)
    subtitle_color = "#a1a1aa" if is_dark else "#666"
    
    # 标题
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem 0;">
        <h1>💬 智能助手对话</h1>
        <p style="color: {subtitle_color};">我是晶晶，可以帮你计算、查询时间、搜索知识库</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化会话状态
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = "default"
    
    # 快捷问题
    st.markdown("**💡 试试这些问题：**")
    quick_questions = [
        "北京天气怎么样？",
        "计算 123 * 456",
        "把'你好世界'翻译成英文",
        "什么是 LangChain？",
    ]
    
    cols = st.columns(len(quick_questions))
    for i, q in enumerate(quick_questions):
        if cols[i].button(q, key=f"quick_{i}", use_container_width=True):
            st.session_state.quick_question = q
            st.rerun()
    
    st.markdown("---")
    
    # 显示历史消息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # 显示思考过程（新格式）
            if "thinking_steps" in message and message["thinking_steps"]:
                with st.expander("🧠 思考过程", expanded=False):
                    for i, step in enumerate(message["thinking_steps"], 1):
                        st.markdown(f"**步骤 {i}**: `{step['name']}`")
                        args_str = ", ".join([f"{k}={v}" for k, v in step['args'].items()]) if isinstance(step['args'], dict) else str(step['args'])
                        st.caption(f"📥 {args_str}")
                        if "result" in step:
                            result_preview = step["result"][:100] + "..." if len(step["result"]) > 100 else step["result"]
                            st.caption(f"📤 {result_preview}")
            
            # 兼容旧格式
            elif "tool_calls" in message and message["tool_calls"]:
                with st.expander("🔧 工具调用", expanded=False):
                    for tc in message["tool_calls"]:
                        st.code(f"{tc['name']}: {tc.get('args', '')}", language="")
    
    # 处理快捷问题
    if "quick_question" in st.session_state:
        prompt = st.session_state.quick_question
        del st.session_state.quick_question
        process_message(prompt)
    
    # 聊天输入
    if prompt := st.chat_input("请输入您的问题..."):
        process_message(prompt)


def process_message(prompt: str):
    """处理用户消息"""
    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)
    
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })
    
    # 调用 Agent
    with st.chat_message("assistant"):
        # 创建思考过程占位符
        thinking_placeholder = st.empty()
        answer_placeholder = st.empty()
        
        try:
            from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
            
            agent, _ = get_agent()
            config = {"configurable": {"thread_id": st.session_state.session_id}}
            
            # 显示思考中
            thinking_placeholder.info("🤔 正在思考...")
            
            result = agent.invoke(
                {"messages": [HumanMessage(content=prompt)]},
                config=config
            )
            
            # 获取回复
            answer = result["messages"][-1].content
            
            # 收集本次回复的思考过程（只处理最后一轮对话）
            thinking_steps = []
            tool_results = {}
            
            # 找到最后一个用户消息的位置，只处理之后的消息
            last_human_idx = 0
            for i, msg in enumerate(result["messages"]):
                if hasattr(msg, 'content') and isinstance(msg, HumanMessage):
                    last_human_idx = i
            
            # 只处理最后一个用户消息之后的消息
            for msg in result["messages"][last_human_idx + 1:]:
                # AI 决定调用工具
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_name = tc["name"]
                        tool_args = tc.get("args", {})
                        thinking_steps.append({
                            "type": "tool_call",
                            "name": tool_name,
                            "args": tool_args,
                            "id": tc.get("id", "")
                        })
                
                # 工具返回结果
                if isinstance(msg, ToolMessage):
                    tool_results[msg.tool_call_id] = msg.content
            
            # 匹配工具调用和结果
            for step in thinking_steps:
                if step.get("id") in tool_results:
                    step["result"] = tool_results[step["id"]]
            
            # 清除思考中提示
            thinking_placeholder.empty()
            
            # 显示思考过程（如果有工具调用）
            if thinking_steps:
                with st.expander("🧠 思考过程", expanded=True):
                    for i, step in enumerate(thinking_steps, 1):
                        st.markdown(f"**步骤 {i}**: 调用工具 `{step['name']}`")
                        
                        # 显示参数
                        args_str = ", ".join([f"{k}={v}" for k, v in step['args'].items()]) if isinstance(step['args'], dict) else str(step['args'])
                        st.code(f"📥 输入: {args_str}", language="")
                        
                        # 显示结果
                        if "result" in step:
                            result_preview = step["result"][:200] + "..." if len(step["result"]) > 200 else step["result"]
                            st.code(f"📤 输出: {result_preview}", language="")
                        
                        if i < len(thinking_steps):
                            st.markdown("---")
            
            # 显示最终回复（支持流式/非流式）
            if st.session_state.get("stream_output", True):
                # 流式显示
                import time
                displayed_text = ""
                
                # 逐字显示效果
                for char in answer:
                    displayed_text += char
                    answer_placeholder.markdown(displayed_text + "▌")  # 显示光标
                    time.sleep(0.015)  # 控制速度，15ms 每字符
                
                # 移除光标，显示完整内容
                answer_placeholder.markdown(answer)
            else:
                # 直接显示
                answer_placeholder.markdown(answer)
            
            # 保存到历史
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "thinking_steps": thinking_steps
            })
            
            # 自动保存到数据库
            save_session(st.session_state.session_id, st.session_state.messages)
            
        except Exception as e:
            thinking_placeholder.empty()
            error_msg = f"❌ 发生错误: {str(e)}"
            answer_placeholder.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })
            # 保存错误消息
            save_session(st.session_state.session_id, st.session_state.messages)


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
