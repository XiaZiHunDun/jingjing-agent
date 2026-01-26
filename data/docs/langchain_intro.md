# LangChain 框架介绍

## 什么是 LangChain？

LangChain 是一个用于构建大语言模型（LLM）应用的开源框架。它提供了一套完整的工具和抽象，帮助开发者快速构建基于 LLM 的应用程序。

## 核心组件

### 1. Models（模型）

LangChain 支持多种 LLM 提供商：
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- Google (Gemini)
- Moonshot AI (Kimi)
- 本地模型 (Ollama, LlamaCpp)

### 2. Prompts（提示词）

提示词模板用于构建发送给 LLM 的输入：
- PromptTemplate：基础字符串模板
- ChatPromptTemplate：聊天消息模板
- FewShotPromptTemplate：少样本学习模板

### 3. Chains（链）

链是将多个组件串联起来的方式：
- LLMChain：最基础的链，连接提示词和模型
- SequentialChain：顺序执行多个链
- RouterChain：根据条件路由到不同的链

### 4. Agents（智能体）

Agent 是能够自主决策和调用工具的 AI 系统：
- ReAct Agent：推理和行动交替进行
- Tool Agent：专注于工具调用
- Custom Agent：自定义决策逻辑

### 5. Memory（记忆）

记忆组件让 LLM 能够记住之前的对话：
- ConversationBufferMemory：保存完整对话历史
- ConversationSummaryMemory：保存对话摘要
- VectorStoreMemory：使用向量数据库存储记忆

### 6. Retrieval（检索）

RAG（检索增强生成）相关组件：
- Document Loaders：加载各种格式的文档
- Text Splitters：将文档分割成小块
- Vector Stores：向量数据库（ChromaDB, FAISS）
- Retrievers：从向量库中检索相关内容

## LangGraph

LangGraph 是 LangChain 的扩展，用于构建复杂的多步骤工作流：
- 状态图（State Graph）
- 条件分支
- 循环和迭代
- 人机协作节点

## 安装方法

```bash
pip install langchain langchain-openai langchain-community langgraph
```

## 快速开始

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# 创建 LLM 实例
llm = ChatOpenAI(model="gpt-3.5-turbo")

# 创建提示词模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有帮助的助手"),
    ("human", "{input}")
])

# 创建链
chain = prompt | llm

# 调用
response = chain.invoke({"input": "你好"})
```

## 最佳实践

1. **使用合适的模型**：根据任务复杂度选择模型
2. **优化提示词**：清晰、具体的提示词效果更好
3. **控制上下文长度**：避免超出模型的 token 限制
4. **添加错误处理**：LLM 输出可能不稳定
5. **使用缓存**：减少重复 API 调用
