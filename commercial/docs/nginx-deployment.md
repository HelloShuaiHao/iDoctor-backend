# iDoctor Commercial Nginx 部署指南

本文档介绍如何在服务器上部署 iDoctor Commercial 前端应用，使用 Nginx 反向代理统一管理前后端服务。

## 目录

- [架构说明](#架构说明)
- [前置要求](#前置要求)
- [部署步骤](#部署步骤)
- [验证部署](#验证部署)
- [常见问题](#常见问题)
- [SSL/HTTPS 配置](#sslhttps-配置)

---

## 架构说明

### 服务端口映射

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|---------|---------|------|
| Commercial 前端 | 3000 | 55305 | React 应用 |
| 主应用前端 | 7500 | 55304 | Flask/Vue 应用 |
| 认证服务 | 9001 | - | FastAPI (内网) |
| 支付服务 | 9002 | - | FastAPI (内网) |
| 主应用API | 4200 | - | FastAPI (内网) |

### API 路由规则

```
http://ai.bygpu.com:55305/
├── /                      → 前端静态资源 (/var/www/idoctor-commercial/dist)
├── /api/auth/*            → http://localhost:9001/*
├── /api/payment/*         → http://localhost:9002/*
└── /api/idoctor/*         → http://localhost:4200/*
```

**优势**: 所有请求同域，**无 CORS 问题**，便于监控和日志管理。

---

## 前置要求

### 1. 安装 Nginx

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install nginx -y
```

**CentOS/RHEL:**
```bash
sudo yum install epel-release -y
sudo yum install nginx -y
```

**验证安装:**
```bash
nginx -v
# 输出: nginx version: nginx/1.18.0 (或更高版本)
```

### 2. 安装 Node.js (用于构建前端)

```bash
# 使用 nvm 安装 (推荐)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18

# 验证
node -v  # v18.x.x
npm -v   # 9.x.x
```

### 3. 确保后端服务运行

```bash
# 检查认证服务
curl http://localhost:9001/health
# 输出: {"status":"ok","service":"auth"}

# 检查支付服务
curl http://localhost:9002/health
# 输出: {"status":"ok","service":"payment"}

# 检查主应用
curl http://localhost:4200/health
# 输出: {"status":"ok"}
```

---

## 部署步骤

### Step 1: 构建前端应用

```bash
# 进入前端目录
cd /path/to/iDoctor-backend/commercial/frontend

# 安装依赖
npm install

# 生产环境构建
npm run build

# 构建完成后，dist 目录包含静态文件
ls -lh dist/
```

### Step 2: 部署前端文件到服务器

```bash
# 创建部署目录
sudo mkdir -p /var/www/idoctor-commercial

# 复制构建产物
sudo cp -r dist/* /var/www/idoctor-commercial/

# 设置权限
sudo chown -R www-data:www-data /var/www/idoctor-commercial
sudo chmod -R 755 /var/www/idoctor-commercial

# 验证文件
ls -lh /var/www/idoctor-commercial/
# 应该看到: index.html, assets/, vite.svg 等文件
```

### Step 3: 配置 Nginx

```bash
# 复制配置文件
sudo cp commercial/nginx/idoctor-commercial.conf /etc/nginx/sites-available/

# 创建软链接（启用配置）
sudo ln -s /etc/nginx/sites-available/idoctor-commercial.conf /etc/nginx/sites-enabled/

# 测试配置语法
sudo nginx -t
# 输出: nginx: configuration file /etc/nginx/nginx.conf test is successful

# 重载 Nginx 配置
sudo systemctl reload nginx

# 或使用 nginx 命令
sudo nginx -s reload
```

### Step 4: 配置防火墙

```bash
# Ubuntu (ufw)
sudo ufw allow 55305/tcp
sudo ufw reload

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=55305/tcp
sudo firewall-cmd --reload

# 验证端口监听
sudo netstat -tulnp | grep 55305
# 或
sudo ss -tulnp | grep 55305
```

---

## 验证部署

### 1. 访问前端

打开浏览器访问: `http://ai.bygpu.com:55305`

应该看到 iDoctor Commercial 登录页面。

### 2. 测试 API 代理

```bash
# 测试认证 API
curl http://ai.bygpu.com:55305/api/auth/health
# 输出: {"status":"ok","service":"auth"}

# 测试支付 API
curl http://ai.bygpu.com:55305/api/payment/health
# 输出: {"status":"ok","service":"payment"}

# 测试主应用 API
curl http://ai.bygpu.com:55305/api/idoctor/health
# 输出: {"status":"ok"}
```

### 3. 检查浏览器控制台

打开浏览器开发者工具 (F12)：
- **Network 标签**: 确认所有请求都是 `http://ai.bygpu.com:55305/api/*`
- **Console 标签**: 不应该有 CORS 错误

### 4. 测试注册/登录

1. 访问 `http://ai.bygpu.com:55305/register`
2. 输入邮箱和密码
3. 发送验证码
4. 完成注册

---

## 常见问题

### Q1: 访问前端返回 502 Bad Gateway

**原因**: 后端服务未启动或端口错误。

**解决**:
```bash
# 检查后端服务状态
docker ps | grep idoctor

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/idoctor-commercial-error.log

# 重启后端服务
cd /path/to/iDoctor-backend/commercial/docker
docker-compose up -d
```

### Q2: API 请求返回 404 Not Found

**原因**: Nginx 配置的 `proxy_pass` 路径错误。

**解决**:
```bash
# 检查配置中的尾部斜杠
# 正确: proxy_pass http://localhost:9001/;
# 错误: proxy_pass http://localhost:9001;  (缺少斜杠)

# 修改后重载配置
sudo nginx -s reload
```

### Q3: 上传大文件失败

**原因**: Nginx 默认请求体大小限制为 1MB。

**解决**: 已在配置中设置 `client_max_body_size 500M;`

如需调整:
```nginx
http {
    client_max_body_size 1G;  # 全局设置
}
```

### Q4: 前端更新后浏览器仍显示旧版本

**原因**: 浏览器缓存。

**解决**:
1. 清除浏览器缓存 (Ctrl+Shift+Delete)
2. 或强制刷新 (Ctrl+Shift+R / Cmd+Shift+R)
3. 或打开无痕模式测试

### Q5: Nginx 日志文件过大

**解决**: 配置日志轮转

```bash
# 编辑 /etc/logrotate.d/nginx
sudo nano /etc/logrotate.d/nginx

# 添加配置:
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

---

## SSL/HTTPS 配置

### 使用 Let's Encrypt 免费证书

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 自动配置 SSL
sudo certbot --nginx -d ai.bygpu.com

# Certbot 会自动:
# 1. 获取 SSL 证书
# 2. 修改 Nginx 配置
# 3. 设置自动续期

# 测试自动续期
sudo certbot renew --dry-run
```

### 手动配置 SSL（如果有自己的证书）

1. 将证书文件放到服务器:
```bash
sudo mkdir -p /etc/nginx/ssl
sudo cp your-cert.crt /etc/nginx/ssl/idoctor-commercial.crt
sudo cp your-cert.key /etc/nginx/ssl/idoctor-commercial.key
sudo chmod 600 /etc/nginx/ssl/idoctor-commercial.key
```

2. 取消注释 `idoctor-commercial.conf` 中的 HTTPS 配置部分

3. 重载 Nginx:
```bash
sudo nginx -t
sudo nginx -s reload
```

4. 更新前端环境变量:
```bash
# .env.production
VITE_IDOCTOR_APP_URL=https://ai.bygpu.com:55304
```

5. 重新构建前端并部署

---

## 监控和日志

### 查看实时日志

```bash
# 访问日志
sudo tail -f /var/log/nginx/idoctor-commercial-access.log

# 错误日志
sudo tail -f /var/log/nginx/idoctor-commercial-error.log

# 结合使用
sudo tail -f /var/log/nginx/idoctor-commercial-*.log
```

### 日志分析

```bash
# 统计访问量
sudo wc -l /var/log/nginx/idoctor-commercial-access.log

# 查看最频繁的 IP
sudo awk '{print $1}' /var/log/nginx/idoctor-commercial-access.log | sort | uniq -c | sort -rn | head -10

# 查看 API 请求统计
sudo grep "/api/" /var/log/nginx/idoctor-commercial-access.log | awk '{print $7}' | sort | uniq -c | sort -rn
```

---

## 性能优化

### 启用 HTTP/2

```nginx
listen 443 ssl http2;
```

### 启用 Brotli 压缩（比 gzip 更高效）

```bash
# 安装 Brotli 模块
sudo apt install nginx-module-brotli -y

# 在 nginx.conf 中添加
load_module modules/ngx_http_brotli_filter_module.so;
load_module modules/ngx_http_brotli_static_module.so;

# 在 server 块中添加
brotli on;
brotli_comp_level 6;
brotli_types text/plain text/css application/json application/javascript text/xml application/xml+rss;
```

### 配置缓存

```nginx
# 添加到 http 块
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;

# 在 location 块中使用
location /api/payment/plans {
    proxy_cache api_cache;
    proxy_cache_valid 200 10m;
    proxy_pass http://localhost:9002/plans;
}
```

---

## 维护命令

```bash
# 启动 Nginx
sudo systemctl start nginx

# 停止 Nginx
sudo systemctl stop nginx

# 重启 Nginx
sudo systemctl restart nginx

# 重载配置（不中断服务）
sudo systemctl reload nginx

# 查看状态
sudo systemctl status nginx

# 开机自启
sudo systemctl enable nginx

# 测试配置
sudo nginx -t

# 查看 Nginx 版本和编译选项
nginx -V
```

---

## 总结

✅ **已完成配置**:
- Nginx 反向代理统一所有 API 请求
- 前端静态资源部署
- 文件上传大小限制 (500MB)
- Gzip 压缩
- 健康检查端点

🎯 **下一步**:
1. 配置 SSL 证书（推荐 Let's Encrypt）
2. 设置日志轮转
3. 配置监控告警
4. 性能优化和缓存策略

📚 **相关文档**:
- [Nginx 官方文档](https://nginx.org/en/docs/)
- [Let's Encrypt 官方指南](https://letsencrypt.org/getting-started/)
- [商业化系统文档](../README.md)

---

**部署完成！** 🎉

现在您可以通过 `http://ai.bygpu.com:55305` 访问 iDoctor Commercial 平台了。
