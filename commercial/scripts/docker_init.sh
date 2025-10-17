#!/bin/bash
set -e

echo "🚀 开始数据库初始化..."

# 设置 Python 路径
export PYTHONPATH=/app:$PYTHONPATH

# 等待数据库完全就绪
echo "⏳ 等待 PostgreSQL 就绪..."
sleep 5

# 检查数据库连接
until pg_isready -h postgres -p 5432 -U postgres; do
  echo "⏳ 数据库未就绪，等待中..."
  sleep 2
done

echo "✅ 数据库已就绪！"

# 初始化订阅计划
echo "💳 初始化订阅计划..."
cd /app
python scripts/seed_plans.py || echo "订阅计划初始化跳过"

# 初始化配额系统
echo "📊 初始化配额系统..."
python scripts/init_database.py

echo "✅ 数据库初始化完成！"
echo "🎉 商业化系统已准备就绪！"
echo ""
echo "📝 访问以下地址查看 API 文档："
echo "   - 认证服务: http://localhost:9001/docs"
echo "   - 支付服务: http://localhost:9002/docs"
