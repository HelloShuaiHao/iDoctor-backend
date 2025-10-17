# Docker 部署指南

## 快速启动

### macOS / Linux
```bash
cd commercial
./start.sh
```

### Windows
```bash
cd commercial
start.bat
```

---

## 详细说明

### 系统架构

Docker Compose 会启动以下服务：

```
┌─────────────────┐
│   PostgreSQL    │  数据库
│   (端口 5432)    │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
┌────────▼────────┐ ┌─────▼──────────┐
│  认证服务        │ │  支付服务       │
│  (端口 9001)     │ │  (端口 9002)    │
└─────────────────┘ └────────────────┘
```

### 服务说明

1. **postgres** - PostgreSQL 15 数据库
   - 端口: 5432
   - 用户名: postgres
   - 密码: postgres123
   - 数据库: idoctor_commercial
   - 数据持久化: `postgres_data` 卷

2. **db_init** - 数据库初始化服务
   - 运行 Alembic 迁移
   - 创建默认订阅计划
   - 一次性任务（运行后自动退出）

3. **auth_service** - 认证服务
   - 端口: 9001
   - API 文档: http://localhost:9001/docs
   - 功能: 用户注册、登录、JWT Token、API Key

4. **payment_service** - 支付服务
   - 端口: 9002
   - API 文档: http://localhost:9002/docs
   - 功能: 订阅管理、支付处理、配额管理

---

## 常用命令

### 启动服务
```bash
docker compose up -d
```

### 查看服务状态
```bash
docker compose ps
```

### 查看所有日志
```bash
docker compose logs -f
```

### 查看特定服务日志
```bash
docker compose logs -f auth_service
docker compose logs -f payment_service
docker compose logs -f postgres
```

### 停止服务
```bash
docker compose down
```

### 停止并删除数据（包括数据库）
```bash
docker compose down -v
```

### 重启服务
```bash
docker compose restart
```

### 重启特定服务
```bash
docker compose restart auth_service
docker compose restart payment_service
```

### 重新构建并启动
```bash
docker compose up -d --build
```

---

## 故障排查

### 问题1: Docker Desktop 未启动

**错误信息:**
```
Cannot connect to the Docker daemon
```

**解决方案:**
1. 打开 Docker Desktop
2. 等待 Docker 引擎启动（状态栏显示绿色）
3. 重新运行启动命令

---

### 问题2: 端口被占用

**错误信息:**
```
Bind for 0.0.0.0:9001 failed: port is already allocated
```

**解决方案:**

**方法1 - 找到并停止占用端口的进程:**
```bash
# macOS/Linux
lsof -i :9001
kill -9 <PID>

# Windows
netstat -ano | findstr :9001
taskkill /PID <PID> /F
```

**方法2 - 修改 docker-compose.yml 中的端口映射:**
```yaml
ports:
  - "19001:9001"  # 使用 19001 代替 9001
```

---

### 问题3: 数据库连接失败

**错误信息:**
```
could not connect to server: Connection refused
```

**解决方案:**
```bash
# 1. 检查 PostgreSQL 容器是否健康
docker compose ps

# 2. 查看 PostgreSQL 日志
docker compose logs postgres

# 3. 重启数据库
docker compose restart postgres

# 4. 如果还是失败，清除数据重新启动
docker compose down -v
docker compose up -d
```

---

### 问题4: 迁移失败

**错误信息:**
```
Target database is not up to date
```

**解决方案:**
```bash
# 进入任意容器手动运行迁移
docker compose exec auth_service bash
alembic upgrade head
exit
```

---

### 问题5: 服务启动后立即退出

**查看详细错误:**
```bash
docker compose logs auth_service
docker compose logs payment_service
```

**常见原因:**
- 环境变量配置错误
- 数据库未就绪
- 代码语法错误

**解决方案:**
```bash
# 重新构建镜像
docker compose down
docker compose up -d --build
```

---

## 数据管理

### 备份数据库

```bash
# 导出所有数据
docker compose exec postgres pg_dump -U postgres idoctor_commercial > backup.sql

# 导出特定表
docker compose exec postgres pg_dump -U postgres -t users idoctor_commercial > users_backup.sql
```

### 恢复数据库

```bash
# 从备份恢复
docker compose exec -T postgres psql -U postgres idoctor_commercial < backup.sql
```

### 清空数据重新开始

```bash
# 停止并删除所有容器和数据卷
docker compose down -v

# 重新启动
docker compose up -d
```

---

## 配置自定义

### 修改数据库密码

编辑 `docker-compose.yml`:

```yaml
postgres:
  environment:
    POSTGRES_PASSWORD: your_new_password

auth_service:
  environment:
    DATABASE_URL: postgresql+asyncpg://postgres:your_new_password@postgres:5432/idoctor_commercial

payment_service:
  environment:
    DATABASE_URL: postgresql+asyncpg://postgres:your_new_password@postgres:5432/idoctor_commercial
```

### 修改 JWT 密钥

编辑 `docker-compose.yml`:

```yaml
auth_service:
  environment:
    JWT_SECRET_KEY: your-super-secret-jwt-key
    JWT_REFRESH_SECRET_KEY: your-super-secret-refresh-key

payment_service:
  environment:
    JWT_SECRET_KEY: your-super-secret-jwt-key
```

### 配置支付密钥

编辑 `docker-compose.yml`:

```yaml
payment_service:
  environment:
    # 支付宝
    ALIPAY_APP_ID: your_alipay_app_id
    ALIPAY_PRIVATE_KEY: your_alipay_private_key
    ALIPAY_PUBLIC_KEY: your_alipay_public_key

    # 微信支付
    WECHAT_APP_ID: your_wechat_app_id
    WECHAT_MCH_ID: your_wechat_mch_id
    WECHAT_API_KEY: your_wechat_api_key
```

---

## 生产环境部署

### 1. 使用环境变量文件

创建 `.env.production`:
```bash
POSTGRES_PASSWORD=production_password
JWT_SECRET_KEY=production_jwt_key
ALIPAY_APP_ID=production_alipay_id
# ... 其他配置
```

使用:
```bash
docker compose --env-file .env.production up -d
```

### 2. 使用外部数据库

修改 `docker-compose.yml`，移除 postgres 服务，修改 DATABASE_URL 指向外部数据库。

### 3. 启用 HTTPS

使用 Nginx 反向代理或 Traefik 添加 SSL 证书。

### 4. 资源限制

```yaml
auth_service:
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 512M
      reservations:
        cpus: '0.25'
        memory: 256M
```

---

## 性能优化

### 数据库连接池

已在代码中配置:
- pool_size: 10
- max_overflow: 20

### 日志级别

生产环境设置:
```yaml
auth_service:
  environment:
    ENVIRONMENT: production  # 关闭 SQL echo
```

---

## 监控和维护

### 查看资源使用

```bash
docker stats
```

### 定期清理

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷
docker volume prune
```

---

## 更多帮助

- Docker 官方文档: https://docs.docker.com/
- Docker Compose 文档: https://docs.docker.com/compose/
- PostgreSQL 文档: https://www.postgresql.org/docs/
