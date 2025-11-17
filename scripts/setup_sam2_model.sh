#!/bin/bash
################################################################################
# SAM2 模型下载和部署脚本
#
# 用途：下载 SAM2 模型并部署到 Docker volume
# 适用于：本地开发环境和生产服务器
#
# 使用方法：
#   本地测试：./scripts/setup_sam2_model.sh
#   生产环境：./scripts/setup_sam2_model.sh --production
#
# 作者：iDoctor Team
# 日期：2025-11-11
################################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
SAM2_MODEL_URL="https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt"
SAM2_MODEL_NAME="sam2_hiera_large.pt"
LOCAL_MODEL_DIR="$HOME/sam2_models"
DOCKER_VOLUME_NAME="docker_sam2_models"
DOCKER_COMPOSE_DIR="$(cd "$(dirname "$0")/../commercial/docker" && pwd)"

# 检查是否为生产环境
PRODUCTION=false
if [[ "$1" == "--production" ]]; then
    PRODUCTION=true
fi

################################################################################
# 辅助函数
################################################################################

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 未安装，请先安装"
        exit 1
    fi
}

################################################################################
# 主要步骤
################################################################################

step1_check_prerequisites() {
    print_header "步骤 1: 检查环境依赖"

    check_command wget
    check_command docker

    if [ "$PRODUCTION" = true ]; then
        check_command docker-compose
    fi

    print_success "所有依赖已安装"
}

step2_create_model_directory() {
    print_header "步骤 2: 创建模型目录"

    if [ -d "$LOCAL_MODEL_DIR" ]; then
        print_info "模型目录已存在: $LOCAL_MODEL_DIR"
    else
        mkdir -p "$LOCAL_MODEL_DIR"
        print_success "已创建模型目录: $LOCAL_MODEL_DIR"
    fi
}

step3_download_model() {
    print_header "步骤 3: 下载 SAM2 模型"

    local model_path="$LOCAL_MODEL_DIR/$SAM2_MODEL_NAME"

    if [ -f "$model_path" ]; then
        local file_size=$(du -h "$model_path" | cut -f1)
        print_warning "模型文件已存在: $model_path (大小: $file_size)"

        if [ "$PRODUCTION" = true ]; then
            print_info "生产环境：跳过下载，使用现有模型"
            return 0
        else
            read -p "是否重新下载? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "跳过下载，使用现有模型"
                return 0
            fi

            print_info "删除旧模型..."
            rm -f "$model_path"
        fi
    fi

    print_info "开始下载 SAM2.1 Hiera Large 模型..."
    print_info "下载地址: $SAM2_MODEL_URL"
    print_info "目标路径: $model_path"
    print_warning "模型大小约 2GB，请耐心等待..."

    if wget -O "$model_path" "$SAM2_MODEL_URL" --progress=bar:force 2>&1 | tee /dev/stderr | grep -q "100%"; then
        local file_size=$(du -h "$model_path" | cut -f1)
        print_success "模型下载完成! 大小: $file_size"
    else
        print_error "模型下载失败"
        rm -f "$model_path"
        exit 1
    fi
}

step4_copy_to_docker_volume() {
    print_header "步骤 4: 复制模型到 Docker Volume"

    local model_path="$LOCAL_MODEL_DIR/$SAM2_MODEL_NAME"

    # 检查 Docker volume 是否存在
    if ! docker volume inspect "$DOCKER_VOLUME_NAME" &> /dev/null; then
        print_warning "Docker volume 不存在，正在创建..."
        docker volume create "$DOCKER_VOLUME_NAME"
        print_success "已创建 Docker volume: $DOCKER_VOLUME_NAME"
    else
        print_info "Docker volume 已存在: $DOCKER_VOLUME_NAME"
    fi

    # 检查 volume 中是否已有模型
    print_info "检查 Docker volume 中的模型..."
    local existing_model=$(docker run --rm -v "$DOCKER_VOLUME_NAME:/models" alpine ls -lh "/models/$SAM2_MODEL_NAME" 2>/dev/null || echo "")

    if [ -n "$existing_model" ]; then
        print_warning "Docker volume 中已存在模型文件"
        echo "$existing_model"

        if [ "$PRODUCTION" = true ]; then
            print_info "生产环境：跳过复制，使用现有模型"
            return 0
        else
            read -p "是否覆盖? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "跳过复制，使用现有模型"
                return 0
            fi
        fi
    fi

    # 复制模型到 Docker volume
    print_info "正在复制模型到 Docker volume..."
    docker run --rm \
        -v "$DOCKER_VOLUME_NAME:/models" \
        -v "$LOCAL_MODEL_DIR:/source" \
        alpine \
        cp "/source/$SAM2_MODEL_NAME" "/models/"

    print_success "模型已复制到 Docker volume"

    # 验证
    print_info "验证 Docker volume 中的模型..."
    docker run --rm -v "$DOCKER_VOLUME_NAME:/models" alpine ls -lh "/models/$SAM2_MODEL_NAME"
}

step5_restart_sam2_service() {
    print_header "步骤 5: 重启 SAM2 服务"

    if [ "$PRODUCTION" = true ]; then
        # 检查容器是否存在
        if docker ps -a --format '{{.Names}}' | grep -q "idoctor_sam2_service\|sam2_service"; then
            print_info "生产环境：重启 SAM2 Docker 服务..."

            cd "$DOCKER_COMPOSE_DIR"
            docker-compose restart sam2_service

            print_info "等待服务启动..."
            sleep 5

            print_success "SAM2 服务已重启"
        else
            print_warning "SAM2 容器尚未创建，跳过重启步骤"
            print_info "容器将在后续的 docker-compose up 步骤中自动加载模型"
        fi
    else
        print_warning "本地环境：请手动重启 SAM2 服务"
        echo -e "${BLUE}方法 1 - 使用 docker-compose:${NC}"
        echo "  cd $DOCKER_COMPOSE_DIR"
        echo "  docker-compose restart sam2_service"
        echo ""
        echo -e "${BLUE}方法 2 - 使用 docker:${NC}"
        echo "  docker restart idoctor_sam2_service"
    fi
}

step6_verify_model_loaded() {
    print_header "步骤 6: 验证模型加载"

    # 检查容器是否正在运行
    if ! docker ps --format '{{.Names}}' | grep -q "idoctor_sam2_service\|sam2_service"; then
        print_warning "SAM2 容器尚未运行，跳过验证步骤"
        print_info "容器启动后，可运行以下命令验证:"
        echo "  curl http://localhost:8000/health"
        return 0
    fi

    print_info "等待 SAM2 服务完全启动..."
    sleep 10

    print_info "检查 SAM2 服务健康状态..."
    local health_check=$(curl -s http://localhost:8000/health || echo "{}")

    echo "$health_check" | python3 -m json.tool 2>/dev/null || echo "$health_check"

    local model_loaded=$(echo "$health_check" | grep -o '"model_loaded":\s*true' || echo "")

    if [ -n "$model_loaded" ]; then
        print_success "SAM2 模型加载成功!"
        print_success "服务已准备好进行推理"
    else
        print_warning "模型可能未加载成功，请检查日志"
        echo -e "${BLUE}查看日志命令:${NC}"
        echo "  docker logs --tail 50 idoctor_sam2_service"
    fi
}

step7_cleanup() {
    print_header "步骤 7: 清理（可选）"

    if [ "$PRODUCTION" = true ]; then
        # 生产环境自动保留本地模型文件以便后续使用
        print_info "生产环境：保留本地模型文件"
        print_info "如需删除，请手动运行: rm -rf $LOCAL_MODEL_DIR"
    else
        read -p "是否删除本地模型文件以节省空间? (y/N): " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$LOCAL_MODEL_DIR"
            print_success "已删除本地模型目录: $LOCAL_MODEL_DIR"
            print_info "模型仍保留在 Docker volume 中"
        else
            print_info "保留本地模型文件"
        fi
    fi
}

################################################################################
# 主流程
################################################################################

main() {
    print_header "SAM2 模型部署脚本"

    if [ "$PRODUCTION" = true ]; then
        print_info "运行模式: 生产环境"
    else
        print_info "运行模式: 本地开发"
    fi

    echo ""

    step1_check_prerequisites
    echo ""

    step2_create_model_directory
    echo ""

    step3_download_model
    echo ""

    step4_copy_to_docker_volume
    echo ""

    step5_restart_sam2_service
    echo ""

    step6_verify_model_loaded
    echo ""

    step7_cleanup
    echo ""

    print_header "部署完成!"

    print_success "SAM2 模型已成功部署"
    print_info "现在可以使用 AI一键分割 功能了"

    echo ""
    echo -e "${BLUE}后续操作:${NC}"
    echo "1. 测试分割功能: 在前端点击 'AI一键分割' 按钮"
    echo "2. 查看服务日志: docker logs -f idoctor_sam2_service"
    echo "3. 检查健康状态: curl http://localhost:8000/health"
}

# 执行主流程
main
