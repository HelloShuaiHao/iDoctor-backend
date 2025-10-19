# iDoctor Commercial Docker + Nginx 架构文档

## 目录

- [架构概览](#架构概览)
- [多环境支持](#多环境支持)
- [Nginx Docker化设计](#nginx-docker化设计)
- [部署流程](#部署流程)
- [环境变量配置](#环境变量配置)
- [路由与代理](#路由与代理)
- [常见问题](#常见问题)

---

## 架构概览

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Nginx (Docker容器)   │
              │  端口: 3000 / 55305   │
              └───────────┬───────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ 静态文件服务 │  │   API 代理    │  │ WebSocket    │
│  (React)     │  │  /api/auth    │  │   支持       │
│              │  │  /api/payment │  │              │
│              │  │  /api/idoctor │  │              │
└──────────────┘  └──────┬───────┘  └──────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ auth_service │  │payment_service│  │host.docker. │
│  (Docker)    │  │   (Docker)    │  │ internal    │
│  :9001       │  │   :9002       │  │  :4200      │
└──────┬───────┘  └──────┬────────┘  └──────────────┘
       │                 │
       └────────┬────────┘
                ▼
        ┌──────────────┐
        │  PostgreSQL   │
        │   (Docker)    │
        │    :5432      │
        └───────────────┘
```

### 容器清单

| 容器名称 | 服务 | 端口映射 | 说明 |
|---------|------|---------|------|
| `idoctor_commercial_nginx` | Nginx | 3000:3000 (dev) / 55305:3000 (prod) | 前端服务器 + API网关 |
| `idoctor_auth_service` | FastAPI | 9001:9001 | 认证服务 |
| `idoctor_payment_service` | FastAPI | 9002:9002 | 支付服务 |
| `idoctor_commercial_db` | PostgreSQL | 5432:5432 | 数据库 |
| `idoctor_db_init` | Python | - | 数据库初始化（一次性） |

---

## 多环境支持

### 环境对比

| 特性 | 本地开发 (dev) | 生产环境 (prod) |
|-----|---------------|----------------|
| 前端开发 | Vite dev server (npm run dev) | Nginx Docker |
| Nginx URL | http://localhost:3000 | http://ai.bygpu.com:55305 |
| API 代理 | Vite proxy → localhost:9001/9002 | Nginx proxy → auth_service:9001 |
| 后端服务 | Docker Compose | Docker Compose |
| 数据持久化 | Docker volume | 宿主机目录 |
| SSL | 不使用 | 可选 |

### 开发流程 (本地)

```bash
# 方式1: 前端开发模式（推荐）
cd commercial/frontend
npm run dev  # Vite dev server，支持热重载

# 后端服务
cd commercial/docker
docker-compose up -d auth_service payment_service

# 方式2: 完整 Docker 部署（测试用）
cd commercial
bash scripts/deploy-all.sh dev
```

### 生产部署流程

```bash
# 一键部署
cd commercial
bash scripts/deploy-all.sh prod

# 手动部署
cd commercial/frontend
npm run build

cd ../docker
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Nginx Docker化设计

### 设计原则

1. **环境变量驱动配置** - 通过环境变量适配不同环境，无需修改配置文件
2. **配置模板化** - 使用 `nginx.conf.template` + `envsubst` 动态生成配置
3. **容器化隔离** - 所有服务在同一 Docker 网络，统一管理
4. **静态文件挂载** - 前端构建产物通过 volume 挂载，便于更新

### 文件结构

```
commercial/
├── nginx/
│   ├── Dockerfile              # Nginx 镜像定义
│   ├── nginx.conf.template     # 配置模板（支持环境变量）
│   ├── docker-entrypoint.sh    # 启动脚本（替换环境变量）
│   └── idoctor-commercial.conf # 宿主机 Nginx 配置（备用）
├── docker/
│   ├── docker-compose.yml      # 基础配置
│   ├── docker-compose.prod.yml # 生产环境覆盖
│   └── .env.prod.example       # 生产环境变量示例
└── frontend/
    └── dist/                   # 构建产物（挂载到 Nginx）
```

### Nginx 容器启动流程

```
1. Docker启动 → docker-entrypoint.sh
2. 设置默认环境变量
3. envsubst 替换 nginx.conf.template → default.conf
4. nginx -t 测试配置
5. nginx -g 'daemon off;' 启动
```

### 环境变量说明

| 变量名 | 默认值 | 说明 |
|-------|--------|------|
| `NGINX_PORT` | 3000 | Nginx 容器内监听端口 |
| `NGINX_SERVER_NAME` | localhost | 服务器域名 |
| `AUTH_SERVICE_HOST` | auth_service | 认证服务地址（Docker网络内） |
| `AUTH_SERVICE_PORT` | 9001 | 认证服务端口 |
| `PAYMENT_SERVICE_HOST` | payment_service | 支付服务地址 |
| `PAYMENT_SERVICE_PORT` | 9002 | 支付服务端口 |
| `IDOCTOR_API_HOST` | host.docker.internal | 主应用地址 |
| `IDOCTOR_API_PORT` | 4200 | 主应用端口 |
| `STATIC_ROOT` | /usr/share/nginx/html | 静态文件目录 |

---

## 部署流程

### 快速部署（推荐）

```bash
# 开发环境
bash commercial/scripts/deploy-all.sh dev

# 生产环境
bash commercial/scripts/deploy-all.sh prod
```

### 手动部署

#### Step 1: 构建前端

```bash
cd commercial/frontend
npm install
npm run build
# 产物: dist/
```

#### Step 2: 配置环境变量（生产环境）

```bash
cd commercial/docker
cp .env.prod.example .env.prod

# 编辑 .env.prod
vim .env.prod
```

配置示例:
```bash
NGINX_PORT=3000
NGINX_EXTERNAL_PORT=55305
NGINX_SERVER_NAME=ai.bygpu.com
IDOCTOR_API_HOST=host.docker.internal
IDOCTOR_API_PORT=4200
```

#### Step 3: 启动 Docker 服务

```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d
```

#### Step 4: 验证部署

```bash
# 检查容器状态
docker-compose ps

# 测试 Nginx
curl http://localhost:3000/health

# 测试 API 代理
curl http://localhost:3000/api/auth/health
curl http://localhost:3000/api/payment/health
```

---

## 环境变量配置

### .env.prod 完整示例

```bash
# ==================== Nginx 配置 ====================
NGINX_PORT=3000
NGINX_EXTERNAL_PORT=55305
NGINX_SERVER_NAME=ai.bygpu.com

# ==================== 后端服务配置 ====================
# 主应用 API（宿主机）
IDOCTOR_API_HOST=host.docker.internal
IDOCTOR_API_PORT=4200

# ==================== 数据库配置 ====================
POSTGRES_PASSWORD=your_secure_password

# ==================== 可选配置 ====================
# 数据持久化目录
POSTGRES_DATA_DIR=/var/lib/idoctor/postgres_data
NGINX_LOGS_DIR=/var/log/idoctor/nginx
```

### docker-compose.yml 环境变量传递

```yaml
services:
  frontend_nginx:
    environment:
      NGINX_PORT: ${NGINX_PORT:-3000}
      NGINX_SERVER_NAME: ${NGINX_SERVER_NAME:-localhost}
      # ... 其他变量
```

---

## 路由与代理

### URL 路由规则

#### 开发环境 (localhost:3000)

```
http://localhost:3000/
├── /                       → React 应用（dist/index.html）
├── /subscription           → React Router（订阅页面）
├── /api-keys              → React Router（API密钥页面）
├── /api/auth/*            → auth_service:9001/*
├── /api/payment/*         → payment_service:9002/*
└── /api/idoctor/*         → host.docker.internal:4200/*
```

#### 生产环境 (ai.bygpu.com:55305)

```
http://ai.bygpu.com:55305/
├── /                       → React 应用
├── /subscription?token=xxx → 订阅页面（从 CTAI_web 跳转）
├── /api/auth/*            → auth_service:9001/*
├── /api/payment/*         → payment_service:9002/*
└── /api/idoctor/*         → host.docker.internal:4200/*
```

### 跨应用跳转

#### CTAI_web → Commercial

```javascript
// CTAI_web/src/components/Header.vue
const commercialUrl = process.env.VUE_APP_COMMERCIAL_URL; // http://ai.bygpu.com:55305
window.location.href = `${commercialUrl}/subscription?token=${token}`;
```

#### Commercial → CTAI_web

```typescript
// commercial/frontend/src/pages/HomePage.tsx
const idoctorUrl = import.meta.env.VITE_IDOCTOR_APP_URL; // http://ai.bygpu.com:55304
window.location.href = idoctorUrl;
```

### Token 传递机制

1. **CTAI_web 登录** → 获取 `access_token`
2. **点击"订阅管理"** → 跳转携带 token: `?token=xxx`
3. **Commercial 接收** → `AuthContext.tsx` 读取 URL 参数
4. **保存到 localStorage** → `localStorage.setItem('access_token', urlToken)`
5. **清除 URL 参数** → `window.history.replaceState({}, '', pathname)`
6. **自动登录** → 使用 token 获取用户信息

---

## 常见问题

### Q1: 本地开发时如何快速重启？

**方式1: 仅重启 Nginx**
```bash
docker-compose restart frontend_nginx
```

**方式2: 更新前端后重新挂载**
```bash
cd frontend
npm run build

# Nginx 会自动加载新的 dist/ 文件
docker-compose restart frontend_nginx
```

**方式3: 使用 Vite dev server（推荐）**
```bash
# 不使用 Docker Nginx，直接用 Vite
cd frontend
npm run dev  # 自动热重载
```

### Q2: 如何查看 Nginx 日志？

```bash
# 实时查看访问日志
docker exec idoctor_commercial_nginx tail -f /var/log/nginx/idoctor-commercial-access.log

# 实时查看错误日志
docker exec idoctor_commercial_nginx tail -f /var/log/nginx/idoctor-commercial-error.log

# 查看所有日志
docker logs -f idoctor_commercial_nginx
```

### Q3: 如何修改 Nginx 配置？

**修改环境变量**（推荐）:
```bash
# 编辑 .env.prod 或 docker-compose.yml
vim docker/.env.prod

# 重启 Nginx
docker-compose restart frontend_nginx
```

**修改配置模板**:
```bash
# 编辑模板
vim nginx/nginx.conf.template

# 重新构建并启动
docker-compose build frontend_nginx
docker-compose up -d frontend_nginx
```

### Q4: CORS 错误怎么办？

**检查清单**:
1. ✅ 前端 `.env.production` 使用相对路径 `/api/auth`
2. ✅ Nginx 配置了正确的 `proxy_set_header Host $host`
3. ✅ 后端 CORS 配置包含 Nginx 的域名

**调试方法**:
```bash
# 检查请求是否经过 Nginx
curl -v http://localhost:3000/api/auth/health

# 检查响应头
curl -I http://localhost:3000/api/auth/health
```

### Q5: 如何在生产环境配置 HTTPS？

**方式1: 使用 Let's Encrypt**
```bash
# 安装 Certbot
sudo apt install certbot

# 获取证书
sudo certbot certonly --standalone -d ai.bygpu.com

# 挂载证书到 Nginx
# docker-compose.yml:
volumes:
  - /etc/letsencrypt:/etc/letsencrypt:ro

# 修改 nginx.conf.template 添加 SSL 配置
```

**方式2: 使用自签名证书（测试）**
```bash
# 生成证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/nginx.key \
  -out nginx/ssl/nginx.crt

# 挂载证书
volumes:
  - ./nginx/ssl:/etc/nginx/ssl:ro
```

### Q6: Docker 容器无法访问宿主机服务（主应用 4200 端口）

**问题**: Nginx 容器内访问 `host.docker.internal:4200` 失败

**解决**:

**Linux**:
```yaml
# docker-compose.yml
services:
  frontend_nginx:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

**macOS/Windows**: 自动支持 `host.docker.internal`

### Q7: 如何升级/回滚部署？

**升级**:
```bash
# 1. 构建新版本前端
cd frontend
npm run build

# 2. 重启 Nginx（自动加载新 dist/）
cd ../docker
docker-compose restart frontend_nginx
```

**回滚**:
```bash
# 1. 恢复旧版本 dist/
cd frontend
git checkout HEAD~1 dist/

# 2. 或从备份恢复
cp -r dist.backup dist/

# 3. 重启 Nginx
cd ../docker
docker-compose restart frontend_nginx
```

---

## 监控与维护

### 健康检查

```bash
# Nginx 健康检查
curl http://localhost:3000/health

# 容器健康状态
docker ps --format "table {{.Names}}\t{{.Status}}"

# 自动健康检查（已在 docker-compose.yml 配置）
docker inspect idoctor_commercial_nginx | grep -A 10 Health
```

### 资源监控

```bash
# 容器资源使用
docker stats

# 磁盘使用
docker system df

# 清理未使用资源
docker system prune -a
```

### 日志轮转

**Docker 日志限制**:
```json
// /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

**Nginx 日志轮转**: 已通过 volume 持久化，可配置 logrotate

---

## 总结

### 关键特性

✅ **多环境支持** - dev/prod 配置分离
✅ **环境变量驱动** - 灵活配置，无需修改代码
✅ **一键部署** - `deploy-all.sh` 脚本自动化
✅ **Docker 隔离** - 所有服务容器化
✅ **API 网关** - Nginx 统一代理，无 CORS 问题
✅ **健康检查** - 自动监控服务状态
✅ **日志管理** - 统一日志输出和持久化

### 部署命令速查

```bash
# 开发环境
bash commercial/scripts/deploy-all.sh dev

# 生产环境
bash commercial/scripts/deploy-all.sh prod

# 查看日志
cd commercial/docker
docker-compose logs -f

# 停止服务
docker-compose down

# 重启单个服务
docker-compose restart frontend_nginx
```

---

**最后更新**: 2025-01-19
**版本**: 2.0
**相关文档**:
- [Nginx 部署指南](./nginx-deployment.md)
- [路由验证文档](./routing-verification.md)
