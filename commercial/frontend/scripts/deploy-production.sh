#!/bin/bash

# 生产环境部署脚本
set -e

echo "🚀 开始生产环境部署..."

# 1. 清理之前的构建
echo "📦 清理构建目录..."
rm -rf dist/

# 2. 安装依赖
echo "📚 安装依赖..."
npm ci --only=production

# 3. 使用生产环境配置构建
echo "🔨 构建生产版本..."
export NODE_ENV=production
npm run build

# 4. 检查构建结果
if [ ! -d "dist" ]; then
    echo "❌ 构建失败：dist目录不存在"
    exit 1
fi

echo "✅ 构建完成！文件位于 dist/ 目录"

# 5. 显示构建统计
echo "📊 构建统计："
du -sh dist/
ls -la dist/

# 6. 验证环境变量替换
echo "🔍 验证配置..."
if grep -r "ai.bygpu.com:55304" dist/ > /dev/null; then
    echo "✅ 生产环境URL配置正确"
else
    echo "⚠️  警告：未找到生产环境URL配置"
fi

echo "🎉 部署准备完成！"
echo "📋 下一步："
echo "   1. 将 dist/ 目录上传到服务器"
echo "   2. 配置 Nginx 或 Apache"
echo "   3. 确保端口 55303 可访问"