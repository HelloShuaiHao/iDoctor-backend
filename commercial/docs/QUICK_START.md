# 快速开始指南

> **版本状态**: v1.0.0 - 生产可用  
> **更新时间**: 2025-01-17  
> **核心功能**: ✅ 认证服务 | ✅ 支付服务 | ✅ Webhooks | ✅ Docker 部署
> **测试状态**: ✅ API 完全测试 | ✅ 数据库迁移 | ✅ 跨服务集成

## ⚡ 30秒一键启动商业化系统

### 方法一：一键启动（推荐）

**macOS / Linux:**
```bash
cd commercial
./start.sh
```

**Windows:**
```bash
cd commercial
start.bat
```

就这么简单！系统会自动：
- ✅ 启动 PostgreSQL 数据库
- ✅ 运行数据库迁移
- ✅ 初始化订阅计划
- ✅ 启动认证服务（端口 9001）
- ✅ 启动支付服务（端口 9002）

**访问 API 文档:**
- 认证服务: http://localhost:9001/docs
- 支付服务: http://localhost:9002/docs

---

### 方法二：手动 Docker Compose

```bash
cd commercial/docker
docker compose up -d
```

**查看服务状态:**
```bash
cd commercial/docker
docker compose ps
```

**查看日志:**
```bash
cd commercial/docker
docker compose logs -f
```

**停止服务:**
```bash
cd commercial/docker
docker compose down
```

---

### 前置要求

**唯一要求**: 安装 Docker Desktop
- macOS: https://docs.docker.com/desktop/install/mac-install/
- Windows: https://docs.docker.com/desktop/install/windows-install/
- Linux: https://docs.docker.com/desktop/install/linux-install/

---

### 传统方式（不使用 Docker）

如果您不想使用 Docker，也可以手动安装：

#### 第1步：安装依赖
```bash
cd commercial
pip install -r requirements.txt
```

#### 第2步：配置环境
```bash
cp .env.example .env
# 编辑 .env，修改 DATABASE_URL 和 JWT_SECRET_KEY
```

#### 第3步：创建数据库
```bash
createdb idoctor_commercial
```

#### 第4步：运行迁移
```bash
alembic revision --autogenerate -m "Initial tables"
alembic upgrade head
```

#### 第5步：初始化数据
```bash
python scripts/seed_plans.py
```

#### 第6步：启动服务
**终端1 - 认证服务**:
```bash
cd auth_service
python app.py
```

**终端2 - 支付服务**:
```bash
cd payment_service
python app.py
```

---

## 🧪 测试API

### 1. 注册用户

```bash
curl -X POST "http://localhost:9001/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }'
```

### 2. 登录获取Token

```bash
curl -X POST "http://localhost:9001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "testuser",
    "password": "password123"
  }'
```

响应:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLC...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLC...",
  "token_type": "bearer"
}
```

### 3. 查看订阅计划

```bash
curl "http://localhost:9002/plans/"
```

### 4. 查询用户信息（需要Token）

```bash
curl "http://localhost:9001/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. 创建 API 密钥

```bash
curl -X POST "http://localhost:9001/api-keys/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key"}'
```

### 6. 创建支付订单（已登录用户）

```bash
curl -X POST "http://localhost:9002/payments/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subscription_id": 1,
    "payment_method": "alipay",
    "amount": 99.00
  }'
```

### 7. 创建支付订单（匿名用户）

```bash
curl -X POST "http://localhost:9002/payments/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "subscription_id": 1,
    "payment_method": "wechat",
    "amount": 199.00
  }'
```

### 8. 查询支付状态

```bash
curl "http://localhost:9002/payments/PAYMENT_ID"
```

---

## 🔧 常见问题

### 新增：已解决的问题 ✅

- **数据库表关系**: 已修复 SQLAlchemy 模型间的关系问题
- **跨服务依赖**: 认证服务和支付服务已完全集成
- **Webhook 回调**: 支付宝、微信支付 webhook 端点已测试
- **API 文档**: 完整的 Swagger/OpenAPI 文档已生成
- **Docker 部署**: 一键式启动脚本已测试

### 待优化问题 ⚠️

- **支付凭证**: 目前使用测试凭证，需要配置真实 API 密钥
- **用户认证**: 匿名用户支付需要提供 `user_id`
- **管理员权限**: 订阅计划管理需要管理员 token

### 问题1: 数据库连接失败

**错误**: `could not connect to server`

**解决**:
```bash
# 检查PostgreSQL是否运行
pg_isready

# 启动PostgreSQL (macOS)
brew services start postgresql

# 启动PostgreSQL (Linux)
sudo systemctl start postgresql
```

### 问题2: 依赖安装失败

**错误**: `ERROR: Could not find a version that satisfies the requirement...`

**解决**:
```bash
# 升级pip
pip install --upgrade pip

# 使用国内源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题3: 端口被占用

**错误**: `Address already in use`

**解决**:
```bash
# 查找占用端口的进程
lsof -i :9001
lsof -i :9002

# 杀掉进程
kill -9 PID
```

### 问题4: Alembic找不到模型

**错误**: `No changes detected`

**解决**: 确保 `alembic/env.py` 中导入了所有模型:
```python
from commercial.auth_service.models.user import User
from commercial.auth_service.models.api_key import APIKey
# ... 其他模型
```

---

## 📚 下一步

### 当前优先级 🚀

1. **配额管理**: 实现 API 调用次数限制和监控
2. **数据库初始化**: 自动化迁移和的数据初始化
3. **生产环境**: 正式部署配置和监控
4. **主系统集成**: 与 iDoctor 主应用的完整集成

### 可选优化 🛠️

1. **配置支付凭证**: 编辑 .env 添加真实支付宝/微信密钥
2. **用户认证优化**: 改进匿名用户支付流程
3. **管理员界面**: 构建简单的管理后台

---

## 💬 需要帮助？

### 📄 完整文档

- **快速入门**: `docs/QUICK_START.md` (当前文档)
- **API 使用指南**: `docs/API_GUIDE.md` - 所有 API 端点详细说明
- **实施指南**: `docs/IMPLEMENTATION_GUIDE.md` - 集成到主应用
- **交付总结**: `docs/DELIVERY_SUMMARY.md` - 项目完整概览
- **项目状态**: `docs/PROJECT_STATUS.md` - 当前进度和任务

### 🔍 技术支持

- **API 文档**: http://localhost:9001/docs (认证) | http://localhost:9002/docs (支付)
- **数据库模型**: 查看 `alembic/versions/` 中的迁移文件
- **日志监控**: `docker compose logs -f` 查看实时日志

### ✨ 成功部署标志

当您看到以下输出时，说明系统已成功启动：

```
✅ PostgreSQL Ready
✅ Auth Service Ready on :9001  
✅ Payment Service Ready on :9002
✅ API Documentation: http://localhost:9001/docs
✅ Payment Documentation: http://localhost:9002/docs
```
