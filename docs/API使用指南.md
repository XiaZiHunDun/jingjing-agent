# 晶晶助手 API 使用指南

> 更新时间: 2026-03-10 (新增流式响应)

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
- `GET /api/stats` - 统计数据
- `GET /api/rate-limit` - 速率限制状态
- `GET /api/metrics/health` - 指标服务健康状态

---

## 速率限制

API 对高频接口（`/api/chat`、`/api/knowledge/upload`）启用了速率限制：

| 限制类型 | 默认值 | 说明 |
|----------|--------|------|
| 每分钟请求数 | 60 | 滑动窗口 |
| 每小时请求数 | 1000 | 滑动窗口 |
| 突发限制 | 10 | 防止瞬时高频请求 |

### 响应头

限流接口的响应会包含以下头信息：
- `X-RateLimit-Limit`: 每分钟限制
- `X-RateLimit-Remaining`: 剩余次数

### 超限响应

超过限制时返回 HTTP 429：
```json
{
  "error": "RateLimitExceeded",
  "message": "超过每分钟请求限制 (60/分钟)",
  "retry_after": 30
}
```

### 配置

在 `.env` 中配置：
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_BURST=10
```

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
    "database": "connected",
    "auth": "enabled",
    "influxdb": "connected"
  }
}
```

---

### 2. 获取统计数据

查看 API 调用统计。

```bash
curl http://localhost:8000/api/stats
```

**响应示例：**
```json
{
  "start_time": "2026-03-09T10:38:52",
  "total_requests": 100,
  "total_chats": 25,
  "total_errors": 2,
  "avg_response_time_ms": 150.5,
  "endpoints": {
    "POST /api/chat": {"count": 25, "errors": 1, "avg_ms": 2500},
    "GET /api/tools": {"count": 10, "errors": 0, "avg_ms": 50}
  },
  "tools_usage": {
    "calculator": 5,
    "get_weather": 8,
    "search_knowledge_base": 12
  },
  "uptime_seconds": 3600
}
```

---

### 3. 发送消息

与晶晶助手对话，支持普通响应和流式响应两种模式。

#### 普通模式

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
| stream | boolean | 否 | 是否启用流式响应（默认 false） |

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

#### 流式模式（SSE）

设置 `stream: true` 启用流式响应，实时接收 AI 输出。

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "计算 15 * 23", "session_id": "user_001", "stream": true}'
```

**响应格式（Server-Sent Events）：**
```
data: {"event": "tool_start", "name": "calculator", "args": {"expression": "15*23"}}

data: {"event": "tool_end", "name": "calculator", "result": "计算结果: 345"}

data: {"event": "token", "content": "计算"}

data: {"event": "token", "content": "结果"}

data: {"event": "token", "content": "为 345。"}

data: {"event": "done", "answer": "计算结果为 345。", "thinking_steps": [...], "session_id": "user_001"}
```

**事件类型：**
| event | 说明 |
|-------|------|
| tool_start | 开始调用工具 |
| tool_end | 工具返回结果 |
| token | AI 输出的文本片段 |
| done | 完成，包含完整回答 |
| error | 发生错误 |

**前端使用示例（JavaScript）：**
```javascript
const eventSource = new EventSource('/api/chat?...');  // 或使用 fetch + ReadableStream

// 使用 fetch 的流式处理
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({ message: '你好', stream: true })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const text = decoder.decode(value);
  const lines = text.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      if (event.event === 'token') {
        console.log(event.content);  // 实时显示
      }
    }
  }
}
```

---

### 4. 获取工具列表

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

### 6. 会话管理

#### 获取会话列表

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/sessions
```

**响应示例：**
```json
{
  "sessions": [
    {
      "session_id": "s_100831",
      "title": "什么是多智能体系统",
      "updated_at": "2026-03-09 10:08:51",
      "msg_count": 2
    }
  ],
  "total": 3
}
```

#### 获取会话详情

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/sessions/s_100831
```

#### 删除会话

```bash
curl -X DELETE -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/sessions/s_100831
```

---

### 7. 指标查询（时序数据库）

需要启用 InfluxDB 后使用。在 `.env` 中配置：

```bash
INFLUXDB_ENABLED=true
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=jingjing
INFLUXDB_BUCKET=metrics
```

启动 InfluxDB 容器：

```bash
docker compose up -d influxdb
```

#### 获取指标概要

```bash
curl -H "X-API-Key: your-api-key" "http://localhost:8000/api/metrics/summary?hours=24"
```

**响应示例：**
```json
{
  "enabled": true,
  "connected": true,
  "api_stats": {
    "total": 150,
    "avg_duration_ms": 534.9,
    "max_duration_ms": 1916.0,
    "min_duration_ms": 0.7
  },
  "tool_usage": [
    {"tool": "get_weather", "count": 10},
    {"tool": "calculator", "count": 5}
  ]
}
```

#### 获取 API 请求指标

```bash
curl -H "X-API-Key: your-api-key" "http://localhost:8000/api/metrics/requests?hours=24"
```

#### 获取工具使用指标

```bash
curl -H "X-API-Key: your-api-key" "http://localhost:8000/api/metrics/tools?hours=24"
```

#### 获取趋势数据

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/metrics/trends?measurement=api_requests&field=duration_ms&hours=24&interval=1h"
```

**响应示例：**
```json
{
  "measurement": "api_requests",
  "field": "duration_ms",
  "interval": "1h",
  "data": [
    {"time": "2026-03-10T02:00:00+00:00", "value": 150.5},
    {"time": "2026-03-10T03:00:00+00:00", "value": 200.3}
  ]
}
```

**支持的 measurement：**
- `api_requests` - API 请求指标
- `chat_metrics` - 对话指标
- `tool_calls` - 工具调用指标
- `system_metrics` - 系统资源指标

---

### 8. 知识库管理

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
