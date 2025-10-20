# 🚀 快速启动指南

## Mac 本地开发环境

### 推荐启动方式（3步）⭐

```bash
# 1. 启动 Commercial 模块（使用一键部署脚本）
bash commercial/scripts/deploy-all.sh dev

# 2. 启动 CTAI Backend（新终端）
cd iDoctor-backend
python main.py  # 运行在 4200 端口

# 3. 启动 CTAI_web（新终端）
cd CTAI_web
npm run mac  # 运行在 7500 端口
```

> **说明**: `deploy-all.sh dev` 脚本会自动：
> - ✅ 检查前置条件（Node.js, npm, Docker）
> - ✅ 构建 Commercial 前端
> - ✅ 启动 Docker 服务（Nginx + Auth + Payment + DB）
> - ✅ 验证服务健康状态

### 访问地址

- **Commercial 前端**: http://localhost:3000
- **CTAI_web 前端**: http://localhost:3000/ctai
- **CTAI_web 直接访问**: http://localhost:7500 (开发调试)

---

## 服务器生产环境

### 一键部署

```bash
# 1. 启动 Commercial 模块（使用一键部署脚本）
bash commercial/scripts/deploy-all.sh prod

# 2. 启动 CTAI Backend（新终端）
cd iDoctor-backend
python main.py  # 运行在 4200 端口

# 3. 启动 CTAI_web（新终端）
cd CTAI_web
npm run server  # 运行在 7500 端口
```

> **说明**: `deploy-all.sh prod` 脚本会自动：
> - ✅ 读取 `.env.prod` 配置
> - ✅ 构建 Commercial 前端（生产模式）
> - ✅ 启动 Docker 服务（使用 docker-compose.prod.yml）
> - ✅ 验证服务健康状态

### 访问地址

- **Commercial 前端**: http://ai.bygpu.com:55305
- **CTAI_web 前端**: http://ai.bygpu.com:55305/ctai

---

## 快速参考表

### 端口映射

| 服务 | 本地端口 | 服务器端口 | 说明 |
|------|---------|-----------|------|
| Nginx | 3000 | 55305 | 统一入口 |
| CTAI Backend | 4200 | 55303 | 主应用 API |
| CTAI_web | 7500 | 55304 | 前端开发服务器 |
| Auth Service | - | - | Docker 内部 9001 |
| Payment Service | - | - | Docker 内部 9002 |

### 常用命令

```bash
# 查看 Docker 服务状态
cd commercial/docker
docker-compose ps

# 查看服务日志
docker-compose logs -f auth_service
docker-compose logs -f frontend_nginx

# 重启 Nginx
docker-compose restart frontend_nginx

# 重新构建并启动
docker-compose build frontend_nginx && docker-compose up -d frontend_nginx

# 检查端口占用
lsof -i:3000  # Nginx
lsof -i:4200  # CTAI Backend
lsof -i:7500  # CTAI_web
```

### 环境变量文件

| 环境 | CTAI_web | Commercial | 启动命令 |
|------|----------|-----------|---------|
| Mac 本地 | `.env.local` | `.env.development` | `deploy-all.sh dev` + `npm run mac` |
| 服务器 | `.env.production` | `.env.production` | `deploy-all.sh prod` + `npm run server` |

---

## 🛠️ 部署脚本说明

### deploy-all.sh 参数

```bash
bash commercial/scripts/deploy-all.sh [环境]

环境选项:
  dev   - 本地开发环境（默认）
  prod  - 生产环境
```

### 脚本执行流程

1. **检查前置条件**
   - Node.js >= 16
   - npm
   - Docker
   - Docker Compose

2. **构建前端**
   - `dev`: 运行 `npm run build:dev`
   - `prod`: 运行 `npm run build:prod`

3. **启动 Docker 服务**
   - 停止现有服务
   - 构建 Docker 镜像
   - 启动服务（包括 db_init 初始化）

4. **验证部署**
   - 检查容器健康状态
   - 测试 Nginx 健康检查
   - 测试 API 代理

5. **显示部署信息**
   - 访问地址
   - 常用命令
   - 日志查看方式

---

## 🐛 故障排查

### 问题: 无法访问 /ctai

```bash
# 1. 检查 CTAI_web 是否运行
lsof -i:7500

# 2. 检查 Nginx 配置
docker exec idoctor_commercial_nginx curl -I http://host.docker.internal:7500/

# 3. 重启 CTAI_web
cd CTAI_web
npm run mac  # 或 npm run server
```

### 问题: API 404 错误

```bash
# 1. 检查后端是否运行
lsof -i:4200

# 2. 测试后端健康
curl http://localhost:4200/health

# 3. 查看 Nginx 错误日志
docker exec idoctor_commercial_nginx tail -f /var/log/nginx/idoctor-commercial-error.log
```

### 问题: 浏览器缓存

```
# 解决方法：
1. 打开无痕窗口测试
2. 开发者工具 > Network > 勾选 "Disable cache"
3. 硬刷新: Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows)
```

### 问题: Docker 容器启动失败

```bash
# 查看容器日志
docker-compose logs -f [service_name]

# 重新构建容器
docker-compose build --no-cache [service_name]
docker-compose up -d [service_name]

# 完全重置
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

详细文档请参考: [architecture-overview.md](./architecture-overview.md)

**最后更新**: 2025-10-20
**维护者**: iDoctor Team
