#!/bin/bash

#####################################################################
# iDoctor Commercial 一键部署脚本
#
# 用途: 构建前端、启动 Docker 服务（包括 Nginx）
# 使用: bash commercial/scripts/deploy-all.sh [环境]
#
# 环境选项:
#   dev   - 本地开发环境（默认）
#   prod  - 生产环境
#
# 作者: iDoctor Team
# 日期: 2025-01-19
#####################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMMERCIAL_ROOT="$PROJECT_ROOT/commercial"
FRONTEND_DIR="$COMMERCIAL_ROOT/frontend"
DOCKER_DIR="$COMMERCIAL_ROOT/docker"

# 环境参数
ENVIRONMENT="${1:-dev}"

# 打印带颜色的消息
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

step() {
    echo -e "${CYAN}▶ $1${NC}"
}

# 显示 Banner
show_banner() {
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   iDoctor Commercial 一键部署                             ║
║                                                           ║
║   包含: 前端构建 + Nginx + 认证服务 + 支付服务            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
}

# 检查前置条件
check_prerequisites() {
    step "检查前置条件..."

    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        error "Node.js 未安装。请先安装 Node.js >= 16"
        exit 1
    fi
    info "Node.js $(node -v) ✓"

    # 检查 npm
    if ! command -v npm &> /dev/null; then
        error "npm 未安装"
        exit 1
    fi
    info "npm $(npm -v) ✓"

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        error "Docker 未安装。请先安装 Docker"
        exit 1
    fi
    info "Docker $(docker --version | sed -n 's/.*version \([0-9.]*\).*/\1/p') ✓"

    # 检查 Docker Compose
    if ! docker compose version &> /dev/null; then
        error "Docker Compose 未安装"
        exit 1
    fi
    info "Docker Compose $(docker compose version --short) ✓"

    # 检查 wget (SAM2 模型下载需要)
    if ! command -v wget &> /dev/null; then
        warning "wget 未安装。SAM2 模型下载需要 wget"
        warning "请安装 wget: brew install wget (macOS) 或 apt-get install wget (Linux)"
    else
        info "wget ✓"
    fi

    success "前置条件检查通过"
}

# 构建前端
build_frontend() {
    step "构建前端应用..."

    cd "$FRONTEND_DIR"

    # 安装依赖
    if [ ! -d "node_modules" ]; then
        info "安装前端依赖..."
        npm install
    else
        info "依赖已安装，跳过 npm install"
    fi

    # 根据环境选择构建命令
    if [ "$ENVIRONMENT" = "prod" ]; then
        info "运行生产环境构建..."
        npm run build:prod
    else
        info "运行开发环境构建..."
        npm run build:dev
    fi

    # 验证构建产物
    if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
        error "构建失败：dist 目录不存在或缺少 index.html"
        exit 1
    fi

    DIST_SIZE=$(du -sh dist | cut -f1)
    success "前端构建完成！产物大小: $DIST_SIZE"
}

# 设置 SAM2 模型
setup_sam2_model() {
    step "设置 SAM2 模型..."

    # SAM2 模型脚本路径
    SAM2_SETUP_SCRIPT="$PROJECT_ROOT/scripts/setup_sam2_model.sh"

    if [ ! -f "$SAM2_SETUP_SCRIPT" ]; then
        error "SAM2 设置脚本不存在: $SAM2_SETUP_SCRIPT"
        exit 1
    fi

    # 检查 Docker volume 是否存在且包含模型
    DOCKER_VOLUME_NAME="docker_sam2_models"
    SAM2_MODEL_NAME="sam2_hiera_large.pt"

    info "检查 SAM2 模型是否已部署..."

    if docker volume inspect "$DOCKER_VOLUME_NAME" &> /dev/null; then
        # Volume 存在，检查是否有模型文件
        MODEL_CHECK=$(docker run --rm -v "$DOCKER_VOLUME_NAME:/models" alpine ls "/models/$SAM2_MODEL_NAME" 2>/dev/null || echo "")

        if [ -n "$MODEL_CHECK" ]; then
            success "SAM2 模型已存在，跳过下载"
            return 0
        fi
    fi

    # 模型不存在，需要下载
    warning "SAM2 模型未找到，需要下载（约 2GB）"

    if [ "$ENVIRONMENT" = "prod" ]; then
        info "生产环境：自动执行 SAM2 模型部署..."
        bash "$SAM2_SETUP_SCRIPT" --production
    else
        read -p "是否现在下载 SAM2 模型? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            bash "$SAM2_SETUP_SCRIPT"
        else
            warning "跳过 SAM2 模型下载。SAM2 服务将在 mock 模式下运行"
            warning "稍后可运行: bash $SAM2_SETUP_SCRIPT"
        fi
    fi

    success "SAM2 模型设置完成"
}

# 启动 Docker 服务
start_docker_services() {
    step "启动 Docker 服务..."

    cd "$DOCKER_DIR"

    # 根据环境选择配置文件
    if [ "$ENVIRONMENT" = "prod" ]; then
        info "使用生产环境配置..."

        # 检查 .env.prod 文件
        if [ ! -f ".env.prod" ]; then
            warning ".env.prod 文件不存在，从示例文件创建..."
            cp .env.prod.example .env.prod
            warning "请编辑 .env.prod 文件配置生产环境参数"
            read -p "是否继续部署? (y/N): " confirm
            if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                info "部署已取消"
                exit 0
            fi
        fi

        # 使用生产配置
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
        ENV_FILE="--env-file .env.prod"
    else
        info "使用本地开发环境配置..."
        COMPOSE_FILES="-f docker-compose.yml"
        ENV_FILE=""
    fi

    # 停止现有服务
    info "停止现有服务..."
    docker compose $COMPOSE_FILES down

    # 构建镜像
    info "构建 Docker 镜像..."
    docker compose $COMPOSE_FILES build

    # 启动服务
    info "启动服务..."
    docker compose $COMPOSE_FILES $ENV_FILE up -d

    # 等待服务启动
    info "等待服务启动..."
    sleep 5

    # 检查服务状态
    info "检查服务状态..."
    docker compose $COMPOSE_FILES ps

    success "Docker 服务启动完成"
}

# 验证部署
verify_deployment() {
    step "验证部署..."

    cd "$DOCKER_DIR"

    # 获取配置
    if [ "$ENVIRONMENT" = "prod" ]; then
        source .env.prod 2>/dev/null || true
        NGINX_URL="http://${NGINX_SERVER_NAME:-localhost}:${NGINX_EXTERNAL_PORT:-55305}"
    else
        NGINX_URL="http://localhost:3000"
    fi

    # 检查服务健康状态
    info "检查容器健康状态..."
    CONTAINERS=(
        "idoctor_commercial_db"
        "idoctor_auth_service"
        "idoctor_payment_service"
        "idoctor_sam2_service"
        "idoctor_commercial_nginx"
    )

    ALL_HEALTHY=true
    for container in "${CONTAINERS[@]}"; do
        if docker ps | grep -q "$container"; then
            success "✓ $container 运行中"
        else
            error "✗ $container 未运行"
            ALL_HEALTHY=false
        fi
    done

    # 测试 Nginx 健康检查
    if command -v curl &> /dev/null; then
        info "测试 Nginx 健康检查..."
        if curl -sf "$NGINX_URL/health" > /dev/null; then
            success "✓ Nginx 健康检查通过"
        else
            warning "✗ Nginx 健康检查失败"
            ALL_HEALTHY=false
        fi

        # 测试 API 代理
        info "测试 API 代理..."
        if curl -sf "$NGINX_URL/api/auth/health" > /dev/null; then
            success "✓ 认证 API 代理正常"
        else
            warning "✗ 认证 API 代理失败"
        fi

        if curl -sf "$NGINX_URL/api/payment/health" > /dev/null; then
            success "✓ 支付 API 代理正常"
        else
            warning "✗ 支付 API 代理失败"
        fi

        # 测试 SAM2 服务
        info "测试 SAM2 服务..."
        if curl -sf "http://localhost:8000/health" > /dev/null; then
            success "✓ SAM2 服务健康检查通过"

            # 检查模型是否加载
            SAM2_HEALTH=$(curl -s "http://localhost:8000/health" 2>/dev/null || echo "{}")
            if echo "$SAM2_HEALTH" | grep -q '"model_loaded":\s*true'; then
                success "✓ SAM2 模型已加载"
            else
                warning "✗ SAM2 模型未加载（可能运行在 mock 模式）"
            fi
        else
            warning "✗ SAM2 服务健康检查失败"
        fi
    fi

    if [ "$ALL_HEALTHY" = true ]; then
        success "部署验证通过！"
    else
        warning "部署验证发现问题，请检查日志"
    fi
}

# 显示部署信息
show_deployment_info() {
    cd "$DOCKER_DIR"

    if [ "$ENVIRONMENT" = "prod" ]; then
        source .env.prod 2>/dev/null || true
        NGINX_URL="http://${NGINX_SERVER_NAME:-ai.bygpu.com}:${NGINX_EXTERNAL_PORT:-55305}"
    else
        NGINX_URL="http://localhost:3000"
    fi

    echo ""
    echo "======================================"
    echo "      部署完成！"
    echo "======================================"
    echo ""
    echo "🌐 访问地址: $NGINX_URL"
    echo ""
    echo "📊 服务状态:"
    echo "   - 前端: $NGINX_URL"
    echo "   - 认证 API: $NGINX_URL/api/auth/docs"
    echo "   - 支付 API: $NGINX_URL/api/payment/docs"
    echo "   - SAM2 服务: http://localhost:8000/docs"
    echo ""
    echo "🔍 常用命令:"
    echo "   - 查看日志: cd $DOCKER_DIR && docker compose logs -f"
    echo "   - 停止服务: cd $DOCKER_DIR && docker compose down"
    echo "   - 重启服务: cd $DOCKER_DIR && docker compose restart"
    echo ""
    echo "📝 Nginx 日志:"
    echo "   - 访问日志: docker exec idoctor_commercial_nginx tail -f /var/log/nginx/idoctor-commercial-access.log"
    echo "   - 错误日志: docker exec idoctor_commercial_nginx tail -f /var/log/nginx/idoctor-commercial-error.log"
    echo ""
    echo "🤖 SAM2 服务:"
    echo "   - 查看日志: docker logs -f idoctor_sam2_service"
    echo "   - 健康检查: curl http://localhost:8000/health"
    echo "   - 重新部署模型: bash $PROJECT_ROOT/scripts/setup_sam2_model.sh"
    echo ""
    echo "======================================"
    echo ""
}

# 主流程
main() {
    show_banner
    echo ""
    info "环境: $ENVIRONMENT"
    echo ""

    check_prerequisites
    echo ""

    build_frontend
    echo ""

    setup_sam2_model
    echo ""

    start_docker_services
    echo ""

    verify_deployment
    echo ""

    show_deployment_info
}

# 执行主流程
main
