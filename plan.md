# 智能体(Agent)开发计划

## 1. 项目概述

### 1.1 项目目标
构建一个功能完善的智能体系统，能够：
- 理解用户意图并分解复杂任务
- 自主规划执行步骤
- 调用工具完成具体操作
- 具备记忆和学习能力
- 支持多轮对话和上下文理解

### 1.2 开发与部署环境

#### 开发阶段
```
┌─────────────────┐      SSH       ┌─────────────────────┐
│  Windows 主机   │ ◄───────────► │   Linux 虚拟机       │
│  (MobaXterm)    │               │   (开发/运行环境)    │
└─────────────────┘               └──────────┬──────────┘
                                             │ 代理
                                             ▼
                                  ┌─────────────────────┐
                                  │      外部网络        │
                                  │  (Kimi API 等)      │
                                  └─────────────────────┘
```

#### 部署阶段（Windows 访问 Agent）
```
┌─────────────────────┐                    ┌─────────────────────────────┐
│    Windows 主机     │                    │       Linux 虚拟机           │
│                     │   HTTP (端口8000)  │                             │
│  ┌───────────────┐  │ ◄───────────────► │  ┌───────────────────────┐  │
│  │ 浏览器/客户端  │  │                    │  │  Agent Web Service    │  │
│  │ localhost:8000│  │                    │  │  (FastAPI/Streamlit)  │  │
│  └───────────────┘  │                    │  └───────────┬───────────┘  │
└─────────────────────┘                    │              │              │
                                           │              ▼              │
                                           │  ┌───────────────────────┐  │
                                           │  │    Agent Core         │  │
                                           │  │  (LangChain/LangGraph)│  │
                                           │  └───────────┬───────────┘  │
                                           │              │ 代理         │
                                           └──────────────┼──────────────┘
                                                          ▼
                                           ┌─────────────────────────────┐
                                           │      Kimi API (外网)        │
                                           └─────────────────────────────┘
```

| 资源 | 说明 |
|------|------|
| **Linux 虚拟机** | Agent 运行环境，提供 Web 服务 |
| **Windows 主机** | 通过浏览器访问 Agent Web UI |
| **代理链接** | Linux 访问外网（Kimi API） |
| **Kimi API Key** | LLM 服务提供商 |
| **网络端口** | 8000（FastAPI）或 8501（Streamlit） |

### 1.3 技术栈选择
- **编程语言**: Python 3.10+
- **LLM接口**: Kimi API（Moonshot AI，兼容 OpenAI 接口）
- **Agent框架**: LangChain + LangGraph（主流生产级框架）
- **Web服务**: FastAPI（后端API）+ Streamlit/Gradio（前端UI）
- **向量数据库**: ChromaDB / FAISS（用于长期记忆）
- **开发环境**: Linux 虚拟机
- **访问方式**: Windows 浏览器访问 Linux Web 服务

---

## 2. 核心架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户接口层                            │
│                  (CLI / Web UI / API)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      Agent 核心层                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   感知模块   │  │   决策模块   │  │      执行模块       │  │
│  │  (Parser)   │  │  (Planner)  │  │    (Executor)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                       基础设施层                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  LLM API │  │ 工具注册  │  │ 记忆系统  │  │  配置管理  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块说明

| 模块 | 职责 | 关键功能 |
|------|------|----------|
| 感知模块 | 理解输入 | 意图识别、实体抽取、上下文理解 |
| 决策模块 | 任务规划 | 目标分解、步骤规划、策略选择 |
| 执行模块 | 操作执行 | 工具调用、结果处理、异常恢复 |
| 记忆系统 | 信息存储 | 短期记忆、长期记忆、知识检索 |
| 工具系统 | 能力扩展 | 工具注册、参数验证、调用封装 |

---

## 3. 详细设计

### 3.1 核心循环（Agent Loop）

```
┌──────────────────────────────────────────────────────────┐
│                     Agent 主循环                          │
│                                                          │
│   用户输入 ──► 感知理解 ──► 任务规划 ──► 执行动作 ──┐     │
│       ▲                                           │     │
│       │           ◄── 结果评估 ◄── 观察结果 ◄─────┘     │
│       │                   │                             │
│       └───────────────────┴─── 完成/继续 ───────────────┘
└──────────────────────────────────────────────────────────┘
```

### 3.2 记忆系统设计

#### 短期记忆（Working Memory）
- 当前会话的对话历史
- 当前任务的执行状态
- 临时变量和中间结果

#### 长期记忆（Long-term Memory）
- 用户偏好和历史交互
- 成功的任务执行模式
- 知识库和文档索引

### 3.3 工具系统设计（LangChain）

```python
from langchain.tools import tool, StructuredTool
from pydantic import BaseModel, Field

# 方式1: @tool 装饰器（简单工具）
@tool
def read_file(file_path: str) -> str:
    """读取指定路径的文件内容"""
    with open(file_path, 'r') as f:
        return f.read()

# 方式2: StructuredTool（复杂参数）
class SearchInput(BaseModel):
    query: str = Field(description="搜索关键词")
    max_results: int = Field(default=5, description="最大结果数")

def search_func(query: str, max_results: int = 5) -> str:
    # 执行搜索逻辑
    return f"搜索 '{query}' 的结果..."

search_tool = StructuredTool.from_function(
    func=search_func,
    name="web_search",
    description="在网上搜索信息",
    args_schema=SearchInput
)
```

---

## 4. 实现步骤

### 第一阶段：基础框架搭建

- [ ] **4.1 项目初始化**
  - 创建项目结构
  - 配置 Python 虚拟环境
  - 安装 LangChain 及相关依赖

- [ ] **4.2 LLM 配置（Kimi + LangChain）**
  - 使用 ChatOpenAI 封装 Kimi API
  - 配置代理以访问外网
  - 测试基本对话功能
  - 验证流式输出

- [ ] **4.3 配置管理**
  - 环境变量管理（KIMI_API_KEY, HTTP_PROXY等）
  - .env 文件配置
  - config.yaml 加载

### 第二阶段：核心功能开发

- [ ] **4.4 Prompt 工程**
  - 学习 LangChain PromptTemplate
  - 掌握 ChatPromptTemplate
  - 理解 Few-shot 示例

- [ ] **4.5 ReAct Agent**
  - 使用 create_react_agent 创建 Agent
  - 配置 AgentExecutor
  - 理解 Agent 执行流程

- [ ] **4.6 LangGraph（高级）**
  - 学习状态图概念
  - 创建多步骤工作流
  - 实现条件分支和循环

### 第三阶段：工具生态

- [ ] **4.7 LangChain 工具开发**
  - 使用 @tool 装饰器创建工具
  - 使用 StructuredTool 定义复杂工具
  - 集成内置工具（搜索、计算等）

- [ ] **4.8 自定义工具集**
  - 文件操作工具（读/写/搜索）
  - 网络请求工具（支持代理）
  - Shell命令工具（Linux环境）
  - Python代码执行工具

### 第四阶段：记忆与检索

- [ ] **4.9 对话记忆**
  - ConversationBufferMemory（完整历史）
  - ConversationSummaryMemory（摘要）
  - ConversationBufferWindowMemory（滑动窗口）

- [ ] **4.10 RAG 检索增强**
  - 文档加载与分割
  - 向量化存储（ChromaDB）
  - 检索链（RetrievalQA）

### 第五阶段：用户界面（Windows 远程访问）

- [ ] **4.11 Web API 后端（FastAPI）**
  - RESTful API 设计
  - WebSocket 实时通信（流式输出）
  - 跨域配置（CORS）
  - 绑定 0.0.0.0 以允许远程访问

- [ ] **4.12 Web 前端界面**
  - Streamlit（快速原型，推荐）
  - 或 Gradio（更简单）
  - 对话界面 + 工具执行可视化
  - 配置 server.address 和 server.port

- [ ] **4.13 命令行界面（可选）**
  - 交互式CLI（本地调试用）
  - 输出美化

### 第六阶段：优化与完善

- [ ] **4.14 性能优化**
  - 并发执行
  - 缓存机制
  - Token优化

- [ ] **4.15 可靠性增强**
  - 日志系统
  - 错误处理
  - 单元测试

---

## 5. 项目结构

```
agent-learn-2/
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── react_agent.py   # ReAct Agent实现
│   │   ├── graph_agent.py   # LangGraph Agent实现
│   │   └── prompts.py       # Agent专用Prompt
│   ├── llm/
│   │   ├── __init__.py
│   │   └── kimi_llm.py      # Kimi LLM封装（基于ChatOpenAI）
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── conversation.py  # 对话记忆（ConversationBufferMemory）
│   │   └── vector_store.py  # 向量存储（ChromaDB）
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── file_tools.py    # 文件操作工具
│   │   ├── web_tools.py     # 网络请求工具
│   │   ├── shell_tools.py   # Shell命令工具
│   │   └── custom_tools.py  # 自定义工具模板
│   ├── chains/
│   │   ├── __init__.py
│   │   ├── qa_chain.py      # 问答链
│   │   └── rag_chain.py     # RAG检索链
│   └── utils/
│       ├── __init__.py
│       ├── config.py        # 配置管理
│       └── logger.py        # 日志工具
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_llm.py
│   └── test_tools.py
├── web/
│   ├── __init__.py
│   ├── api.py               # FastAPI 后端
│   ├── app.py               # Streamlit 前端
│   └── static/              # 静态资源
├── examples/
│   ├── 01_simple_chat.py    # 简单对话
│   ├── 02_react_agent.py    # ReAct Agent示例
│   ├── 03_tool_calling.py   # 工具调用示例
│   ├── 04_langgraph.py      # LangGraph示例
│   └── 05_rag.py            # RAG示例
├── notebooks/
│   └── playground.ipynb     # 实验笔记本
├── config/
│   └── config.yaml          # 主配置文件
├── requirements.txt
├── README.md
├── plan.md                  # 本文件
└── .env.example             # 环境变量模板
```

---

## 6. 关键Prompt设计

### 6.1 系统Prompt模板

```
你是一个智能助手，具备以下能力：
{tool_descriptions}

当需要完成任务时，请按以下格式思考和行动：

思考：分析当前情况，决定下一步行动
行动：选择一个工具并提供参数
观察：查看工具执行结果
...（重复直到任务完成）
最终回答：总结并回答用户问题
```

### 6.2 工具调用格式

```json
{
  "thought": "我需要先读取文件内容...",
  "action": {
    "tool": "read_file",
    "parameters": {
      "path": "/path/to/file.txt"
    }
  }
}
```

---

## 7. 技术要点

### 7.1 ReAct模式
- **Reasoning**: 让LLM显式输出推理过程
- **Acting**: 基于推理选择并执行动作
- **循环**: 观察结果后继续推理

### 7.2 工具选择策略
- 提供清晰的工具描述
- 包含使用示例
- 限制可用工具数量（避免选择困难）

### 7.3 上下文管理
- 滑动窗口保留最近对话
- 重要信息摘要
- 按需检索历史信息

### 7.4 错误处理
- 工具执行失败时的重试策略
- 无限循环检测与中断
- 优雅降级机制

---

## 8. 学习资源

### 8.1 LangChain 官方资源
- [LangChain 文档](https://python.langchain.com/docs/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangChain GitHub](https://github.com/langchain-ai/langchain)
- [LangSmith（调试平台）](https://smith.langchain.com/)

### 8.2 核心论文
- [ReAct: Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629)
- [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)
- [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)

### 8.3 推荐学习路径
1. **入门**: LangChain Quickstart → PromptTemplate → Chains
2. **进阶**: Tools → Agents → Memory
3. **高级**: LangGraph → RAG → 生产部署

---

## 9. 里程碑检查点

| 阶段 | 目标 | 验收标准 |
|------|------|----------|
| M1 | 基础对话 | Kimi + LangChain 完成基本对话 |
| M2 | ReAct Agent | 创建能调用工具的 ReAct Agent |
| M3 | 自定义工具 | 至少3个自定义工具正常工作 |
| M4 | 记忆与RAG | 多轮对话 + 文档检索问答 |
| M5 | LangGraph | 实现复杂多步骤工作流 |
| **M6** | **Web 服务** | **Windows 浏览器能访问 Agent** |
| M7 | 完整应用 | 功能完善，稳定可用 |

---

## 10. 环境配置指南

### 10.1 Kimi API 配置

```bash
# .env 文件示例
KIMI_API_KEY=your_kimi_api_key_here
KIMI_BASE_URL=https://api.moonshot.cn/v1

# 代理配置（如需要）
HTTP_PROXY=http://your-proxy:port
HTTPS_PROXY=http://your-proxy:port
```

### 10.2 LangChain + Kimi API 调用示例

```python
import os
from langchain_openai import ChatOpenAI

# Kimi API 兼容 OpenAI 接口，直接用 ChatOpenAI
llm = ChatOpenAI(
    model="moonshot-v1-8k",  # 或 moonshot-v1-32k, moonshot-v1-128k
    openai_api_key=os.getenv("KIMI_API_KEY"),
    openai_api_base="https://api.moonshot.cn/v1",
    temperature=0.7,
)

# 简单调用
response = llm.invoke("你好，请介绍一下你自己")
print(response.content)

# 创建 ReAct Agent
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub

prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm, tools=[], prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=[], verbose=True)
```

### 10.3 代理配置（如需要）

```python
import os
import httpx

# 方式1: 环境变量（推荐）
os.environ["HTTP_PROXY"] = "http://your-proxy:port"
os.environ["HTTPS_PROXY"] = "http://your-proxy:port"

# 方式2: httpx 自定义 client
http_client = httpx.Client(proxies={"http://": proxy, "https://": proxy})
llm = ChatOpenAI(
    ...,
    http_client=http_client
)
```

### 10.4 Linux 虚拟机环境准备

```bash
# 1. 更新系统
sudo apt update && sudo apt upgrade -y

# 2. 安装 Python 3.10+
sudo apt install python3.10 python3.10-venv python3-pip -y

# 3. 创建项目目录和虚拟环境
mkdir -p ~/projects/agent-learn-2
cd ~/projects/agent-learn-2
python3 -m venv venv
source venv/bin/activate

# 4. 安装核心依赖
pip install langchain langchain-openai langchain-community langgraph
pip install chromadb faiss-cpu  # 向量数据库
pip install python-dotenv pyyaml httpx  # 工具库

# 5. 配置代理（如需要，添加到 ~/.bashrc）
export HTTP_PROXY="http://your-proxy:port"
export HTTPS_PROXY="http://your-proxy:port"
```

### 10.5 requirements.txt 参考

```
# LangChain 核心
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-community>=0.0.10
langgraph>=0.0.20

# 向量数据库
chromadb>=0.4.0
faiss-cpu>=1.7.4

# Web 服务
fastapi>=0.109.0
uvicorn>=0.27.0
streamlit>=1.30.0
websockets>=12.0

# 工具库
python-dotenv>=1.0.0
pyyaml>=6.0
httpx>=0.25.0

# 开发工具
jupyter>=1.0.0
pytest>=7.0.0
```

### 10.6 Windows 远程访问配置

#### 获取 Linux 虚拟机 IP
```bash
# 在 Linux 虚拟机上执行
ip addr show | grep inet
# 或
hostname -I
# 假设得到 IP: 192.168.1.100
```

#### 启动 Web 服务（Linux）
```bash
# 方式1: FastAPI 后端
cd ~/projects/agent-learn-2
source venv/bin/activate
uvicorn web.api:app --host 0.0.0.0 --port 8000

# 方式2: Streamlit 前端
streamlit run web/app.py --server.address 0.0.0.0 --server.port 8501
```

#### Windows 浏览器访问
```
# FastAPI 接口文档
http://192.168.1.100:8000/docs

# Streamlit Web UI
http://192.168.1.100:8501
```

#### 防火墙配置（如需要）
```bash
# Linux 开放端口
sudo ufw allow 8000
sudo ufw allow 8501
```

### 10.7 FastAPI 基础示例

```python
# web/api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Agent API")

# 允许跨域（Windows 浏览器访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 调用 Agent
    from src.agent.react_agent import agent_executor
    result = agent_executor.invoke({"input": request.message})
    return ChatResponse(reply=result["output"])

# 启动: uvicorn web.api:app --host 0.0.0.0 --port 8000
```

### 10.8 Streamlit 基础示例

```python
# web/app.py
import streamlit as st
from src.llm.kimi_llm import get_llm

st.title("🤖 Agent Chat")

# 初始化对话历史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 用户输入
if prompt := st.chat_input("请输入您的问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # 调用 Agent
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            llm = get_llm()
            response = llm.invoke(prompt)
            st.write(response.content)
            st.session_state.messages.append(
                {"role": "assistant", "content": response.content}
            )

# 启动: streamlit run web/app.py --server.address 0.0.0.0 --server.port 8501
```

---

## 11. 下一步行动

1. **环境搭建**: 在 Linux 虚拟机上安装 LangChain 和依赖
2. **首要任务**: 用 ChatOpenAI + Kimi API 完成第一次对话
3. **中期目标**: 创建一个能调用自定义工具的 ReAct Agent
4. **最终目标**: 部署 Web 服务，实现 Windows 浏览器访问

---

## 12. 功能完成状态

> 更新时间: 2026-02-27

### 12.1 核心RAG

| 功能 | 状态 | 说明 |
|------|------|------|
| 文档上传（PDF/Word/TXT） | ✅ 已实现 | `web/app.py` 支持多格式上传 |
| 文本切分与向量化 | ✅ 已实现 | `src/memory/vector_store.py` |
| 向量数据库（ChromaDB） | ✅ 已实现 | 本地持久化存储 |
| 相似度检索 | ✅ 已实现 | RAG 工具集成 |
| 大模型问答（Kimi API） | ✅ 已实现 | `src/llm/kimi.py` |
| 答案来源引用 | ✅ 已实现 | 回答末尾显示"📚 参考来源" |

### 12.2 前端界面

| 功能 | 状态 | 说明 |
|------|------|------|
| Web聊天界面 | ✅ Streamlit | `web/app.py` 完整实现 |
| 知识库管理后台 | ✅ 已实现 | 侧边栏显示文档列表、支持删除 |
| 用户登录/权限 | ❌ 未实现 | - |

### 12.3 部署运维

| 功能 | 状态 | 说明 |
|------|------|------|
| Docker容器化 | ✅ 已实现 | `Dockerfile` |
| Docker Compose | ✅ 已实现 | `docker-compose.yml` |
| 时序数据库（InfluxDB） | ❌ 未实现 | 用于记录性能指标 |
| 监控告警 | ❌ 未实现 | Prometheus/Grafana |

### 12.4 对接集成

| 功能 | 状态 | 说明 |
|------|------|------|
| 企业微信机器人 | ❌ 未实现 | - |
| 钉钉机器人 | ❌ 未实现 | - |
| 飞书机器人 | ❌ 未实现 | - |
| API接口（FastAPI） | ✅ 已实现 | `api/main.py` 完整实现 |

### 12.5 高级功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 多轮对话/上下文记忆 | ✅ 已实现 | `src/db/chat_history.py` |
| 本地模型部署（Ollama） | ❌ 未实现 | 降低成本 |
| 多租户/多知识库隔离 | ❌ 未实现 | 企业场景需要 |
| 用户权限管理（RBAC） | ❌ 未实现 | - |
| 模型微调接口 | ❌ 未实现 | 领域优化 |

### 12.6 工具生态

| 工具 | 状态 | 文件 |
|------|------|------|
| 计算器 | ✅ 已实现 | `src/tools/calculator.py` |
| 时间查询 | ✅ 已实现 | `src/tools/time_tool.py` |
| 天气查询 | ✅ 已实现 | `src/tools/weather.py` (Open-Meteo API) |
| 网页搜索 | ✅ 已实现 | `src/tools/search.py` |
| 翻译工具 | ✅ 已实现 | `src/tools/translate.py` |
| 网页内容读取 | ✅ 已实现 | `src/tools/webpage.py` |
| 知识库检索 | ✅ 已实现 | `src/memory/vector_store.py` |

---

## 13. 未来发展计划

### 阶段1：工程优化（优先级 P0）

> 目标：让项目"专业可交付"

| 任务 | 优先级 | 预计工作量 | 状态 | 说明 |
|------|--------|-----------|------|------|
| 完善知识库管理界面 | P0 | 1天 | ✅ 完成 | 文档列表、删除功能 |
| 答案来源引用展示 | P0 | 0.5天 | ✅ 完成 | RAG 回答显示参考来源 |
| FastAPI 后端完善 | P1 | 1-2天 | ✅ 完成 | `api/` 完整实现 |
| 健康检查接口 | P1 | 0.5天 | ✅ 完成 | `/health` 端点 |
| 时序数据库集成 | P2 | 2天 | 待开始 | InfluxDB 记录性能指标 |
| 基础监控 | P2 | 1天 | 待开始 | Sentry 或简单日志监控 |

**验收标准：**
- [x] 知识库支持查看/删除文档
- [x] RAG 回答显示来源引用
- [x] `/health` 接口返回服务状态
- [x] 有部署文档（Docker部署指南.md）
- [x] FastAPI 后端完整实现

### 阶段2：本地模型接入（优先级 P1）

> 目标：验证本地部署可行性，降低 API 成本

| 任务 | 优先级 | 预计工作量 | 说明 |
|------|--------|-----------|------|
| Ollama 环境搭建 | P1 | 0.5天 | 安装并测试 |
| Qwen2.5-7B 接入 | P1 | 1天 | 替换 API 调用 |
| 双模型架构 | P1 | 2天 | 简单问题走本地，复杂问题走 API |
| 效果评估脚本 | P1 | 1天 | 对比本地 vs API 效果 |

**推荐模型选型：**
| Agent类型 | 推荐模型 | 显存需求 |
|----------|---------|---------|
| 通用问答 | Qwen2.5-7B-Instruct | 10-12G |
| 代码/技术 | Qwen2.5-Coder-7B | 10-12G |
| 推理分析 | DeepSeek-R1-Distill-7B | 12-14G |

**验收标准：**
- [ ] 本地模型能跑通 Agent 全流程
- [ ] 有量化评估：本地 vs API 的效果差距
- [ ] 确定是否值得微调

### 阶段3：领域微调（优先级 P2）

> 目标：建立技术壁垒，效果超越通用模型

| 任务 | 优先级 | 预计工作量 | 说明 |
|------|--------|-----------|------|
| 数据准备 | P2 | 持续 | 收集 100-500 条高质量问答 |
| LLaMA-Factory 环境 | P2 | 1天 | 微调工具安装配置 |
| QLoRA 微调 | P2 | 2-3天 | 单卡 16G 可运行 |
| A/B 测试框架 | P2 | 1天 | 对比微调前后效果 |

**数据量建议：**
- 最小可行：100条
- 有效果：500-1000条
- 较好效果：3000-5000条

**验收标准：**
- [ ] 微调后模型超越本地基座模型
- [ ] 至少达到 API 模型 80% 效果
- [ ] 能讲清楚微调模型的适用场景

### 阶段4：企业集成（优先级 P3）

> 目标：对接企业办公生态

| 任务 | 优先级 | 预计工作量 | 说明 |
|------|--------|-----------|------|
| 企业微信机器人 | P3 | 2天 | Webhook 接入 |
| 钉钉机器人 | P3 | 2天 | - |
| 飞书机器人 | P3 | 2天 | - |
| 用户权限管理 | P3 | 3天 | RBAC 基础实现 |
| 多知识库隔离 | P3 | 2天 | 按部门/项目隔离 |

---

## 14. 近期任务清单

### 已完成任务 ✅

- [x] 完善知识库管理：文档列表、删除功能
- [x] RAG 答案来源引用：回答末尾显示参考来源
- [x] Docker 部署优化：代理配置分离

### 已完成 P1 任务

- [x] 完善 FastAPI 后端接口（供外部系统调用）
- [x] 添加 `/health` 健康检查端点
- [x] API 文档生成（Swagger/OpenAPI）

### 下一阶段任务

- [x] 基础监控和日志记录
- [x] API 认证（API Key）
- [ ] 对接企业微信/钉钉机器人

### 可选任务（需 GPU）

- [ ] 安装 Ollama，测试 Qwen2.5:7B
- [ ] 编写效果评估脚本（本地 vs API 对比）

### 数据准备（持续）

- [ ] 整理现有 Agent 的优质回答，存为 JSONL
- [ ] 收集典型业务问题，编写标准答案

---

## 15. 技术架构演进

### 当前架构
```
用户 → Streamlit UI → LangChain Agent → Kimi API
                           ↓
                      ChromaDB (RAG)
```

### 目标架构（阶段2完成后）
```
用户 → Streamlit UI → 路由层 → 简单问题 → 本地 Qwen2.5-7B
         ↓              ↓
    FastAPI 后端    复杂问题 → Kimi API
         ↓
    InfluxDB (指标)   ChromaDB (RAG)
         ↓
    Grafana (监控)
```

### 企业级架构（阶段4完成后）
```
              ┌─────────────┐
              │   企业微信   │
              │   钉钉/飞书  │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │  API 网关    │
              │  (认证/限流) │
              └──────┬──────┘
                     │
┌────────────────────▼────────────────────┐
│              Agent 服务层                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ 本地模型 │  │ API模型  │  │  RAG   │  │
│  └─────────┘  └─────────┘  └─────────┘  │
└─────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼────┐            ┌────▼────┐
    │ InfluxDB │            │ ChromaDB│
    │  (指标)  │            │  (向量) │
    └─────────┘            └─────────┘
```

---

*计划创建时间: 2026-01-25*
*最后更新: 2026-02-27*
*状态: 阶段1 进行中*
