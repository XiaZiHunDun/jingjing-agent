#!/bin/bash
# ============================================================
# Agent Learn 2 - Docker 构建与运行脚本
# ============================================================

set -e

PROJECT_NAME="jingjing-agent"
IMAGE_NAME="jingjing-agent:latest"

echo "╭──────────────────────────────────────╮"
echo "│  🐳 晶晶助手 Docker 构建工具         │"
echo "╰──────────────────────────────────────╯"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 缺少 .env 文件，请先创建"
    echo "   可以复制 .env.example 并填入 API Key"
    exit 1
fi

case "$1" in
    build)
        echo "📦 构建 Docker 镜像..."
        docker build -t $IMAGE_NAME .
        echo "✅ 镜像构建完成: $IMAGE_NAME"
        ;;
    
    run)
        echo "🚀 启动容器..."
        docker run -d \
            --name $PROJECT_NAME \
            -p 8501:8501 \
            -v $(pwd)/data:/app/data \
            -v $(pwd)/.env:/app/.env:ro \
            --restart unless-stopped \
            $IMAGE_NAME
        echo "✅ 容器已启动"
        echo "🌐 访问地址: http://localhost:8501"
        ;;
    
    stop)
        echo "⏹️ 停止容器..."
        docker stop $PROJECT_NAME 2>/dev/null || true
        docker rm $PROJECT_NAME 2>/dev/null || true
        echo "✅ 容器已停止"
        ;;
    
    logs)
        echo "📜 查看日志..."
        docker logs -f $PROJECT_NAME
        ;;
    
    compose-up)
        echo "🚀 使用 docker-compose 启动..."
        docker-compose up -d
        echo "✅ 服务已启动"
        echo "🌐 访问地址: http://localhost:8501"
        ;;
    
    compose-down)
        echo "⏹️ 使用 docker-compose 停止..."
        docker-compose down
        echo "✅ 服务已停止"
        ;;
    
    export)
        echo "📤 导出镜像..."
        EXPORT_FILE="jingjing-agent-$(date +%Y%m%d).tar"
        docker save -o $EXPORT_FILE $IMAGE_NAME
        echo "✅ 镜像已导出: $EXPORT_FILE"
        echo "   大小: $(du -h $EXPORT_FILE | cut -f1)"
        echo ""
        echo "💡 在其他机器导入: docker load -i $EXPORT_FILE"
        ;;
    
    *)
        echo "用法: $0 {build|run|stop|logs|compose-up|compose-down|export}"
        echo ""
        echo "命令说明:"
        echo "  build        构建 Docker 镜像"
        echo "  run          运行容器（单独模式）"
        echo "  stop         停止并删除容器"
        echo "  logs         查看容器日志"
        echo "  compose-up   使用 docker-compose 启动"
        echo "  compose-down 使用 docker-compose 停止"
        echo "  export       导出镜像为 tar 文件（用于迁移）"
        ;;
esac
