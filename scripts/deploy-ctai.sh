#!/bin/bash
# CTAI Complete Deployment Script
# 用于一键部署整个 CTAI 应用（前端 + 后端）

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录的父目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CTAI Complete Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 环境参数：dev 或 prod（默认 dev）
ENVIRONMENT="${1:-dev}"
echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"
echo ""

# 步骤 1: 检查 Commercial 模块是否已启动
echo -e "${BLUE}[1/5] Checking Commercial Module...${NC}"
if ! docker ps | grep -q idoctor_commercial_nginx; then
    echo -e "${RED}❌ Commercial module not running!${NC}"
    echo -e "${YELLOW}Starting Commercial module first...${NC}"
    cd "$PROJECT_ROOT/commercial"
    bash scripts/deploy-all.sh "$ENVIRONMENT"
    cd "$PROJECT_ROOT"
else
    echo -e "${GREEN}✅ Commercial module is running${NC}"
fi
echo ""

# 步骤 2: 构建 CTAI 前端
echo -e "${BLUE}[2/5] Building CTAI Frontend...${NC}"
cd "$PROJECT_ROOT/CTAI_web"

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing npm dependencies...${NC}"
    npm install
fi

# 构建
if [ "$ENVIRONMENT" == "dev" ]; then
    echo -e "${YELLOW}Building for development...${NC}"
    npm run build:dev || npm run build
else
    echo -e "${YELLOW}Building for production...${NC}"
    npm run build
fi

if [ ! -d "dist" ]; then
    echo -e "${RED}❌ Frontend build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Frontend built successfully${NC}"
echo ""

# 步骤 3: 复制前端到 Nginx
echo -e "${BLUE}[3/5] Deploying Frontend to Nginx...${NC}"
NGINX_CTAI_DIR="$PROJECT_ROOT/commercial/docker/nginx/html/ctai"
mkdir -p "$NGINX_CTAI_DIR"

echo -e "${YELLOW}Copying dist/ to Nginx directory...${NC}"
cp -r dist/* "$NGINX_CTAI_DIR/"
echo -e "${GREEN}✅ Frontend deployed to Nginx${NC}"
echo ""

# 步骤 4: 启动 CTAI 后端
echo -e "${BLUE}[4/5] Starting CTAI Backend...${NC}"
cd "$PROJECT_ROOT"

# 使用专用的后端启动脚本
bash "$SCRIPT_DIR/start-ctai-backend.sh" "$ENVIRONMENT"
echo -e "${GREEN}✅ Backend started${NC}"
echo ""

# 步骤 5: 重启 Nginx（应用前端更新）
echo -e "${BLUE}[5/5] Restarting Nginx...${NC}"
docker restart idoctor_commercial_nginx
sleep 2
echo -e "${GREEN}✅ Nginx restarted${NC}"
echo ""

# 完成
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ CTAI Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 显示访问信息
if [ "$ENVIRONMENT" == "dev" ]; then
    NGINX_PORT=3000
    echo -e "${YELLOW}Development Environment:${NC}"
    echo -e "  🌐 Commercial Frontend: ${GREEN}http://localhost:$NGINX_PORT${NC}"
    echo -e "  🌐 CTAI Frontend:       ${GREEN}http://localhost:$NGINX_PORT/ctai${NC}"
    echo -e "  🔌 CTAI Backend API:    ${GREEN}http://localhost:$NGINX_PORT/api/ctai${NC}"
    echo -e "  🔌 Direct Backend:      ${GREEN}http://localhost:4200${NC}"
    echo -e "  📊 Backend Health:      ${GREEN}http://localhost:4200/health${NC}"
else
    echo -e "${YELLOW}Production Environment:${NC}"
    echo -e "  🌐 Commercial Frontend: ${GREEN}http://ai.bygpu.com:55305${NC}"
    echo -e "  🌐 CTAI Frontend:       ${GREEN}http://ai.bygpu.com:55305/ctai${NC}"
    echo -e "  🔌 CTAI Backend API:    ${GREEN}http://ai.bygpu.com:55305/api/ctai${NC}"
fi
echo ""

# 显示服务状态
echo -e "${YELLOW}Service Status:${NC}"
echo -e "${BLUE}Docker Containers:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep idoctor || echo "No iDoctor containers found"
echo ""
echo -e "${BLUE}CTAI Backend Process:${NC}"
BACKEND_PID=$(pgrep -f "uvicorn app:app" || echo "")
if [ -n "$BACKEND_PID" ]; then
    echo -e "  ${GREEN}✅ Running (PID: $BACKEND_PID)${NC}"
else
    echo -e "  ${RED}❌ Not running${NC}"
fi
echo ""

# 使用说明
echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "  📝 View backend logs:   ${BLUE}tail -f $PROJECT_ROOT/app.log${NC}"
echo -e "  📝 View nginx logs:     ${BLUE}docker logs -f idoctor_commercial_nginx${NC}"
echo -e "  🔄 Restart backend:     ${BLUE}bash $SCRIPT_DIR/start-ctai-backend.sh $ENVIRONMENT${NC}"
echo -e "  🔄 Restart all:         ${BLUE}bash $SCRIPT_DIR/deploy-ctai.sh $ENVIRONMENT${NC}"
echo -e "  ✅ Check services:      ${BLUE}bash $SCRIPT_DIR/check-services.sh${NC}"
echo ""
