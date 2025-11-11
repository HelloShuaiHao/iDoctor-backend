#!/bin/bash
# CTAI Frontend Startup Script
# 用于启动/构建 CTAI Vue 前端应用

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
echo -e "${GREEN}CTAI Frontend Startup Script${NC}"
echo -e "${GREEN}========================================${NC}"

# 环境参数：dev 或 prod（默认 dev）
ENVIRONMENT="${1:-dev}"
echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"

# 切换到前端目录
FRONTEND_DIR="$PROJECT_ROOT/CTAI_web"
cd "$FRONTEND_DIR"

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo -e "${RED}❌ node_modules not found!${NC}"
    echo -e "${YELLOW}Installing dependencies...${NC}"
    npm install
fi

# 检查环境配置文件
if [ "$ENVIRONMENT" == "dev" ]; then
    if [ ! -f ".env.development" ]; then
        echo -e "${RED}❌ .env.development not found!${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Using .env.development${NC}"
else
    if [ ! -f ".env.production" ]; then
        echo -e "${RED}❌ .env.production not found!${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Using .env.production${NC}"
fi

if [ "$ENVIRONMENT" == "dev" ]; then
    # 开发模式：启动开发服务器
    echo -e "${GREEN}Starting CTAI Frontend (Development Mode)...${NC}"
    echo -e "${YELLOW}Features: Hot reload, dev server${NC}"

    # 检查端口
    PORT=7500
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${RED}❌ Port $PORT is already in use!${NC}"
        echo -e "${YELLOW}Killing process on port $PORT...${NC}"
        lsof -ti:$PORT | xargs kill -9 || true
        sleep 1
    fi

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Starting Vue Dev Server...${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${YELLOW}Port:${NC} 7500"
    echo -e "${YELLOW}URL:${NC} http://localhost:7500"
    echo ""

    # 启动开发服务器（前台运行）
    npm run serve
else
    # 生产模式：构建静态文件
    echo -e "${GREEN}Building CTAI Frontend (Production Mode)...${NC}"
    echo -e "${YELLOW}Features: Minified, optimized${NC}"

    # 清理旧的构建文件
    if [ -d "dist" ]; then
        echo -e "${YELLOW}Cleaning old dist directory...${NC}"
        rm -rf dist
    fi

    # 构建
    echo -e "${YELLOW}Building...${NC}"
    npm run build

    # 检查构建结果
    if [ ! -d "dist" ]; then
        echo -e "${RED}❌ Build failed! dist directory not created.${NC}"
        exit 1
    fi

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ CTAI Frontend built successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${YELLOW}Output:${NC} $FRONTEND_DIR/dist"
    echo -e "${YELLOW}Files:${NC}"
    ls -lh dist/ | head -10
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  1. Copy dist/ to Nginx directory"
    echo -e "  2. Update Nginx config to serve /ctai from dist/"
    echo -e "  3. Restart Nginx"
    echo ""

    # 检查是否需要复制到 Nginx
    read -p "Copy to Nginx directory? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        NGINX_CTAI_DIR="$PROJECT_ROOT/commercial/docker/nginx/html/ctai"
        echo -e "${YELLOW}Copying to Nginx: $NGINX_CTAI_DIR${NC}"

        # 创建目录（如果不存在）
        mkdir -p "$NGINX_CTAI_DIR"

        # 复制文件
        cp -r dist/* "$NGINX_CTAI_DIR/"

        echo -e "${GREEN}✅ Copied to Nginx directory${NC}"
        echo -e "${YELLOW}Restart Nginx to apply changes:${NC}"
        echo -e "  docker restart idoctor_commercial_nginx"
    fi
fi
