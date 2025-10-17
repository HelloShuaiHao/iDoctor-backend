# 生产环境部署指南

本文档提供从开发到生产的完整部署流程。

## 📋 前置准备

### 1. 服务器要求

**最低配置**：
- CPU: 2核
- 内存: 4GB
- 硬盘: 20GB SSD
- 系统: Ubuntu 20.04 LTS / CentOS 7+

**推荐配置**：
- CPU: 4核
- 内存: 8GB
- 硬盘: 50GB SSD
- 系统: Ubuntu 22.04 LTS

### 2. 域名与 SSL

- 注册域名（例如：`api.yourdomain.com`）
- 配置 DNS 解析指向服务器 IP
- 准备 SSL 证书（推荐使用 Let's Encrypt 免费证书）

### 3. 支付平台账号

**支付宝**：
- 企业支付宝账号
- 完成实名认证
- 签约「电脑网站支付」或「手机网站支付」

**微信支付**：
- 微信商户平台账号
- 完成企业认证
- 开通「Native 支付」

---

## 🚀 快速部署（Docker 方式）

### Step 1: 安装 Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo apt-get install docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### Step 2: 克隆项目

```bash
git clone https://github.com/yourusername/idoctor-commercial.git
cd idoctor-commercial/commercial
```

### Step 3: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

**关键配置项**：

```bash
# ==================== 环境 ====================
ENVIRONMENT=production  # 必须设置为 production

# ==================== 数据库 ====================
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_STRONG_PASSWORD@db:5432/idoctor_commercial

# ==================== JWT ====================
# 生成强随机密钥：openssl rand -hex 32
JWT_SECRET_KEY=your-production-secret-key-min-32-chars

# ==================== 支付宝（正式环境）====================
ALIPAY_APP_ID=2021001199600000  # 你的正式 AppID
ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do  # 正式网关
ALIPAY_RETURN_URL=https://yourdomain.com/payment/return
ALIPAY_NOTIFY_URL=https://api.yourdomain.com:9002/webhooks/alipay

# ==================== 微信支付 ====================
WECHAT_APP_ID=wxYOUR_APPID
WECHAT_MCH_ID=1234567890
WECHAT_API_KEY=your32charlongapikeyhere1234567
WECHAT_NOTIFY_URL=https://api.yourdomain.com:9002/webhooks/wechat

# ==================== CORS ====================
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Step 4: 配置支付密钥

```bash
# 创建密钥目录
mkdir -p keys

# 上传密钥文件（使用 scp 或 SFTP）
# 支付宝密钥
scp alipay_private_key.pem user@server:/path/to/commercial/keys/
scp alipay_public_key.pem user@server:/path/to/commercial/keys/

# 微信证书
scp apiclient_cert.pem user@server:/path/to/commercial/keys/
scp apiclient_key.pem user@server:/path/to/commercial/keys/

# 设置权限
chmod 600 keys/*.pem
```

### Step 5: 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 检查服务状态
docker-compose ps
```

### Step 6: 初始化数据库

```bash
# 进入认证服务容器
docker-compose exec auth-service bash

# 运行数据库迁移（如果有 Alembic）
alembic upgrade head

# 或手动创建超级用户（可选）
python scripts/create_superuser.py
```

### Step 7: 配置 Nginx 反向代理

```bash
# 安装 Nginx
sudo apt-get install nginx

# 创建配置文件
sudo nano /etc/nginx/sites-available/idoctor-commercial
```

**Nginx 配置示例**：

```nginx
# 认证服务
server {
    listen 80;
    server_name api.yourdomain.com;

    # 强制 HTTPS（Let's Encrypt 配置后）
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL 证书（Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # 认证服务
    location /auth/ {
        proxy_pass http://localhost:9001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 支付服务
    location /api/payments/ {
        proxy_pass http://localhost:9002/payments/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 支付回调（重要：不能有认证拦截）
    location /webhooks/ {
        proxy_pass http://localhost:9002/webhooks/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/idoctor-commercial /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### Step 8: 配置 SSL（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d api.yourdomain.com

# 自动续期测试
sudo certbot renew --dry-run
```

---

## 🔧 手动部署（非 Docker）

### 1. 安装依赖

```bash
# Python 3.10+
sudo apt-get install python3.10 python3.10-venv python3-pip

# PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Redis
sudo apt-get install redis-server
```

### 2. 创建数据库

```bash
sudo -u postgres psql

CREATE DATABASE idoctor_commercial;
CREATE USER idoctor_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE idoctor_commercial TO idoctor_user;
\q
```

### 3. 配置项目

```bash
# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env
```

### 4. 启动服务（systemd）

创建服务文件：`/etc/systemd/system/idoctor-auth.service`

```ini
[Unit]
Description=iDoctor Auth Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/idoctor-commercial/commercial
Environment="PATH=/opt/idoctor-commercial/commercial/venv/bin"
ExecStart=/opt/idoctor-commercial/commercial/venv/bin/uvicorn auth_service.app:app --host 0.0.0.0 --port 9001 --workers 4

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

创建支付服务：`/etc/systemd/system/idoctor-payment.service`

```ini
[Unit]
Description=iDoctor Payment Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/idoctor-commercial/commercial
Environment="PATH=/opt/idoctor-commercial/commercial/venv/bin"
ExecStart=/opt/idoctor-commercial/commercial/venv/bin/uvicorn payment_service.app:app --host 0.0.0.0 --port 9002 --workers 2

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start idoctor-auth
sudo systemctl start idoctor-payment

# 开机自启
sudo systemctl enable idoctor-auth
sudo systemctl enable idoctor-payment

# 查看状态
sudo systemctl status idoctor-auth
sudo systemctl status idoctor-payment
```

---

## 🔍 验证部署

### 1. 健康检查

```bash
# 认证服务
curl https://api.yourdomain.com/auth/health

# 支付服务
curl https://api.yourdomain.com/api/payments/health

# 应返回：{"status": "ok"}
```

### 2. 测试注册登录

```bash
# 注册用户
curl -X POST "https://api.yourdomain.com/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "SecurePass123"
  }'

# 登录
curl -X POST "https://api.yourdomain.com/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "testuser",
    "password": "SecurePass123"
  }'
```

### 3. 测试支付创建

```bash
# 获取 JWT token（从登录响应）
TOKEN="your_jwt_token_here"

# 创建支付订单
curl -X POST "https://api.yourdomain.com/api/payments/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "amount": 0.01,
    "currency": "CNY",
    "payment_method": "alipay"
  }'
```

---

## 📊 监控与日志

### 1. 查看日志（Docker）

```bash
# 实时日志
docker-compose logs -f auth-service
docker-compose logs -f payment-service

# 最近 100 行
docker-compose logs --tail=100 auth-service
```

### 2. 查看日志（systemd）

```bash
# 实时日志
sudo journalctl -u idoctor-auth -f
sudo journalctl -u idoctor-payment -f

# 查看错误
sudo journalctl -u idoctor-auth -p err
```

### 3. 数据库备份

```bash
# 每日备份脚本
cat > /opt/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker-compose exec -T db pg_dump -U postgres idoctor_commercial | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 保留最近 7 天
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /opt/backup_db.sh

# 添加到 crontab（每天凌晨 2 点）
echo "0 2 * * * /opt/backup_db.sh" | crontab -
```

---

## 🛡️ 安全加固

### 1. 防火墙配置

```bash
# UFW 防火墙
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# 禁止直接访问后端端口
sudo ufw deny 9001/tcp
sudo ufw deny 9002/tcp
```

### 2. 限制数据库访问

编辑 PostgreSQL 配置 `/etc/postgresql/*/main/pg_hba.conf`：

```
# 只允许本地连接
local   all             all                                     peer
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

### 3. 环境变量安全

```bash
# 限制 .env 文件权限
chmod 600 .env

# 定期轮换密钥
# JWT 密钥建议每 6 个月更换一次
```

---

## ❓ 常见问题

### Q1: 支付回调收不到？

**检查项**：
1. 确认回调 URL 是公网可访问的 HTTPS 地址
2. 检查防火墙是否拦截
3. 查看 Nginx 日志：`sudo tail -f /var/log/nginx/error.log`
4. 确认支付平台配置的回调地址正确

### Q2: 数据库连接失败？

```bash
# 检查数据库是否运行
sudo systemctl status postgresql

# 检查连接
psql -h localhost -U idoctor_user -d idoctor_commercial

# 检查 .env 中的 DATABASE_URL
```

### Q3: SSL 证书过期？

```bash
# 手动续期
sudo certbot renew

# 重启 Nginx
sudo systemctl restart nginx
```

### Q4: 服务启动失败？

```bash
# 查看详细错误
sudo journalctl -u idoctor-auth -n 50 --no-pager

# 检查端口占用
sudo lsof -i :9001
sudo lsof -i :9002

# 检查配置文件语法
python -m py_compile auth_service/app.py
```

---

## 📈 性能优化

### 1. 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_transactions_status ON payment_transactions(status);
CREATE INDEX idx_subscriptions_user ON user_subscriptions(user_id);

-- 定期 VACUUM
VACUUM ANALYZE;
```

### 2. Redis 缓存

```python
# 在 shared/config.py 中配置 Redis
REDIS_URL = "redis://localhost:6379/0"

# 缓存 JWT 黑名单、会话等
```

### 3. Nginx 缓存

```nginx
# 静态资源缓存
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

---

## 📞 技术支持

- 文档：https://docs.yourdomain.com
- 邮箱：support@yourdomain.com
- GitHub Issues：https://github.com/yourusername/idoctor-commercial/issues

---

**最后更新**：2025-01-17
**维护者**：iDoctor DevOps Team
