# ============================================================
# Agent Learn 2 - Docker 镜像
# 基于 Python 3.11 的智能助手应用
# ============================================================

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 构建时代理配置（通过 build-arg 传入，仅用于构建阶段）
ARG HTTP_PROXY
ARG HTTPS_PROXY

# 安装系统依赖（使用构建时代理）
RUN if [ -n "$HTTP_PROXY" ]; then export http_proxy=$HTTP_PROXY https_proxy=$HTTPS_PROXY; fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（使用构建时代理）
RUN if [ -n "$HTTP_PROXY" ]; then export http_proxy=$HTTP_PROXY https_proxy=$HTTPS_PROXY; fi && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/docs /app/data/chroma_db

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 启动命令
CMD ["streamlit", "run", "web/app.py", \
     "--server.address", "0.0.0.0", \
     "--server.port", "8501", \
     "--server.headless", "true", \
     "--browser.gatherUsageStats", "false"]
