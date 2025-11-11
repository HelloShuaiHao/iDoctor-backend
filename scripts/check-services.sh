#!/bin/bash
# Service Health Check Script
# 检查所有 iDoctor 服务的运行状态

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  iDoctor Service Health Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 Docker 容器
echo -e "${YELLOW}[1] Docker Containers${NC}"
echo -e "${BLUE}────────────────────────────────────────${NC}"
CONTAINERS=(
    "idoctor_commercial_nginx"
    "idoctor_auth_service"
    "idoctor_payment_service"
    "idoctor_commercial_db"
    "idoctor_sam2_service"
)

ALL_CONTAINERS_UP=true
for container in "${CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        STATUS=$(docker ps --format '{{.Status}}' --filter "name=^${container}$")
        echo -e "  ✅ ${GREEN}${container}${NC} - ${STATUS}"
    else
        echo -e "  ❌ ${RED}${container}${NC} - Not running"
        ALL_CONTAINERS_UP=false
    fi
done
echo ""

# 检查 CTAI Backend
echo -e "${YELLOW}[2] CTAI Backend${NC}"
echo -e "${BLUE}────────────────────────────────────────${NC}"
BACKEND_PID=$(pgrep -f "uvicorn app:app" || echo "")
if [ -n "$BACKEND_PID" ]; then
    echo -e "  ✅ ${GREEN}Running${NC} (PID: $BACKEND_PID)"

    # 检查健康端点
    if curl -s http://localhost:4200/health > /dev/null 2>&1; then
        echo -e "  ✅ ${GREEN}Health check passed${NC}"
    else
        echo -e "  ⚠️  ${YELLOW}Health check failed${NC}"
    fi
else
    echo -e "  ❌ ${RED}Not running${NC}"
fi
echo ""

# 检查端口占用
echo -e "${YELLOW}[3] Port Status${NC}"
echo -e "${BLUE}────────────────────────────────────────${NC}"
PORTS=(3000 4200 5432 8000 9001 9002)
PORT_NAMES=("Nginx" "CTAI Backend" "PostgreSQL" "SAM2" "Auth Service" "Payment Service")

for i in "${!PORTS[@]}"; do
    PORT=${PORTS[$i]}
    NAME=${PORT_NAMES[$i]}
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        PID=$(lsof -ti:$PORT)
        echo -e "  ✅ ${GREEN}Port $PORT${NC} ($NAME) - In use (PID: $PID)"
    else
        echo -e "  ❌ ${RED}Port $PORT${NC} ($NAME) - Not in use"
    fi
done
echo ""

# 检查数据库连接
echo -e "${YELLOW}[4] Database${NC}"
echo -e "${BLUE}────────────────────────────────────────${NC}"
if docker ps --format '{{.Names}}' | grep -q "^idoctor_commercial_db$"; then
    if docker exec idoctor_commercial_db pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "  ✅ ${GREEN}PostgreSQL is ready${NC}"

        # 检查数据库连接数
        CONN_COUNT=$(docker exec idoctor_commercial_db psql -U postgres -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ')
        if [ -n "$CONN_COUNT" ]; then
            echo -e "  📊 Active connections: ${CONN_COUNT}"
        fi
    else
        echo -e "  ⚠️  ${YELLOW}PostgreSQL not ready${NC}"
    fi
else
    echo -e "  ❌ ${RED}PostgreSQL container not running${NC}"
fi
echo ""

# 检查 SAM2 服务
echo -e "${YELLOW}[5] SAM2 Service${NC}"
echo -e "${BLUE}────────────────────────────────────────${NC}"
if docker ps --format '{{.Names}}' | grep -q "^idoctor_sam2_service$"; then
    SAM2_HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo "{}")
    if echo "$SAM2_HEALTH" | grep -q "healthy"; then
        echo -e "  ✅ ${GREEN}SAM2 service is healthy${NC}"

        MODEL_LOADED=$(echo "$SAM2_HEALTH" | grep -o '"model_loaded":[^,}]*' | cut -d':' -f2)
        if [ "$MODEL_LOADED" == "true" ]; then
            echo -e "  ✅ ${GREEN}Model loaded${NC}"
        else
            echo -e "  ⚠️  ${YELLOW}Model not loaded${NC}"
        fi
    else
        echo -e "  ⚠️  ${YELLOW}SAM2 health check failed${NC}"
    fi
else
    echo -e "  ❌ ${RED}SAM2 container not running${NC}"
fi
echo ""

# 总结
echo -e "${BLUE}========================================${NC}"
if [ "$ALL_CONTAINERS_UP" = true ] && [ -n "$BACKEND_PID" ]; then
    echo -e "${GREEN}  ✅ All services are running!${NC}"
else
    echo -e "${RED}  ⚠️  Some services are down${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo -e "  1. Start Commercial: ${BLUE}cd commercial && bash scripts/deploy-all.sh dev${NC}"
    echo -e "  2. Start CTAI:       ${BLUE}bash scripts/deploy-ctai.sh dev${NC}"
    echo -e "  3. View logs:        ${BLUE}bash scripts/view-logs.sh${NC}"
fi
echo -e "${BLUE}========================================${NC}"
