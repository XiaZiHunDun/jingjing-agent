# 晶晶助手 API 使用指南

> 更新时间: 2026-03-09

## 快速开始

### 启动 API 服务

```bash
cd /home/ailearn/projects/agent-learn-2
conda activate agent-learn
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 访问 API 文档

启动后访问：
- **Swagger UI**: http://服务器IP:8000/docs
- **ReDoc**: http://服务器IP:8000/redoc

---

## 认证方式

大部分 API 接口需要认证，支持两种方式传递 API Key：

### 1. Header 方式（推荐）

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/chat ...
```

### 2. Query 参数方式

```bash
curl "http://localhost:8000/api/chat?api_key=your-api-key" ...
```

### 配置 API Key

在 `.env` 文件中配置：

```bash
# 单个 Key
API_KEYS=your-secret-key

# 多个 Key（逗号分隔）
API_KEYS=key1,key2,key3
```

**注意**：如果 `API_KEYS` 为空，则认证功能自动禁用（开发模式）。

### 公开接口（无需认证）

- `GET /` - API 信息
- `GET /health` - 健康检查

---

## API 接口

### 1. 健康检查

检查服务及各组件状态。

```bash
curl http://localhost:8000/health
```

**响应示例：**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "llm": "connected",
    "vector_store": "loaded",
    "database": "connected"
  }
}
```

---

### 2. 发送消息

与晶晶助手对话。

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "北京天气怎么样？", "session_id": "user_001"}'
```

**请求参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户消息 |
| session_id | string | 否 | 会话ID，用于保持上下文 |

**响应示例：**
```json
{
  "answer": "北京今天天气晴朗，气温 15°C。",
  "session_id": "user_001",
  "thinking_steps": [
    {
      "name": "get_weather",
      "args": {"city": "北京"},
      "result": "☀️ 晴朗, 15°C"
    }
  ],
  "timestamp": "2026-03-09T10:30:00"
}
```

---

### 3. 获取工具列表

查看可用的工具。

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/tools
```

**响应示例：**
```json
{
  "tools": [
    {"name": "calculator", "description": "计算数学表达式"},
    {"name": "get_weather", "description": "查询城市天气"},
    {"name": "translate", "description": "翻译文本"},
    ...
  ],
  "total": 7
}
```

---

### 4. 知识库管理

#### 获取文档列表

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/knowledge
```

#### 上传文档

```bash
curl -X POST http://localhost:8000/api/knowledge/upload \
  -H "X-API-Key: your-api-key" \
  -F "file=@/path/to/document.pdf"
```

支持格式：txt, md, pdf, docx

#### 删除文档

```bash
curl -X DELETE -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/knowledge/文档名.pdf
```

---

## 与 Streamlit 共存

API 服务（端口 8000）和 Streamlit 界面（端口 8501）可以同时运行：

```bash
# 终端1：启动 API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 终端2：启动 Web 界面
streamlit run web/app.py --server.address 0.0.0.0 --server.port 8501
```

---

## Docker 部署

更新 `docker-compose.yml` 添加 API 服务端口映射：

```yaml
services:
  jingjing-agent:
    ports:
      - "8501:8501"  # Streamlit
      - "8000:8000"  # FastAPI
    command: >
      sh -c "uvicorn api.main:app --host 0.0.0.0 --port 8000 &
             streamlit run web/app.py --server.address 0.0.0.0 --server.port 8501"
```

---

## 错误处理

所有 API 错误返回统一格式：

```json
{
  "error": "ErrorType",
  "message": "错误详情",
  "timestamp": "2026-03-09T10:30:00"
}
```

常见 HTTP 状态码：
- `200`: 成功
- `400`: 请求参数错误
- `401`: 缺少 API Key
- `403`: 无效的 API Key
- `500`: 服务器内部错误

### 认证错误示例

缺少 API Key：
```json
{
  "detail": "缺少 API Key，请在 Header 中添加 X-API-Key 或在 URL 中添加 api_key 参数"
}
```

无效 API Key：
```json
{
  "detail": "无效的 API Key"
}
```
