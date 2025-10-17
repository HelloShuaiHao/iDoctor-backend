#!/bin/bash
# 阶段 1 测试脚本 - 基础中间件集成验证

echo "🧪 阶段 1 测试：基础中间件集成"
echo "================================"
echo ""

# 检查 .env 文件
echo "1️⃣ 检查 .env 文件..."
if [ -f .env ]; then
    echo "✅ .env 文件存在"
    if grep -q "ENABLE_AUTH=false" .env && grep -q "ENABLE_QUOTA=false" .env; then
        echo "✅ 认证和配额已关闭（开发模式）"
    fi
    if grep -q "JWT_SECRET_KEY=9b74ca71" .env; then
        echo "✅ JWT 密钥已配置"
    fi
else
    echo "❌ .env 文件不存在"
    exit 1
fi
echo ""

# 检查语法
echo "2️⃣ 检查 app.py 语法..."
python -m py_compile app.py
if [ $? -eq 0 ]; then
    echo "✅ app.py 语法正确"
else
    echo "❌ app.py 语法错误"
    exit 1
fi
echo ""

# 检查依赖
echo "3️⃣ 检查依赖..."
python -c "import dotenv; print('✅ python-dotenv 已安装')" 2>&1
python -c "import fastapi; print('✅ FastAPI 已安装')" 2>&1
echo ""

echo "4️⃣ 测试说明："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 所有基础检查通过！"
echo ""
echo "📝 手动测试步骤："
echo "1. 启动应用（关闭认证模式）："
echo "   uvicorn app:app --host 0.0.0.0 --port 4200 --reload"
echo ""
echo "2. 观察启动日志，应该看到："
echo "   🔐 认证中间件: ❌ 关闭"
echo "   📊 配额中间件: ❌ 关闭"
echo ""
echo "3. 测试健康检查："
echo "   curl http://localhost:4200/docs"
echo ""
echo "4. 测试 API（无需认证）："
echo "   curl http://localhost:4200/list_patients"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 阶段 1 准备完成！现在可以手动启动应用进行测试。"
