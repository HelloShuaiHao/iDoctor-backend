#!/bin/bash

echo "🚀 启动 iDoctor 商业化系统..."
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未安装 Docker"
    echo "请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# 检查 Docker Compose 是否可用
if ! docker compose version &> /dev/null; then
    echo "❌ 错误: Docker Compose 不可用"
    echo "请确保 Docker Desktop 正在运行"
    exit 1
fi

echo "✅ Docker 环境检查通过"
echo ""

# 进入 docker 目录
cd "$(dirname "$0")"

# 启动服务
echo "📦 启动所有服务..."
docker compose up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 10

echo ""
echo "✅ 服务启动成功！"
echo ""
echo "📝 访问以下地址："
echo "   - 认证服务 API 文档: http://localhost:9001/docs"
echo "   - 支付服务 API 文档: http://localhost:9002/docs"
echo ""
echo "📊 查看服务状态:"
echo "   docker compose ps"
echo ""
echo "📋 查看服务日志:"
echo "   docker compose logs -f"
echo ""
echo "🛑 停止服务:"
echo "   docker compose down"
echo ""
