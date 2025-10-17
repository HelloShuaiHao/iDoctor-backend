# iDoctor 商业化模块

> 认证、支付、配额管理的完整商业化解决方案
> 包含后端服务和前端测试应用

## 📁 项目结构

```
commercial/
├── 📄 文档
│   ├── docs/                          # 📚 所有文档
│   │   ├── QUICK_START.md            # 后端快速开始
│   │   ├── API_GUIDE.md              # API 使用指南
│   │   ├── PROJECT_STATUS.md         # 项目进度
│   │   └── FRONTEND_STRUCTURE.md     # 前端架构
│   └── README.md                      # 本文件
│
├── 🔧 后端服务
│   ├── auth_service/                  # 认证服务 (端口 9001)
│   │   ├── api/                       # API 路由
│   │   ├── core/                      # 核心逻辑
│   │   ├── models/                    # 数据模型
│   │   └── schemas/                   # Pydantic 模式
│   ├── payment_service/               # 支付服务 (端口 9002)
│   │   ├── api/                       # API 路由
│   │   ├── core/                      # 核心逻辑
│   │   ├── models/                    # 数据模型
│   │   ├── providers/                 # 支付提供商
│   │   └── schemas/                   # Pydantic 模式
│   ├── quota_service/                 # 配额服务
│   │   ├── models/                    # 配额模型
│   │   └── services/                  # 配额服务
│   └── shared/                        # 共享模块
│       ├── config.py                  # 配置管理
│       ├── database.py                # 数据库连接
│       └── exceptions.py              # 自定义异常
│
├── 🎨 前端应用
│   └── frontend/                      # React 测试应用 (端口 3000)
│       ├── src/
│       │   ├── components/            # React 组件
│       │   ├── pages/                 # 页面组件
│       │   ├── services/              # API 服务
│       │   ├── hooks/                 # 自定义 Hooks
│       │   ├── context/               # React Context
│       │   ├── types/                 # TypeScript 类型
│       │   └── utils/                 # 工具函数
│       ├── README.md                  # 前端文档
│       └── QUICK_START.md             # 前端快速开始
│
├── 🗄️ 数据库
│   └── alembic/                       # 数据库迁移
│       └── versions/                  # 迁移版本
│
├── 🐳 部署
│   ├── docker/                        # Docker 配置
│   │   ├── docker-compose.yml        # 容器编排
│   │   └── Dockerfile.init           # 初始化镜像
│   ├── start.sh                       # macOS/Linux 启动
│   └── start.bat                      # Windows 启动
│
└── 🔨 工具
    ├── scripts/                       # 初始化脚本
    │   ├── create_admin.py           # 创建管理员
    │   └── seed_plans.py             # 初始化订阅计划
    └── requirements.txt               # Python 依赖
```

## 🚀 快速开始

### 一键启动（推荐）

```bash
./start.sh              # macOS/Linux
start.bat               # Windows
```

启动后访问：
- 🔐 认证服务: http://localhost:9001/docs
- 💳 支付服务: http://localhost:9002/docs
- 🎨 前端应用: http://localhost:3000

### 分步启动

#### 1. 启动后端服务

```bash
cd docker
docker compose up -d
```

#### 2. 启动前端应用

```bash
cd frontend
npm install
npm run dev
```

## 📚 文档导航

### 快速入门
- [后端快速开始](./docs/QUICK_START.md) - 后端服务启动指南
- [前端快速开始](./frontend/QUICK_START.md) - 前端应用启动指南

### 开发文档
- [API 使用指南](./docs/API_GUIDE.md) - 所有 API 端点详细说明
- [项目进度](./docs/PROJECT_STATUS.md) - 当前开发状态
- [前端架构](./docs/FRONTEND_STRUCTURE.md) - 前端项目结构规划

### 部署文档
- [Docker 指南](./docs/DOCKER_GUIDE.md) - Docker 部署说明

## ✨ 核心功能

### 🔐 认证服务 (9001)
- ✅ 用户注册/登录
- ✅ JWT Token 管理
- ✅ API Key 生成
- ✅ 权限验证

### 💳 支付服务 (9002)
- ✅ 支付宝/微信支付
- ✅ 订阅计划管理
- ✅ 支付回调处理
- ✅ 退款功能

### 📊 配额服务
- ✅ 多应用配额管理
- ✅ 使用跟踪
- ✅ 限流控制
- ⏳ API 端点（开发中）

### 🎨 前端应用 (3000)
- ✅ 用户认证界面
- ✅ 订阅计划展示
- ✅ 用户仪表板
- ⏳ 支付流程（开发中）

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: PostgreSQL
- **ORM**: SQLAlchemy 2.0
- **认证**: JWT + bcrypt
- **支付**: 支付宝/微信 SDK

### 前端
- **框架**: React 18 + TypeScript
- **构建**: Vite
- **UI**: shadcn/ui + Tailwind CSS
- **路由**: React Router v6
- **HTTP**: Axios

## 💡 使用示例

### 测试认证流程

```bash
# 1. 注册用户
curl -X POST http://localhost:9001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"test","password":"pass123"}'

# 2. 登录获取 Token
curl -X POST http://localhost:9001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"test","password":"pass123"}'

# 3. 获取用户信息
curl http://localhost:9001/users/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 测试支付流程

```bash
# 1. 查看订阅计划
curl http://localhost:9002/plans/

# 2. 创建支付订单
curl -X POST http://localhost:9002/payments/ \
  -H "Content-Type: application/json" \
  -d '{"amount":99,"currency":"CNY","payment_method":"alipay"}'
```

### 前端测试

1. 访问 http://localhost:3000
2. 点击"注册"创建账号
3. 登录后查看控制台
4. 浏览订阅计划

## 📊 开发状态

### 已完成 ✅
- 认证服务完整实现
- 支付服务核心功能
- 配额管理系统架构
- 前端基础框架
- Docker 容器化部署

### 进行中 🚧
- 配额服务 API
- 前端支付流程
- 前端订阅管理

### 待开发 📋
- 系统集成测试
- 生产环境优化
- 监控和日志系统

## 📞 支持

- 📖 API 文档: http://localhost:9001/docs
- 📖 支付文档: http://localhost:9002/docs
- 📁 更多文档: 查看 `docs/` 目录
- 🐛 问题反馈: 创建 Issue

## 📄 许可证

MIT License

---

**快速开始**: `./start.sh` 然后访问 http://localhost:3000
