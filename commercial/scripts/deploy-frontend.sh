#!/bin/bash

#####################################################################
# iDoctor Commercial 前端部署脚本
#
# 用途: 自动构建并部署前端到 Nginx
# 使用: bash commercial/scripts/deploy-frontend.sh [选项]
#
# 选项:
#   --build-only    仅构建，不部署
#   --deploy-only   仅部署，不构建
#   --skip-nginx    跳过 Nginx 配置
#   --help          显示帮助信息
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
NC='\033[0m' # No Color

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/commercial/frontend"
NGINX_CONFIG_SRC="$PROJECT_ROOT/commercial/nginx/idoctor-commercial.conf"
NGINX_SITE_AVAILABLE="/etc/nginx/sites-available/idoctor-commercial.conf"
NGINX_SITE_ENABLED="/etc/nginx/sites-enabled/idoctor-commercial.conf"
DEPLOY_DIR="/var/www/idoctor-commercial"
BACKUP_DIR="/var/backups/idoctor-commercial"

# 标志
BUILD_ONLY=false
DEPLOY_ONLY=false
SKIP_NGINX=false

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

# 显示帮助信息
show_help() {
    cat << EOF
iDoctor Commercial 前端部署脚本

用法:
    bash $0 [选项]

选项:
    --build-only    仅构建前端，不部署到服务器
    --deploy-only   仅部署已构建的文件，不重新构建
    --skip-nginx    跳过 Nginx 配置步骤
    --help          显示此帮助信息

示例:
    # 完整部署（构建 + 部署 + 配置 Nginx）
    bash $0

    # 仅构建
    bash $0 --build-only

    # 仅部署
    bash $0 --deploy-only

    # 部署但不配置 Nginx
    bash $0 --skip-nginx

环境要求:
    - Node.js >= 16
    - npm >= 7
    - Nginx (如果需要配置)
    - sudo 权限 (如果需要部署到系统目录)

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build-only)
                BUILD_ONLY=true
                shift
                ;;
            --deploy-only)
                DEPLOY_ONLY=true
                shift
                ;;
            --skip-nginx)
                SKIP_NGINX=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 检查前置条件
check_prerequisites() {
    info "检查前置条件..."

    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        error "Node.js 未安装。请先安装 Node.js >= 16"
        exit 1
    fi

    NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -lt 16 ]; then
        error "Node.js 版本过低 (当前: $NODE_VERSION, 需要: >= 16)"
        exit 1
    fi
    success "Node.js $(node -v) ✓"

    # 检查 npm
    if ! command -v npm &> /dev/null; then
        error "npm 未安装"
        exit 1
    fi
    success "npm $(npm -v) ✓"

    # 如果需要配置 Nginx，检查 Nginx
    if [ "$SKIP_NGINX" = false ] && [ "$BUILD_ONLY" = false ]; then
        if ! command -v nginx &> /dev/null; then
            warning "Nginx 未安装，将跳过 Nginx 配置"
            SKIP_NGINX=true
        else
            success "Nginx $(nginx -v 2>&1 | grep -oP 'nginx/\K[0-9.]+') ✓"
        fi
    fi
}

# 构建前端
build_frontend() {
    info "开始构建前端..."

    cd "$FRONTEND_DIR"

    # 安装依赖
    if [ ! -d "node_modules" ]; then
        info "安装依赖..."
        npm install
    else
        info "依赖已安装，跳过 npm install"
    fi

    # 构建
    info "运行生产环境构建..."
    npm run build

    # 验证构建产物
    if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
        error "构建失败：dist 目录不存在或缺少 index.html"
        exit 1
    fi

    DIST_SIZE=$(du -sh dist | cut -f1)
    success "构建完成！产物大小: $DIST_SIZE"

    # 如果只构建，这里就结束
    if [ "$BUILD_ONLY" = true ]; then
        success "✨ 构建完成（位于: $FRONTEND_DIR/dist）"
        exit 0
    fi
}

# 备份当前部署
backup_current_deployment() {
    if [ -d "$DEPLOY_DIR" ]; then
        info "备份当前部署..."

        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"

        sudo mkdir -p "$BACKUP_DIR"
        sudo cp -r "$DEPLOY_DIR" "$BACKUP_PATH"

        success "备份完成: $BACKUP_PATH"

        # 保留最近5个备份
        BACKUP_COUNT=$(sudo ls -1 "$BACKUP_DIR" | wc -l)
        if [ "$BACKUP_COUNT" -gt 5 ]; then
            info "清理旧备份（保留最近5个）..."
            sudo ls -t "$BACKUP_DIR" | tail -n +6 | xargs -I {} sudo rm -rf "$BACKUP_DIR/{}"
        fi
    fi
}

# 部署前端文件
deploy_frontend() {
    info "部署前端文件..."

    # 创建部署目录
    sudo mkdir -p "$DEPLOY_DIR"

    # 备份当前部署
    backup_current_deployment

    # 复制新文件
    info "复制构建产物到 $DEPLOY_DIR ..."
    sudo cp -r "$FRONTEND_DIR/dist/"* "$DEPLOY_DIR/"

    # 设置权限
    sudo chown -R www-data:www-data "$DEPLOY_DIR"
    sudo chmod -R 755 "$DEPLOY_DIR"

    # 验证部署
    if [ ! -f "$DEPLOY_DIR/index.html" ]; then
        error "部署失败：index.html 不存在"
        exit 1
    fi

    success "前端文件部署完成"
}

# 配置 Nginx
configure_nginx() {
    if [ "$SKIP_NGINX" = true ]; then
        warning "跳过 Nginx 配置"
        return
    fi

    info "配置 Nginx..."

    # 检查配置文件是否存在
    if [ ! -f "$NGINX_CONFIG_SRC" ]; then
        error "Nginx 配置源文件不存在: $NGINX_CONFIG_SRC"
        exit 1
    fi

    # 复制配置到 sites-available
    sudo cp "$NGINX_CONFIG_SRC" "$NGINX_SITE_AVAILABLE"
    success "配置文件已复制到 $NGINX_SITE_AVAILABLE"

    # 创建软链接到 sites-enabled
    if [ ! -L "$NGINX_SITE_ENABLED" ]; then
        sudo ln -s "$NGINX_SITE_AVAILABLE" "$NGINX_SITE_ENABLED"
        success "创建软链接到 sites-enabled"
    else
        info "软链接已存在，跳过"
    fi

    # 测试 Nginx 配置
    info "测试 Nginx 配置..."
    if sudo nginx -t 2>&1 | grep -q "syntax is ok"; then
        success "Nginx 配置测试通过"
    else
        error "Nginx 配置测试失败"
        sudo nginx -t
        exit 1
    fi

    # 重载 Nginx
    info "重载 Nginx..."
    sudo systemctl reload nginx || sudo nginx -s reload

    success "Nginx 已重载"
}

# 验证部署
verify_deployment() {
    info "验证部署..."

    # 检查文件权限
    if [ ! -r "$DEPLOY_DIR/index.html" ]; then
        error "index.html 权限错误"
        exit 1
    fi

    # 检查 Nginx 是否运行
    if ! systemctl is-active --quiet nginx; then
        warning "Nginx 未运行"
        sudo systemctl start nginx
    fi

    # 测试本地访问
    if command -v curl &> /dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:55305/)
        if [ "$HTTP_CODE" = "200" ]; then
            success "本地访问测试通过 (HTTP $HTTP_CODE)"
        else
            warning "本地访问返回 HTTP $HTTP_CODE"
        fi
    fi

    success "✨ 部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "======================================"
    echo "      部署完成！"
    echo "======================================"
    echo ""
    echo "📦 部署位置: $DEPLOY_DIR"
    echo "🌐 访问地址: http://ai.bygpu.com:55305"
    echo "📊 Nginx 配置: $NGINX_SITE_AVAILABLE"
    echo "📝 Nginx 日志:"
    echo "   - 访问日志: /var/log/nginx/idoctor-commercial-access.log"
    echo "   - 错误日志: /var/log/nginx/idoctor-commercial-error.log"
    echo ""
    echo "🔍 常用命令:"
    echo "   - 查看日志: sudo tail -f /var/log/nginx/idoctor-commercial-*.log"
    echo "   - 重载 Nginx: sudo nginx -s reload"
    echo "   - 查看状态: systemctl status nginx"
    echo ""
    if [ -d "$BACKUP_DIR" ]; then
        echo "💾 备份位置: $BACKUP_DIR"
        echo "   最新备份: $(sudo ls -t $BACKUP_DIR | head -1)"
        echo ""
    fi
    echo "======================================"
    echo ""
}

# 主流程
main() {
    echo ""
    echo "======================================"
    echo "  iDoctor Commercial 前端部署"
    echo "======================================"
    echo ""

    # 解析参数
    parse_args "$@"

    # 检查前置条件
    check_prerequisites

    # 如果只部署，跳过构建
    if [ "$DEPLOY_ONLY" = false ]; then
        build_frontend
    else
        # 验证 dist 目录存在
        if [ ! -d "$FRONTEND_DIR/dist" ]; then
            error "dist 目录不存在，请先构建或去掉 --deploy-only 选项"
            exit 1
        fi
        info "使用已存在的构建产物: $FRONTEND_DIR/dist"
    fi

    # 如果只构建，前面已经退出了，这里不会执行

    # 部署
    deploy_frontend

    # 配置 Nginx
    configure_nginx

    # 验证
    verify_deployment

    # 显示部署信息
    show_deployment_info
}

# 执行主流程
main "$@"
