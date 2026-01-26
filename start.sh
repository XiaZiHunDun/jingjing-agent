#!/bin/bash
#
# Agent Learn 2 - 一键启动脚本
#
# 使用方式：
#   chmod +x start.sh
#   ./start.sh
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ENV="agent-learn"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════╗"
echo "║        🤖 Agent Learn 2 启动脚本           ║"
echo "╚════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查 conda 环境
echo -e "${YELLOW}[1/4] 检查 conda 环境...${NC}"
if ! conda info --envs | grep -q "$CONDA_ENV"; then
    echo -e "${RED}错误: conda 环境 '$CONDA_ENV' 不存在${NC}"
    echo "请先运行: conda create -n $CONDA_ENV python=3.11"
    exit 1
fi
echo -e "${GREEN}✓ conda 环境已就绪${NC}"

# 激活环境
echo -e "${YELLOW}[2/4] 激活环境...${NC}"
source ~/miniconda3/bin/activate $CONDA_ENV
echo -e "${GREEN}✓ 环境已激活: $CONDA_ENV${NC}"

# 检查端口
echo -e "${YELLOW}[3/4] 检查端口 8501...${NC}"
if ss -tlnp | grep -q ":8501"; then
    echo -e "${YELLOW}端口 8501 已被占用，正在停止旧服务...${NC}"
    pkill -f "streamlit run" 2>/dev/null || true
    sleep 2
fi
echo -e "${GREEN}✓ 端口可用${NC}"

# 启动服务
echo -e "${YELLOW}[4/4] 启动 Streamlit 服务...${NC}"
cd "$PROJECT_DIR"

# 获取 IP 地址
IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🚀 服务启动成功！${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo -e "  本地访问: ${BLUE}http://localhost:8501${NC}"
echo -e "  远程访问: ${BLUE}http://${IP_ADDR}:8501${NC}"
echo ""
echo -e "  ${YELLOW}按 Ctrl+C 停止服务${NC}"
echo ""

# 启动 Streamlit（前台运行）
streamlit run web/app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false
