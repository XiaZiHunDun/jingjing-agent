#!/usr/bin/env python3
"""
===========================================
Agent Chat - 完整版 Web 界面（模块化重构版）
===========================================

功能：
- 智能对话（带记忆）
- 工具调用（计算器、时间、知识库）
- RAG 知识库搜索
- 文档上传（添加到知识库）
- 会话管理

启动方式：
    cd /home/ailearn/projects/agent-learn-2
    conda activate agent-learn
    streamlit run web/app.py --server.address 0.0.0.0 --server.port 8501

Windows 访问：
    http://<服务器IP>:8501
"""

import os
import sys
import datetime
import warnings
import json
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入模块化组件
from src.utils.config import Config
from src.llm import get_llm, get_current_provider, set_provider, get_provider_info
from src.llm.ollama import check_ollama_available
from src.memory.vector_store import (
    get_embeddings, 
    get_vector_store, 
    add_documents_to_store,
    create_rag_tool,
    get_all_documents,
    delete_document
)
from src.db.chat_history import (
    init_database,
    save_session,
    load_session,
    get_all_sessions,
    delete_session
)
from src.tools import get_basic_tools

# 初始化数据库
init_database()


# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="晶晶助手",
    page_icon="robot",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
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
</style>
""", unsafe_allow_html=True)


# ============================================================
# 初始化组件（使用缓存）
# ============================================================

def init_llm():
    """初始化 LLM（不缓存，支持动态切换）"""
    return get_llm()


@st.cache_resource
def init_embeddings():
    """初始化 Embeddings"""
    return get_embeddings()


def init_vector_store_cached():
    """初始化向量存储"""
    return get_vector_store()


def get_agent():
    """获取 Agent（每次调用重新创建以获取最新知识库）"""
    from langchain.agents import create_agent
    from langgraph.checkpoint.memory import MemorySaver
    from src.agent.jingjing import JINGJING_SYSTEM_PROMPT
    
    llm = init_llm()
    vector_store = init_vector_store_cached()
    
    # 获取基础工具
    tools = get_basic_tools()
    
    # 如果有知识库，添加 RAG 工具
    if vector_store is not None:
        rag_tool = create_rag_tool(vector_store)
        tools.append(rag_tool)
    
    # 创建带记忆的 Agent
    if "memory" not in st.session_state:
        st.session_state.memory = MemorySaver()
    
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=JINGJING_SYSTEM_PROMPT,
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
        role = "用户" if msg["role"] == "user" else "晶晶"
        lines.append(f"**{role}**")
        lines.append(f"")
        lines.append(f"{msg['content']}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
    
    return "\n".join(lines)


def export_chat_to_json(messages: list, session_id: str) -> str:
    """将对话导出为 JSON 格式"""
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


# ============================================================
# 侧边栏
# ============================================================

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown('<p class="main-header">晶晶助手</p>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 模型选择
        st.subheader("模型选择")
        
        current_provider = get_current_provider().value
        ollama_available = check_ollama_available()
        
        # 模型选项
        model_options = ["ollama", "kimi"]
        model_labels = {
            "ollama": "本地模型 (Qwen3-8B)",
            "kimi": "云端模型 (Kimi API)"
        }
        
        # 当前选中的索引
        current_index = model_options.index(current_provider) if current_provider in model_options else 0
        
        selected = st.radio(
            "选择模型",
            model_options,
            index=current_index,
            format_func=lambda x: model_labels.get(x, x),
            label_visibility="collapsed"
        )
        
        # 显示模型状态
        if selected == "ollama":
            if ollama_available:
                st.success("本地模型运行中", icon="✅")
            else:
                st.error("本地模型不可用", icon="❌")
        else:
            st.info("使用云端 API", icon="☁️")
        
        # 切换模型
        if selected != current_provider:
            if selected == "ollama" and not ollama_available:
                st.warning("Ollama 服务未启动，无法切换")
            else:
                if set_provider(selected):
                    # 清除 Agent 缓存
                    if "memory" in st.session_state:
                        del st.session_state.memory
                    st.success(f"已切换到 {model_labels[selected]}")
                    st.rerun()
        
        st.markdown("---")
        
        # 会话管理
        st.subheader("会话管理")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("新会话", use_container_width=True):
                st.session_state.messages = []
                st.session_state.session_id = f"s_{datetime.datetime.now().strftime('%H%M%S')}"
                if "memory" in st.session_state:
                    del st.session_state.memory
                st.rerun()
        
        with col2:
            if st.button("清空", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        st.caption(f"会话 ID: `{st.session_state.get('session_id', 'default')}`")
        
        # 导出对话
        if st.session_state.get("messages"):
            st.markdown("**导出对话**")
            export_col1, export_col2 = st.columns(2)
            
            session_id = st.session_state.get('session_id', 'default')
            
            with export_col1:
                md_content = export_chat_to_markdown(st.session_state.messages, session_id)
                st.download_button(
                    label="Markdown",
                    data=md_content,
                    file_name=f"chat_{session_id}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with export_col2:
                json_content = export_chat_to_json(st.session_state.messages, session_id)
                st.download_button(
                    label="JSON",
                    data=json_content,
                    file_name=f"chat_{session_id}.json",
                    mime="application/json",
                    use_container_width=True
                )
        
        st.markdown("---")
        
        # 可用工具
        st.subheader("可用工具")
        
        tools_info = [
            ("计算器", "数学计算"),
            ("时间", "获取当前时间"),
            ("天气", "查询城市天气"),
            ("网页", "获取网页摘要"),
            ("翻译", "多语言翻译"),
            ("知识库", "搜索技术文档"),
        ]
        
        for icon_name, desc in tools_info:
            st.markdown(f"<span class='tool-badge'>{icon_name}</span> {desc}", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 文档上传
        st.subheader("添加知识")
        st.caption("支持 TXT、MD、PDF、Word 文件")
        
        uploaded_file = st.file_uploader(
            "选择文件",
            type=['txt', 'md', 'pdf', 'docx'],
            help="支持 .txt .md .pdf .docx 格式",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            file_size = len(uploaded_file.getvalue()) / 1024
            st.caption(f"文件: {uploaded_file.name} ({file_size:.1f} KB)")
            
            if st.button("添加到知识库", use_container_width=True):
                with st.spinner("处理中..."):
                    try:
                        file_bytes = uploaded_file.getvalue()
                        file_ext = uploaded_file.name.lower().split('.')[-1]
                        
                        if file_ext == 'pdf':
                            content = extract_text_from_pdf(file_bytes)
                        elif file_ext == 'docx':
                            content = extract_text_from_docx(file_bytes)
                        else:
                            content = file_bytes.decode('utf-8')
                        
                        if not content.strip():
                            st.error("文件内容为空")
                        else:
                            success, msg = add_documents_to_store(content, uploaded_file.name)
                            
                            if success:
                                st.success(f"成功: {msg}")
                                # 保存原文件
                                Config.ensure_dirs()
                                save_path = Config.DOCS_DIR / uploaded_file.name
                                with open(save_path, 'wb') as f:
                                    f.write(file_bytes)
                            else:
                                st.error(f"失败: {msg}")
                    except Exception as e:
                        st.error(f"文件处理失败: {str(e)}")
        
        st.markdown("---")
        
        # 历史记录
        st.subheader("历史记录")
        
        sessions = get_all_sessions()
        if sessions:
            for sess in sessions[:5]:
                col_title, col_del = st.columns([4, 1])
                with col_title:
                    btn_label = f"{sess['title']}"
                    if st.button(btn_label, key=f"load_{sess['session_id']}", use_container_width=True):
                        st.session_state.messages = load_session(sess['session_id'])
                        st.session_state.session_id = sess['session_id']
                        if "memory" in st.session_state:
                            del st.session_state.memory
                        st.rerun()
                with col_del:
                    if st.button("X", key=f"del_{sess['session_id']}"):
                        delete_session(sess['session_id'])
                        st.rerun()
            
            if len(sessions) > 5:
                st.caption(f"还有 {len(sessions) - 5} 条更早的记录...")
        else:
            st.caption("暂无历史记录")
        
        st.markdown("---")
        
        # 知识库文档管理
        st.subheader("知识库文档")
        
        kb_docs = get_all_documents()
        if kb_docs:
            st.caption(f"共 {len(kb_docs)} 个文档")
            
            for doc in kb_docs:
                col_name, col_info, col_del = st.columns([3, 1, 1])
                with col_name:
                    st.markdown(f"📄 `{doc['source']}`")
                with col_info:
                    st.caption(f"{doc['chunk_count']}块")
                with col_del:
                    if st.button("🗑️", key=f"del_doc_{doc['source']}", help=f"删除 {doc['source']}"):
                        success, msg = delete_document(doc['source'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.caption("暂无文档，请上传")
        
        st.markdown("---")
        
        # 系统信息
        st.subheader("系统状态")
        
        vector_store = init_vector_store_cached()
        kb_status = "已加载" if vector_store else "未加载"
        doc_count = len(kb_docs) if kb_docs else 0
        
        # 获取当前模型信息
        provider_info = get_provider_info()
        model_name = provider_info.get("model", "未知")
        if len(model_name) > 20:
            model_name = model_name.split("/")[-1][:20] + "..."
        
        st.markdown(f"""
        - **LLM**: {provider_info['provider'].upper()}
        - **模型**: {model_name}
        - **知识库**: {kb_status} ({doc_count} 文档)
        - **记忆**: 已启用
        """)
        
        st.markdown("---")
        st.caption("Agent Learn 2 项目 | 2026")


# ============================================================
# 主聊天界面
# ============================================================

def render_chat():
    """渲染聊天界面"""
    
    # 标题
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h1>智能助手对话</h1>
        <p style="color: #666;">我是晶晶，可以帮你计算、查询时间、搜索知识库</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化会话状态
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = "default"
    
    # 快捷问题
    st.markdown("**试试这些问题：**")
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
            
            if "thinking_steps" in message and message["thinking_steps"]:
                with st.expander("思考过程", expanded=False):
                    for i, step in enumerate(message["thinking_steps"], 1):
                        st.markdown(f"**步骤 {i}**: `{step['name']}`")
                        args_str = ", ".join([f"{k}={v}" for k, v in step['args'].items()]) if isinstance(step['args'], dict) else str(step['args'])
                        st.caption(f"输入: {args_str}")
                        if "result" in step:
                            result_preview = step["result"][:100] + "..." if len(step["result"]) > 100 else step["result"]
                            st.caption(f"输出: {result_preview}")
    
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
    from langchain_core.messages import HumanMessage, ToolMessage
    
    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)
    
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })
    
    # 调用 Agent
    with st.chat_message("assistant"):
        thinking_placeholder = st.empty()
        answer_placeholder = st.empty()
        
        try:
            agent, _ = get_agent()
            config = {"configurable": {"thread_id": st.session_state.session_id}}
            
            thinking_placeholder.info("正在思考...")
            
            result = agent.invoke(
                {"messages": [HumanMessage(content=prompt)]},
                config=config
            )
            
            answer = result["messages"][-1].content
            
            # 收集思考过程
            thinking_steps = []
            tool_results = {}
            
            last_human_idx = 0
            for i, msg in enumerate(result["messages"]):
                if hasattr(msg, 'content') and isinstance(msg, HumanMessage):
                    last_human_idx = i
            
            for msg in result["messages"][last_human_idx + 1:]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        thinking_steps.append({
                            "type": "tool_call",
                            "name": tc["name"],
                            "args": tc.get("args", {}),
                            "id": tc.get("id", "")
                        })
                
                if isinstance(msg, ToolMessage):
                    tool_results[msg.tool_call_id] = msg.content
            
            for step in thinking_steps:
                if step.get("id") in tool_results:
                    step["result"] = tool_results[step["id"]]
            
            thinking_placeholder.empty()
            
            # 显示思考过程
            if thinking_steps:
                with st.expander("思考过程", expanded=True):
                    for i, step in enumerate(thinking_steps, 1):
                        st.markdown(f"**步骤 {i}**: 调用工具 `{step['name']}`")
                        args_str = ", ".join([f"{k}={v}" for k, v in step['args'].items()]) if isinstance(step['args'], dict) else str(step['args'])
                        st.code(f"输入: {args_str}", language="")
                        if "result" in step:
                            result_preview = step["result"][:200] + "..." if len(step["result"]) > 200 else step["result"]
                            st.code(f"输出: {result_preview}", language="")
                        if i < len(thinking_steps):
                            st.markdown("---")
            
            # 显示最终回复
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
            error_msg = f"发生错误: {str(e)}"
            answer_placeholder.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })
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
