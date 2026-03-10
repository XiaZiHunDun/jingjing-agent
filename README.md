# 🤖 Agent Learn 2 - 晶晶助手

一个功能完整的智能体（Agent）系统，基于 LangChain + Kimi API 构建。

## ✨ 功能特性

### 核心功能
- 💬 **智能对话** - 基于 Kimi API 的多轮对话，支持上下文记忆
- 🔧 **工具调用** - ReAct 模式 Agent，支持计算器、天气、翻译等工具
- 📚 **RAG 知识库** - 本地文档检索增强生成，支持来源引用
- 🧠 **对话记忆** - SQLite 持久化存储，支持多会话管理

### API 服务
- 🌐 **RESTful API** - FastAPI 构建的完整后端接口
- 🔐 **API 认证** - 支持 API Key 认证
- 📊 **监控统计** - 请求日志、性能统计、调用计数
- ⏱️ **速率限制** - 防止 API 滥用，可配置限制规则

### 部署方式
- 🐍 **本地部署** - Conda 环境，开发调试
- 🐳 **Docker 部署** - 容器化部署，生产环境

---

## 📖 文档导航

| 文档 | 说明 |
|------|------|
| [本地部署指南](docs/本地部署指南.md) | Conda 环境部署 |
| [Docker部署指南](docs/Docker部署指南.md) | 容器化部署 |
| [API使用指南](docs/API使用指南.md) | API 接口文档 |
| [测试手册](docs/测试手册.md) | 功能测试说明 |
| [功能计划](docs/功能计划.md) | 功能规划和进度 |

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活 conda 环境
conda activate agent-learn

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件：

```env
# Kimi API
KIMI_API_KEY=your_api_key
KIMI_BASE_URL=https://api.moonshot.cn/v1

# API 认证
API_KEYS=your-api-key

# 速率限制
RATE_LIMIT_PER_MINUTE=60

# 代理（可选）
HTTP_PROXY=http://your-proxy:port
```

### 3. 启动服务

```bash
# 启动 Web 界面
streamlit run web/app.py --server.address 0.0.0.0 --server.port 8501

# 启动 API 服务
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 4. 访问服务

| 服务 | 地址 |
|------|------|
| Web 界面 | http://localhost:8501 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

---

## 🔌 API 接口

### 主要接口

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/health` | GET | 健康检查 | 否 |
| `/api/stats` | GET | 统计数据 | 否 |
| `/api/rate-limit` | GET | 速率限制状态 | 否 |
| `/api/chat` | POST | 发送消息 | 是 |
| `/api/tools` | GET | 工具列表 | 是 |
| `/api/knowledge` | GET | 知识库文档 | 是 |
| `/api/sessions` | GET | 会话列表 | 是 |

### 调用示例

```bash
# 发送消息
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "你好"}'
```

详细文档见 [API使用指南](docs/API使用指南.md)

---

## 📁 项目结构

```
agent-learn-2/
├── api/                    # FastAPI 后端
│   ├── main.py             # API 入口
│   ├── auth.py             # 认证模块
│   ├── rate_limit.py       # 速率限制
│   ├── middleware.py       # 中间件
│   ├── schemas.py          # 数据模型
│   └── routers/            # 路由模块
│       ├── chat.py         # 聊天接口
│       ├── knowledge.py    # 知识库接口
│       └── session.py      # 会话接口
├── src/                    # 核心源码
│   ├── agent/              # Agent 实现
│   ├── llm/                # LLM 封装
│   ├── memory/             # 向量存储
│   ├── tools/              # 工具定义
│   ├── db/                 # 数据库
│   └── utils/              # 工具函数
├── web/
│   └── app.py              # Streamlit 界面
├── data/
│   ├── docs/               # 知识库文档
│   └── chroma_db/          # 向量数据库
├── logs/                   # 日志文件
├── docs/                   # 文档
├── examples/               # 学习示例
├── .env                    # 环境配置
├── Dockerfile              # Docker 构建
├── docker-compose.yml      # Docker Compose
└── requirements.txt        # Python 依赖
```

---

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| LLM | Kimi API (Moonshot AI) |
| Agent 框架 | LangChain + LangGraph |
| 向量数据库 | ChromaDB |
| Embedding | HuggingFace (multilingual-MiniLM) |
| Web 框架 | Streamlit |
| API 框架 | FastAPI |
| 数据库 | SQLite |
| 语言 | Python 3.11 |

---

## 📊 功能完成状态

| 模块 | 功能 | 状态 |
|------|------|------|
| 核心 | 智能对话 | ✅ |
| 核心 | RAG 知识库 | ✅ |
| 核心 | 来源引用 | ✅ |
| API | RESTful 接口 | ✅ |
| API | 认证 (API Key) | ✅ |
| API | 速率限制 | ✅ |
| API | 监控统计 | ✅ |
| API | 会话管理 | ✅ |
| 部署 | Docker | ✅ |
| 部署 | 本地模型 | ⏸️ 需GPU |

---

## 🔧 常用命令

```bash
# 启动 Web 服务
streamlit run web/app.py --server.address 0.0.0.0 --server.port 8501

# 启动 API 服务
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Docker 部署
docker compose up -d

# 查看日志
tail -f logs/api.log

# 停止服务
pkill -f "streamlit\|uvicorn"
```

---

## 📝 更新日志

### 2026-03-09
- ✅ FastAPI 后端完善
- ✅ API 认证 (API Key)
- ✅ 日志和监控系统
- ✅ 会话管理 API
- ✅ 速率限制

### 2026-02-27
- ✅ 知识库管理完善
- ✅ RAG 来源引用
- ✅ Docker 部署优化

---

## 📄 License

MIT License

---

*创建时间: 2026-01-26 | 最后更新: 2026-03-09*
