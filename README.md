# 🤖 Agent Learn 2

一个基于 LangChain + Kimi API 的智能体（Agent）学习项目。

## ✨ 功能特性

- 💬 **智能对话** - 基于 Kimi API 的多轮对话
- 🔧 **工具调用** - ReAct 模式的 Agent，可调用计算器、时间查询等工具
- 📚 **RAG 知识库** - 本地文档检索增强生成
- 🧠 **对话记忆** - 支持多会话的对话记忆
- 🌐 **Web 界面** - Streamlit 构建的聊天界面
- 📄 **文档上传** - 可上传文档到知识库

## 📖 部署文档

| 方式 | 文档 | 适用场景 |
|------|------|----------|
| 🐍 **本地部署** | [本地部署指南.md](docs/本地部署指南.md) | 开发调试、本地使用 |
| 🐳 **Docker 部署** | [Docker部署指南.md](docs/Docker部署指南.md) | 生产部署、快速迁移 |

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活 conda 环境
conda activate agent-learn

# 安装依赖（如果还没安装）
pip install -r requirements.txt
```

### 2. 配置环境变量

确保 `.env` 文件已配置：

```env
KIMI_API_KEY=your_api_key
KIMI_BASE_URL=https://api.moonshot.cn/v1
HTTP_PROXY=http://your-proxy:port  # 如需代理
```

### 3. 启动服务

```bash
# 方式 1：使用启动脚本（推荐）
./start.sh

# 方式 2：手动启动
streamlit run web/app.py --server.address 0.0.0.0 --server.port 8501
```

### 4. 访问界面

- **本地访问**: http://localhost:8501
- **远程访问**: http://192.168.16.58:8501

## 📁 项目结构

```
agent-learn-2/
├── src/                    # 源代码
│   ├── agent/              # Agent 实现
│   ├── llm/                # LLM 封装
│   ├── memory/             # 记忆系统
│   ├── tools/              # 工具定义
│   ├── chains/             # 链式调用
│   └── utils/              # 工具函数
├── web/
│   └── app.py              # Streamlit Web 界面
├── examples/               # 学习示例
│   ├── 00_test_kimi_api.py       # API 测试
│   ├── 01_prompt_engineering.py  # Prompt 工程
│   ├── 02_react_agent.py         # ReAct Agent
│   ├── 03_rag_basics.py          # RAG 基础
│   ├── 04_memory_system.py       # 记忆系统
│   └── 05_langgraph_advanced.py  # LangGraph 高级
├── data/
│   ├── docs/               # 知识库文档
│   └── chroma_db/          # 向量数据库
├── config/                 # 配置文件
├── tests/                  # 测试代码
├── .env                    # 环境变量（不提交 Git）
├── .env.example            # 环境变量模板
├── requirements.txt        # Python 依赖
├── start.sh                # 一键启动脚本
├── plan.md                 # 开发计划
├── DEV_ENV.md              # 开发环境文档
├── PROGRESS.md             # 进度追踪
└── README.md               # 本文件
```

## 📖 学习路径

本项目是一个渐进式的 Agent 学习项目，建议按以下顺序学习：

| 阶段 | 文件 | 内容 |
|------|------|------|
| 1 | `00_test_kimi_api.py` | 测试 API 连接 |
| 2 | `01_prompt_engineering.py` | Prompt 模板、Few-shot |
| 3 | `02_react_agent.py` | ReAct Agent、工具调用 |
| 4 | `03_rag_basics.py` | RAG 检索增强生成 |
| 5 | `04_memory_system.py` | 对话记忆系统 |
| 6 | `05_langgraph_advanced.py` | LangGraph 高级工作流 |

运行示例：

```bash
cd /home/ailearn/projects/agent-learn-2
conda activate agent-learn
python examples/01_prompt_engineering.py
```

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| LLM | Kimi API (Moonshot AI) |
| Agent 框架 | LangChain + LangGraph |
| 向量数据库 | ChromaDB |
| Embedding | HuggingFace (multilingual) |
| Web 框架 | Streamlit |
| 语言 | Python 3.11 |

## 📊 里程碑

- [x] M1: 基础对话
- [x] M2: ReAct Agent
- [x] M3: 自定义工具
- [x] M4: 记忆与 RAG
- [x] M5: LangGraph 高级
- [x] M6: Web 服务
- [x] M7: 完整应用

## 🔧 常用命令

```bash
# 启动 Web 服务
./start.sh

# 停止服务
pkill -f "streamlit run"

# 查看服务状态
ps aux | grep streamlit

# 运行测试
python examples/00_test_kimi_api.py
```

## 📝 配置说明

### Kimi API

- 获取 API Key: https://platform.moonshot.cn/
- 可用模型: `moonshot-v1-8k`, `moonshot-v1-32k`, `moonshot-v1-128k`

### 代理配置

如果需要通过代理访问 API，在 `.env` 中配置：

```env
HTTP_PROXY=http://your-proxy:port
HTTPS_PROXY=http://your-proxy:port
```

## 📄 License

MIT License

---

*创建时间: 2026-01-26*
