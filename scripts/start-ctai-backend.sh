#!/bin/bash
# CTAI Backend Startup Script
# 用于启动 CTAI FastAPI 后端服务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录的父目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CTAI Backend Startup Script${NC}"
echo -e "${GREEN}========================================${NC}"

# 环境参数：dev 或 prod（默认 dev）
ENVIRONMENT="${1:-dev}"
echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo -e "${YELLOW}Please create .env file based on .env.example${NC}"
    exit 1
fi

# 加载环境变量
echo -e "${YELLOW}Loading environment variables from .env...${NC}"
export $(grep -v '^#' .env | xargs)

# 安装/更新依赖
if [ "$ENVIRONMENT" == "dev" ]; then
    echo -e "${YELLOW}Installing dependencies (dev mode)...${NC}"
    pip install -q -r requirements.txt
fi

# 停止旧进程
echo -e "${YELLOW}Stopping old processes...${NC}"
pkill -f "uvicorn app:app" || true
sleep 2

# 检查端口是否被占用
PORT=4200
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${RED}❌ Port $PORT is already in use!${NC}"
    echo -e "${YELLOW}Killing process on port $PORT...${NC}"
    lsof -ti:$PORT | xargs kill -9 || true
    sleep 1
fi

# 启动服务
if [ "$ENVIRONMENT" == "dev" ]; then
    echo -e "${GREEN}Starting CTAI Backend (Development Mode)...${NC}"
    echo -e "${YELLOW}Features: Auto-reload enabled${NC}"
    nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 4200 --reload > app.log 2>&1 &
else
    echo -e "${GREEN}Starting CTAI Backend (Production Mode)...${NC}"
    echo -e "${YELLOW}Features: Multiple workers${NC}"
    nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 4200 --workers 4 > app.log 2>&1 &
fi

# 等待启动
sleep 3

# 检查进程
PID=$(pgrep -f "uvicorn app:app" || echo "")
if [ -z "$PID" ]; then
    echo -e "${RED}❌ Failed to start CTAI backend!${NC}"
    echo -e "${YELLOW}Check app.log for details:${NC}"
    tail -20 app.log
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ CTAI Backend started successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}PID:${NC} $PID"
echo -e "${YELLOW}Port:${NC} 4200"
echo -e "${YELLOW}Mode:${NC} $ENVIRONMENT"
echo -e "${YELLOW}Log:${NC} tail -f app.log"
echo -e "${YELLOW}Health:${NC} curl http://localhost:4200/health"
echo ""

# 显示最后几行日志
echo -e "${YELLOW}Recent logs:${NC}"
tail -10 app.log

echo ""
echo -e "${GREEN}Access the API at: http://localhost:4200${NC}"
