# 快速开始指南

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

### 5. 创建API密钥

```bash
curl -X POST "http://localhost:9001/api-keys/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key"}'
```

---

## 🔧 常见问题

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

## 📖 下一步

1. **配置支付**：编辑.env添加支付宝/微信密钥
2. **集成到主应用**：参考 IMPLEMENTATION_GUIDE.md
3. **部署到生产**：参考 DELIVERY_SUMMARY.md

---

## 💬 需要帮助？

- 查看完整文档: `DELIVERY_SUMMARY.md`
- 实施指南: `IMPLEMENTATION_GUIDE.md`
- 项目状态: `PROJECT_STATUS.md`
