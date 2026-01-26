# 🐳 Docker 部署指南

> 适用于生产部署、快速迁移场景

---

## 📋 前置要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux / macOS / Windows (Docker Desktop) |
| Docker | 20.10+ |
| 内存 | 至少 4GB |
| 磁盘 | 至少 3GB 可用空间 |

### 检查 Docker 安装

```bash
docker --version
# Docker version 20.10.x 或更高
```

---

## 🚀 部署方式

### 方式一：使用预构建镜像（推荐）

如果你有 `jingjing-agent.tar` 镜像文件：

```bash
# 1. 导入镜像
docker load -i jingjing-agent.tar

# 2. 验证导入成功
docker images | grep jingjing
```

### 方式二：从源码构建

```bash
# 1. 进入项目目录
cd agent-learn-2

# 2. 构建镜像（如需代理）
docker build \
  --build-arg HTTP_PROXY=http://your-proxy:port \
  --build-arg HTTPS_PROXY=http://your-proxy:port \
  -t jingjing-agent:latest .

# 2. 构建镜像（无需代理）
docker build -t jingjing-agent:latest .
```

---

## ⚙️ 配置环境变量

在运行容器前，必须准备 `.env` 文件：

```bash
# 创建 .env 文件
cat > .env << 'EOF'
# Kimi API 配置（必填）
KIMI_API_KEY=your_kimi_api_key_here
KIMI_BASE_URL=https://api.moonshot.cn/v1

# 代理配置（如需要）
HTTP_PROXY=http://your-proxy:port
HTTPS_PROXY=http://your-proxy:port
EOF
```

---

## 🚀 启动容器

### 方式一：docker run（简单）

```bash
# 创建数据目录
mkdir -p data

# 启动容器
docker run -d \
  --name jingjing-agent \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env:ro \
  -e HTTP_PROXY=http://your-proxy:port \
  -e HTTPS_PROXY=http://your-proxy:port \
  --restart unless-stopped \
  jingjing-agent:latest
```

### 方式二：docker-compose（推荐）

```bash
# 启动
docker-compose up -d

# 查看状态
docker-compose ps

# 停止
docker-compose down
```

### 方式三：使用便捷脚本

```bash
# 构建镜像
./docker-build.sh build

# 启动容器
./docker-build.sh run

# 查看日志
./docker-build.sh logs

# 停止容器
./docker-build.sh stop
```

---

## 🌐 访问应用

启动成功后，打开浏览器访问：

```
http://localhost:8501        # 本机访问
http://<服务器IP>:8501       # 远程访问
```

---

## 🔧 常用命令

### 容器管理

```bash
# 查看运行状态
docker ps | grep jingjing

# 查看日志
docker logs -f jingjing-agent

# 进入容器（调试）
docker exec -it jingjing-agent bash

# 重启容器
docker restart jingjing-agent

# 停止容器
docker stop jingjing-agent

# 删除容器
docker rm -f jingjing-agent
```

### 镜像管理

```bash
# 查看镜像
docker images | grep jingjing

# 导出镜像（用于迁移）
docker save -o jingjing-agent.tar jingjing-agent:latest

# 导入镜像
docker load -i jingjing-agent.tar

# 删除镜像
docker rmi jingjing-agent:latest
```

---

## 📦 迁移到其他服务器

### 步骤 1：在源服务器导出

```bash
# 导出镜像
docker save -o jingjing-agent.tar jingjing-agent:latest

# 打包配置文件
tar -czvf config.tar.gz .env data/
```

### 步骤 2：传输文件

```bash
# 使用 scp 传输
scp jingjing-agent.tar config.tar.gz user@目标服务器:/path/to/
```

### 步骤 3：在目标服务器部署

```bash
# 导入镜像
docker load -i jingjing-agent.tar

# 解压配置
tar -xzvf config.tar.gz

# 启动容器
docker run -d \
  --name jingjing-agent \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env:ro \
  --restart unless-stopped \
  jingjing-agent:latest
```

---

## ❓ 常见问题

### Q1: 端口被占用

```bash
# 使用其他端口
docker run -d -p 9000:8501 ... jingjing-agent:latest

# 访问 http://localhost:9000
```

### Q2: 容器启动后立即退出

```bash
# 查看日志
docker logs jingjing-agent

# 常见原因：
# 1. .env 文件不存在或格式错误
# 2. API Key 无效
```

### Q3: 无法访问 API

```bash
# 确保传入了代理环境变量
docker run -d \
  -e HTTP_PROXY=http://your-proxy:port \
  -e HTTPS_PROXY=http://your-proxy:port \
  ...
```

### Q4: 数据丢失

确保正确挂载了 data 目录：

```bash
# 检查挂载
docker inspect jingjing-agent --format '{{json .Mounts}}'

# 应该看到 /app/data 的挂载
```

### Q5: 健康检查失败

```bash
# 查看健康状态
docker inspect jingjing-agent --format '{{json .State.Health}}'

# 等待应用完全启动（约 30 秒）
```

---

## 📊 资源占用

| 资源 | 占用 |
|------|------|
| 镜像大小 | ~2.3 GB |
| 运行内存 | ~1-2 GB |
| CPU | 空闲时 <1%，处理请求时 10-30% |

---

## 🔒 安全建议

1. **不要将 .env 文件提交到 Git**
2. **使用 `:ro` 只读挂载敏感文件**
3. **限制容器资源使用**：
   ```bash
   docker run -d \
     --memory=2g \
     --cpus=1 \
     ...
   ```
4. **定期更新镜像**

---

## 📁 文件清单

部署时需要准备的文件：

```
├── jingjing-agent.tar    # Docker 镜像（或从源码构建）
├── .env                  # 环境配置（必需）
├── docker-compose.yml    # 编排配置（可选）
└── data/                 # 数据目录（自动创建）
    ├── docs/             # 知识库文档
    ├── chroma_db/        # 向量数据库
    └── chat_history.db   # 对话历史
```
