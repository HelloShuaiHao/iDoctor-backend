# iDoctor Commercial 架构总览

## 🏗️ 系统架构

### 服务组件

| 组件 | 端口 | 说明 |
|------|------|------|
| **Nginx** | 3000 (内部) | 统一入口，反向代理 |
| **Commercial Frontend** | - | 静态文件，由 Nginx 直接服务 |
| **CTAI_web Frontend** | 7500 | 独立运行，通过 Nginx 代理 |
| **Auth Service** | 9001 | 认证服务（Docker） |
| **Payment Service** | 9002 | 支付服务（Docker） |
| **CTAI Backend** | 4200 | CTAI 主应用（宿主机） |
| **PostgreSQL** | 5432 | 数据库（Docker） |

---

## 📍 本地开发环境 (Mac)

### 访问地址
- **主入口**: `http://localhost:3000`
- **Commercial 前端**: `http://localhost:3000/`
- **CTAI_web 前端**: `http://localhost:3000/ctai`
- **CTAI_web 直接访问**: `http://localhost:7500/` (开发调试用)

### Nginx 代理配置

#### 1. 前端路由

```nginx
# Commercial 前端（静态文件）
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}

# CTAI_web 前端（代理到宿主机 7500）
location /ctai/ {
    proxy_pass http://host.docker.internal:7500/;
    # 去掉 /ctai/ 前缀，代理到根路径
}
```

#### 2. API 路由

| 前端请求路径 | Nginx 代理到 | 最终路由 | 说明 |
|------------|-------------|---------|------|
| `/api/auth/login` | `auth_service:9001` | `/auth/login` | 登录接口 |
| `/api/auth/register` | `auth_service:9001` | `/auth/register` | 注册接口 |
| `/api/users/me` | `auth_service:9001` | `/users/me` | 获取用户信息 |
| `/api/api-keys/` | `auth_service:9001` | `/api-keys/` | API 密钥管理 |
| `/api/payments/` | `payment_service:9002` | `/payments/` | 支付交易 |
| `/api/plans/` | `payment_service:9002` | `/plans/` | 订阅计划 |
| `/api/subscriptions/` | `payment_service:9002` | `/subscriptions/` | 订阅管理 |
| `/api/ctai/*` | `host.docker.internal:4200` | `/*` | CTAI 后端 API |

### 启动步骤

#### 1. 启动 Docker 服务（Nginx + Auth + Payment + DB）

```bash
cd commercial/docker
docker-compose up -d
```

**启动的服务**：
- ✅ PostgreSQL (5432)
- ✅ Auth Service (9001)
- ✅ Payment Service (9002)
- ✅ Nginx (3000)

#### 2. 启动 CTAI 后端（宿主机）

```bash
cd iDoctor-backend
# 根据你的启动方式，例如：
python main.py
# 或其他启动命令，确保运行在 4200 端口
```

**检查启动**：
```bash
lsof -i:4200  # 应该看到 Python 进程
```

#### 3. 启动 CTAI_web 前端（宿主机）

```bash
cd CTAI_web
npm run mac  # Mac 本地开发模式
```

**检查启动**：
```bash
lsof -i:7500  # 应该看到 node 进程
```

访问 `http://localhost:3000/ctai` 应该能看到 CTAI_web 界面。

#### 4. 启动 Commercial 前端（开发模式，可选）

如果需要开发 Commercial 前端：

```bash
cd commercial/frontend
npm run dev  # 开发模式，通常在其他端口
```

生产构建：

```bash
npm run build:dev  # 构建到 dist/
```

### 环境变量配置

#### CTAI_web (.env.local)

```bash
# Mac 本地开发环境
VUE_APP_BASE_URL=http://localhost:3000/api/ctai
VUE_APP_AUTH_BASE_URL=http://localhost:3000/api/auth
VUE_APP_COMMERCIAL_URL=http://localhost:3000
```

#### Commercial Frontend (.env.development)

```bash
VITE_AUTH_API_BASE_URL=http://localhost:3000/api/auth
VITE_PAYMENT_API_BASE_URL=http://localhost:3000/api/payments
```

---

## 🚀 服务器生产环境

### 访问地址
- **主入口**: `http://ai.bygpu.com:55305`
- **Commercial 前端**: `http://ai.bygpu.com:55305/`
- **CTAI_web 前端**: `http://ai.bygpu.com:55305/ctai`

### 端口映射

| 内部端口 | 外部端口 | 服务 |
|---------|---------|------|
| 3000 | 55305 | Nginx |
| 9001 | - | Auth Service (内部) |
| 9002 | - | Payment Service (内部) |
| 5432 | - | PostgreSQL (内部) |
| 4200 | 55303 | CTAI Backend (宿主机) |
| 7500 | 55304 | CTAI_web Dev Server (宿主机，可选) |

### Nginx 代理配置

与本地环境相同，只是主机名不同：

```nginx
# 服务器上 Nginx 配置
NGINX_PORT=3000
NGINX_SERVER_NAME=ai.bygpu.com
IDOCTOR_API_HOST=host.docker.internal
IDOCTOR_API_PORT=4200
```

### 启动步骤

#### 1. 启动 Docker 服务（生产模式）

```bash
cd commercial/docker

# 首次部署：创建 .env.prod
cp .env.prod.example .env.prod
# 编辑 .env.prod，配置生产环境参数

# 启动生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### 2. 启动 CTAI 后端（宿主机 4200）

```bash
cd iDoctor-backend
# 启动 CTAI 后端，监听 4200 端口
python main.py
```

#### 3. 启动 CTAI_web 前端（两种方式）

**方式 A：使用开发服务器（推荐用于测试）**

```bash
cd CTAI_web
npm run server  # 生产模式，运行在 7500 端口
```

**方式 B：使用静态文件部署**

```bash
cd CTAI_web

# 构建生产版本
npm run build:server

# 使用静态文件服务器（例如：nginx、serve）
# 或者将 dist/ 目录部署到其他服务器
npx serve -s dist -l 7500
```

#### 4. 构建并部署 Commercial 前端

```bash
cd commercial/frontend

# 构建生产版本
npm run build:prod

# 产物会输出到 dist/
# Docker 会自动挂载这个目录到 Nginx
```

### 环境变量配置

#### CTAI_web (.env.production)

```bash
# 服务器生产环境
VUE_APP_BASE_URL=http://ai.bygpu.com:55305/api/ctai
VUE_APP_AUTH_BASE_URL=http://ai.bygpu.com:55305/api/auth
VUE_APP_COMMERCIAL_URL=http://ai.bygpu.com:55305
```

#### Commercial Frontend (.env.production)

```bash
VITE_AUTH_API_BASE_URL=http://ai.bygpu.com:55305/api/auth
VITE_PAYMENT_API_BASE_URL=http://ai.bygpu.com:55305/api/payments
```

---

## 🔄 一键部署脚本

### 本地开发环境

```bash
cd commercial
bash scripts/deploy-all.sh dev
```

**脚本会自动**：
1. 构建 Commercial 前端
2. 启动 Docker 服务（Nginx + Auth + Payment + DB）
3. 验证服务健康状态

**手动启动 CTAI 相关服务**：
- CTAI Backend: `python main.py`
- CTAI_web: `cd CTAI_web && npm run mac`

### 服务器生产环境

```bash
cd commercial
bash scripts/deploy-all.sh prod
```

**脚本会自动**：
1. 读取 `.env.prod` 配置
2. 构建 Commercial 前端（生产模式）
3. 启动 Docker 服务（使用 docker-compose.prod.yml）
4. 验证服务健康状态

**手动启动 CTAI 相关服务**：
- CTAI Backend: `python main.py`
- CTAI_web: `cd CTAI_web && npm run server`

---

## 🧪 验证部署

### 检查服务状态

```bash
# 检查 Docker 服务
cd commercial/docker
docker-compose ps

# 检查端口占用
lsof -i:3000  # Nginx
lsof -i:4200  # CTAI Backend
lsof -i:7500  # CTAI_web
```

### 测试 API 端点

```bash
# 本地环境
curl http://localhost:3000/health                    # Nginx 健康检查
curl http://localhost:3000/api/auth/health           # 认证服务
curl http://localhost:3000/api/payments/health       # 支付服务（如果有）

# 服务器环境
curl http://ai.bygpu.com:55305/health
curl http://ai.bygpu.com:55305/api/auth/health
```

### 查看日志

```bash
# Docker 服务日志
docker-compose logs -f auth_service
docker-compose logs -f payment_service
docker-compose logs -f frontend_nginx

# Nginx 访问日志
docker exec idoctor_commercial_nginx tail -f /var/log/nginx/idoctor-commercial-access.log

# Nginx 错误日志
docker exec idoctor_commercial_nginx tail -f /var/log/nginx/idoctor-commercial-error.log
```

---

## 🐛 常见问题

### 1. Nginx 404 错误

**问题**：访问 `/ctai` 返回 404

**检查**：
```bash
# 检查 CTAI_web 是否运行
lsof -i:7500

# 检查 Nginx 配置
docker exec idoctor_commercial_nginx cat /etc/nginx/conf.d/default.conf | grep -A 5 "location /ctai"

# 从 Nginx 容器测试连接
docker exec idoctor_commercial_nginx curl -I http://host.docker.internal:7500/
```

**解决**：确保 CTAI_web 在 7500 端口运行

### 2. CORS 错误

**问题**：浏览器控制台显示 CORS 错误

**检查**：Nginx 配置中是否正确设置了 CORS headers

**解决**：已在 `/api/auth/` 路由中配置 OPTIONS 预检

### 3. 认证失败

**问题**：登录后立即退出或 401 错误

**检查**：
```bash
# 检查 token 是否保存
# 浏览器开发者工具 > Application > Local Storage

# 检查 auth_service 日志
docker-compose logs -f auth_service
```

### 4. 数据库初始化失败

**问题**：订阅计划表为空

**解决**：
```bash
cd commercial/docker
docker-compose build --no-cache db_init
docker-compose up db_init
```

---

## 📝 配置文件清单

### 本地开发

```
commercial/
├── docker/
│   ├── docker-compose.yml           # 本地开发 Docker 配置
│   └── .env (可选)                   # 本地环境变量覆盖
├── frontend/
│   ├── .env.development              # 本地开发环境变量
│   └── dist/                         # 构建产物（挂载到 Nginx）
└── nginx/
    └── nginx.conf.template           # Nginx 配置模板

CTAI_web/
├── .env.local                        # Mac 本地开发环境变量
└── package.json                      # npm run mac
```

### 服务器生产

```
commercial/
├── docker/
│   ├── docker-compose.yml            # 基础配置
│   ├── docker-compose.prod.yml       # 生产环境覆盖
│   ├── .env.prod.example             # 生产环境配置示例
│   └── .env.prod                     # 实际生产配置（需创建）
├── frontend/
│   ├── .env.production               # 生产环境变量
│   └── dist/                         # 构建产物
└── scripts/
    └── deploy-all.sh                 # 一键部署脚本

CTAI_web/
├── .env.production                   # 服务器生产环境变量
└── package.json                      # npm run server
```

---

## 📊 请求流程图

### Commercial Frontend 请求流程

```
浏览器 → http://ai.bygpu.com:55305/
    ↓
Nginx (55305:3000)
    ↓
静态文件 /usr/share/nginx/html/
    ↓
返回 Commercial index.html
```

### CTAI_web 请求流程

```
浏览器 → http://ai.bygpu.com:55305/ctai
    ↓
Nginx (55305:3000)
    ↓
proxy_pass → host.docker.internal:7500
    ↓
CTAI_web Dev Server (7500)
    ↓
返回 CTAI_web 页面
```

### API 请求流程

```
浏览器 → http://ai.bygpu.com:55305/api/auth/login
    ↓
Nginx (55305:3000)
    ↓
rewrite /api/auth/login → /auth/login
    ↓
proxy_pass → auth_service:9001
    ↓
Auth Service 处理
    ↓
返回 JWT token
```

```
浏览器 → http://ai.bygpu.com:55305/api/ctai/admin/quotas/users/me
    ↓
Nginx (55305:3000)
    ↓
rewrite /api/ctai/* → /*
    ↓
proxy_pass → host.docker.internal:4200
    ↓
CTAI Backend 处理
    ↓
返回配额信息
```

---

## 🔐 安全注意事项

1. **生产环境**：
   - 修改 `.env.prod` 中的 `POSTGRES_PASSWORD`
   - 使用 HTTPS（配置 SSL 证书）
   - 限制数据库访问权限

2. **密钥管理**：
   - 不要将 `.env.prod` 提交到 Git
   - 使用环境变量管理敏感信息

3. **CORS 配置**：
   - 生产环境限制 `Access-Control-Allow-Origin`
   - 当前配置为 `$http_origin`，建议限制为特定域名

---

**最后更新**: 2025-10-20
**维护者**: iDoctor Team
