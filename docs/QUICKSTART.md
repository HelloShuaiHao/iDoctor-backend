# iDoctor 快速开始指南

本指南将帮助您快速启动 iDoctor 系统的开发环境。

## 📋 目录

- [系统要求](#系统要求)
- [快速启动（开发环境）](#快速启动开发环境)
- [快速启动（生产环境）](#快速启动生产环境)
- [常用命令](#常用命令)
- [故障排查](#故障排查)

---

## 系统要求

### 软件依赖

- **Docker** & **Docker Compose** (推荐最新版本)
- **Python 3.10+**
- **Node.js 16+** & **npm**
- **PostgreSQL 15** (Docker 提供)

### 端口要求

确保以下端口未被占用：

| 端口 | 用途 |
|------|------|
| 3000 | Nginx (开发) |
| 4200 | CTAI Backend |
| 5432 | PostgreSQL |
| 7500 | CTAI Frontend (开发服务器) |
| 8000 | SAM2 Service |
| 9001 | Auth Service |
| 9002 | Payment Service |

---

## 快速启动（开发环境）

### 步骤 1: 克隆项目

```bash
cd /path/to/your/workspace
git clone <repository-url>
cd iDoctor-backend
```

### 步骤 2: 配置环境变量

#### 2.1 配置 CTAI 主应用

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
vim .env
```

**关键配置项**:

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5432/idoctor_commercial

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256

# 商业化功能
ENABLE_AUTH=true
ENABLE_QUOTA=true

# SAM2
SAM2_SERVICE_URL=http://localhost:8000
SAM2_ENABLED=true
SAM2_REQUEST_TIMEOUT=120

# SMTP (可选，用于邮箱验证)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

#### 2.2 配置 Commercial 模块

```bash
cd commercial

# 复制示例配置
cp .env.example .env

# 编辑配置（确保与主应用的 .env 一致）
vim .env
```

#### 2.3 配置 CTAI 前端

```bash
cd CTAI_web

# 开发环境配置
cat > .env.development <<EOF
VUE_APP_BASE_URL=http://localhost:3000/api/ctai
VUE_APP_AUTH_BASE_URL=http://localhost:3000/api/auth
VUE_APP_COMMERCIAL_URL=http://localhost:3000
EOF

# 本地开发配置（如果需要直连后端）
cat > .env.local <<EOF
VUE_APP_BASE_URL=http://localhost:4200
VUE_APP_AUTH_BASE_URL=http://localhost:3000/api/auth
VUE_APP_COMMERCIAL_URL=http://localhost:3000
EOF
```

### 步骤 3: 一键启动所有服务

```bash
# 回到项目根目录
cd /path/to/iDoctor-backend

# 方法 1: 使用统一部署脚本（推荐）
bash scripts/deploy-ctai.sh dev

# 方法 2: 分步启动
# 先启动 Commercial 模块
cd commercial
bash scripts/deploy-all.sh dev

# 再启动 CTAI 后端
cd ..
bash scripts/start-ctai-backend.sh dev

# （可选）启动 CTAI 前端开发服务器
bash scripts/start-ctai-frontend.sh dev
```

### 步骤 4: 验证部署

```bash
# 检查所有服务状态
bash scripts/check-services.sh
```

**预期输出**:

```
✅ All services are running!

Docker Containers:
  ✅ idoctor_commercial_nginx
  ✅ idoctor_auth_service
  ✅ idoctor_payment_service
  ✅ idoctor_commercial_db
  ✅ idoctor_sam2_service

CTAI Backend:
  ✅ Running (PID: xxxxx)
  ✅ Health check passed
```

### 步骤 5: 访问应用

打开浏览器访问：

- **Commercial 登录页**: http://localhost:3000
- **CTAI 主应用**: http://localhost:3000/ctai
- **CTAI Backend API**: http://localhost:3000/api/ctai
- **API 文档**: http://localhost:4200/docs

---

## 快速启动（生产环境）

### 步骤 1: 准备生产配置

```bash
cd commercial/docker

# 复制生产配置模板
cp .env.prod.example .env.prod

# 编辑生产配置
vim .env.prod
```

**关键配置**:

```bash
# Nginx
NGINX_SERVER_NAME=ai.bygpu.com
NGINX_EXTERNAL_PORT=55305

# 数据库
DATABASE_PASSWORD=your-strong-password

# JWT
JWT_SECRET_KEY=your-production-secret-key

# SMTP
SMTP_USER=your-production-email@example.com
SMTP_PASSWORD=your-production-password
```

### 步骤 2: 配置主应用 .env

```bash
cd /path/to/iDoctor-backend

# 编辑主配置
vim .env
```

确保以下配置适合生产环境：

```bash
ENABLE_AUTH=true
ENABLE_QUOTA=true
SAM2_ENABLED=true
```

### 步骤 3: 部署生产环境

```bash
# 一键部署（推荐）
bash scripts/deploy-ctai.sh prod

# 或分步部署
cd commercial
bash scripts/deploy-all.sh prod

cd ..
bash scripts/start-ctai-backend.sh prod
bash scripts/start-ctai-frontend.sh prod
```

### 步骤 4: 验证部署

```bash
bash scripts/check-services.sh

# 检查外部访问
curl http://ai.bygpu.com:55305/health
```

---

## 常用命令

### 服务管理

```bash
# 检查所有服务状态
bash scripts/check-services.sh

# 查看日志
bash scripts/view-logs.sh

# 重启 CTAI Backend
bash scripts/start-ctai-backend.sh dev

# 重启所有服务
bash scripts/deploy-ctai.sh dev

# 停止所有 Docker 服务
cd commercial/docker
docker-compose stop

# 启动所有 Docker 服务
docker-compose start
```

### Docker 操作

```bash
# 查看运行的容器
docker ps

# 查看特定容器日志
docker logs -f idoctor_sam2_service
docker logs -f idoctor_auth_service
docker logs -f idoctor_commercial_nginx

# 进入容器 shell
docker exec -it idoctor_commercial_db psql -U postgres

# 重启容器
docker restart idoctor_sam2_service
```

### 数据库操作

```bash
# 连接数据库
docker exec -it idoctor_commercial_db psql -U postgres -d idoctor_commercial

# 查看数据库列表
docker exec -it idoctor_commercial_db psql -U postgres -c "\l"

# 备份数据库
docker exec idoctor_commercial_db pg_dump -U postgres idoctor_commercial > backup.sql

# 恢复数据库
cat backup.sql | docker exec -i idoctor_commercial_db psql -U postgres idoctor_commercial
```

### CTAI Backend 操作

```bash
# 查看后端日志
tail -f app.log

# 实时过滤错误日志
tail -f app.log | grep ERROR

# 查看 SAM2 相关日志
tail -f app.log | grep SAM2

# 停止后端
pkill -f "uvicorn app:app"

# 查看后端进程
ps aux | grep uvicorn
```

### 前端操作

```bash
cd CTAI_web

# 开发模式（热重载）
npm run serve

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

---

## 故障排查

### 问题 1: 端口已被占用

**错误信息**:
```
Port 4200 is already in use!
```

**解决方案**:

```bash
# 查看占用端口的进程
lsof -i:4200

# 杀死进程
lsof -ti:4200 | xargs kill -9

# 或使用脚本自动处理
bash scripts/start-ctai-backend.sh dev
```

### 问题 2: SAM2 服务不可用

**错误信息**:
```
SAM2 service is unavailable
```

**解决方案**:

```bash
# 检查 SAM2 容器状态
docker ps | grep sam2

# 查看 SAM2 日志
docker logs idoctor_sam2_service

# 重启 SAM2 服务
docker restart idoctor_sam2_service

# 如果容器未运行，启动它
cd commercial/docker
docker-compose up -d sam2_service
```

### 问题 3: 数据库连接失败

**错误信息**:
```
Connection to PostgreSQL failed
```

**解决方案**:

```bash
# 检查数据库容器
docker ps | grep commercial_db

# 查看数据库日志
docker logs idoctor_commercial_db

# 测试数据库连接
docker exec idoctor_commercial_db pg_isready -U postgres

# 重启数据库
docker restart idoctor_commercial_db
```

### 问题 4: 前端显示 404

**可能原因**:
- Nginx 未正确配置
- 前端未构建
- Nginx 未重启

**解决方案**:

```bash
# 检查前端构建文件
ls -la commercial/docker/nginx/html/ctai

# 重新构建前端
cd CTAI_web
npm run build

# 复制到 Nginx
cp -r dist/* ../commercial/docker/nginx/html/ctai/

# 重启 Nginx
docker restart idoctor_commercial_nginx

# 查看 Nginx 配置
docker exec idoctor_commercial_nginx cat /etc/nginx/conf.d/default.conf

# 测试 Nginx 配置
docker exec idoctor_commercial_nginx nginx -t
```

### 问题 5: 认证失败 401

**错误信息**:
```
Unauthorized
```

**解决方案**:

```bash
# 检查 .env 配置
cat .env | grep ENABLE_AUTH
cat .env | grep JWT_SECRET_KEY

# 确保 ENABLE_AUTH=true
# 确保 JWT_SECRET_KEY 与 commercial/.env 一致

# 清除浏览器缓存和 localStorage
# 重新登录
```

### 问题 6: 配额耗尽 402

**错误信息**:
```
Payment Required
```

**解决方案**:

```bash
# 连接数据库
docker exec -it idoctor_commercial_db psql -U postgres -d idoctor_commercial

# 查看用户配额
SELECT * FROM user_quotas WHERE user_id = 'your-user-id';

# 重置配额（开发环境）
UPDATE user_quotas SET remaining_quota = 100 WHERE user_id = 'your-user-id';
```

### 问题 7: CTAI 后端自动重载失败

**原因**: uvicorn --reload 模式监听文件变化

**解决方案**:

```bash
# 手动重启后端
bash scripts/start-ctai-backend.sh dev

# 或使用生产模式（不自动重载）
bash scripts/start-ctai-backend.sh prod
```

---

## 开发工作流

### 1. 修改后端代码

```bash
# 编辑 app.py 或其他 Python 文件
vim app.py

# 自动重载会在几秒内生效（开发模式）
# 查看日志确认
tail -f app.log
```

### 2. 修改前端代码

```bash
# 如果运行了 Vue 开发服务器（端口 7500）
cd CTAI_web
npm run serve
# 修改文件会自动热重载

# 如果通过 Nginx 访问（端口 3000/ctai）
# 需要重新构建并部署
npm run build
cp -r dist/* ../commercial/docker/nginx/html/ctai/
docker restart idoctor_commercial_nginx
```

### 3. 修改 Commercial 前端

```bash
cd commercial/frontend

# 修改代码
vim src/App.jsx

# 重新构建和部署
npm run build:dev
cp -r dist/* ../docker/nginx/html/
docker restart idoctor_commercial_nginx
```

### 4. 数据库迁移

```bash
# 查看当前迁移
cd commercial/auth_service
alembic current

# 创建新迁移
alembic revision --autogenerate -m "Add new table"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

---

## 常见任务

### 添加新用户

```bash
# 方法 1: 使用 API
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "full_name": "Test User"
  }'

# 方法 2: 直接操作数据库
docker exec -it idoctor_commercial_db psql -U postgres -d idoctor_commercial

INSERT INTO users (id, email, hashed_password, full_name, is_verified)
VALUES (gen_random_uuid(), 'user@example.com', 'hash', 'Test User', true);
```

### 重置数据库

```bash
# ⚠️ 警告: 会删除所有数据！

cd commercial/docker
docker-compose down -v  # 删除所有卷（包括数据库数据）
docker-compose up -d    # 重新创建
```

### 清理 Docker

```bash
# 停止所有容器
docker stop $(docker ps -q)

# 删除所有 iDoctor 容器
docker rm $(docker ps -a | grep idoctor | awk '{print $1}')

# 清理未使用的镜像
docker image prune -a

# 清理所有未使用资源
docker system prune -a --volumes
```

---

## 下一步

- 阅读 [架构文档](./ARCHITECTURE.md) 了解系统设计
- 查看 [API 文档](http://localhost:4200/docs) 了解接口
- 阅读 Commercial 模块文档 (`commercial/README.md`)
- 阅读 SAM2 集成文档 (待补充)

---

## 获取帮助

- **文档**: `/docs` 目录
- **脚本**: `/scripts` 目录
- **日志**: `bash scripts/view-logs.sh`
- **健康检查**: `bash scripts/check-services.sh`
