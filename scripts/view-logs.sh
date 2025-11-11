#!/bin/bash
# Log Viewer Script
# 快速查看各个服务的日志

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
echo -e "${BLUE}  iDoctor Log Viewer${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 显示菜单
echo -e "${YELLOW}Select a service to view logs:${NC}"
echo ""
echo -e "  ${GREEN}1${NC} - CTAI Backend (app.log)"
echo -e "  ${GREEN}2${NC} - Nginx (Docker)"
echo -e "  ${GREEN}3${NC} - Auth Service (Docker)"
echo -e "  ${GREEN}4${NC} - Payment Service (Docker)"
echo -e "  ${GREEN}5${NC} - SAM2 Service (Docker)"
echo -e "  ${GREEN}6${NC} - PostgreSQL (Docker)"
echo -e "  ${GREEN}7${NC} - All Docker Services"
echo -e "  ${GREEN}q${NC} - Quit"
echo ""

read -p "Enter choice: " choice

case $choice in
    1)
        echo -e "${YELLOW}Viewing CTAI Backend logs (Ctrl+C to exit)...${NC}"
        tail -f "$PROJECT_ROOT/app.log"
        ;;
    2)
        echo -e "${YELLOW}Viewing Nginx logs (Ctrl+C to exit)...${NC}"
        docker logs -f idoctor_commercial_nginx
        ;;
    3)
        echo -e "${YELLOW}Viewing Auth Service logs (Ctrl+C to exit)...${NC}"
        docker logs -f idoctor_auth_service
        ;;
    4)
        echo -e "${YELLOW}Viewing Payment Service logs (Ctrl+C to exit)...${NC}"
        docker logs -f idoctor_payment_service
        ;;
    5)
        echo -e "${YELLOW}Viewing SAM2 Service logs (Ctrl+C to exit)...${NC}"
        docker logs -f idoctor_sam2_service
        ;;
    6)
        echo -e "${YELLOW}Viewing PostgreSQL logs (Ctrl+C to exit)...${NC}"
        docker logs -f idoctor_commercial_db
        ;;
    7)
        echo -e "${YELLOW}Viewing all Docker services (Ctrl+C to exit)...${NC}"
        cd "$PROJECT_ROOT/commercial/docker"
        docker-compose logs -f
        ;;
    q|Q)
        echo -e "${GREEN}Goodbye!${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
