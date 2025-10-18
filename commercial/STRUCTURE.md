# 📁 项目文件组织结构

> 清晰的文件组织，便于维护和扩展

## 📂 完整目录树

```
commercial/
│
├── 📄 文档和配置
│   ├── README.md                      # 项目主文档
│   ├── STRUCTURE.md                   # 本文件 - 结构说明
│   ├── requirements.txt               # Python 依赖
│   ├── .env.example                   # 环境变量模板
│   └── alembic.ini                    # 数据库迁移配置
│
├── 📚 docs/ - 所有文档
│   ├── INDEX.md                       # 文档索引（入口）
│   ├── QUICK_START.md                 # 后端快速开始
│   ├── API_GUIDE.md                   # API 使用指南
│   ├── PROJECT_STATUS.md              # 项目进度
│   ├── FRONTEND_STRUCTURE.md          # 前端架构
│   ├── DOCKER_GUIDE.md                # Docker 指南
│   └── DELIVERY_SUMMARY.md            # 交付总结
│
├── 🔧 auth_service/ - 认证服务 (9001)
│   ├── api/                           # API 路由
│   │   ├── auth.py                    # 认证端点
│   │   ├── users.py                   # 用户管理
│   │   └── api_keys.py                # API Key 管理
│   ├── core/                          # 核心逻辑
│   │   ├── security.py                # 密码哈希、JWT
│   │   └── dependencies.py            # FastAPI 依赖
│   ├── models/                        # SQLAlchemy 模型
│   │   ├── user.py                    # 用户模型
│   │   └── api_key.py                 # API Key 模型
│   ├── schemas/                       # Pydantic 模式
│   │   ├── user.py                    # 用户模式
│   │   ├── auth.py                    # 认证模式
│   │   └── api_key.py                 # API Key 模式
│   └── app.py                         # 服务入口
│
├── 💳 payment_service/ - 支付服务 (9002)
│   ├── api/                           # API 路由
│   │   ├── payments.py                # 支付端点
│   │   ├── subscriptions.py           # 订阅管理
│   │   └── webhooks.py                # 支付回调
│   ├── core/                          # 核心逻辑
│   │   └── dependencies.py            # FastAPI 依赖
│   ├── models/                        # SQLAlchemy 模型
│   │   ├── subscription_plan.py       # 订阅计划
│   │   ├── user_subscription.py       # 用户订阅
│   │   └── payment_transaction.py     # 支付交易
│   ├── providers/                     # 支付提供商
│   │   ├── alipay.py                  # 支付宝集成
│   │   └── wechat.py                  # 微信支付集成
│   ├── schemas/                       # Pydantic 模式
│   │   ├── payment.py                 # 支付模式
│   │   └── subscription.py            # 订阅模式
│   └── app.py                         # 服务入口
│
├── 📊 quota_service/ - 配额服务
│   ├── models/                        # 配额模型
│   │   ├── application.py             # 应用模型
│   │   ├── quota_type.py              # 配额类型
│   │   ├── quota_limit.py             # 配额限制
│   │   └── quota_usage.py             # 使用记录
│   └── services/                      # 配额服务
│       ├── application_manager.py     # 应用管理
│       ├── quota_manager.py           # 配额管理
│       └── usage_tracker.py           # 使用跟踪
│
├── 🔗 shared/ - 共享模块
│   ├── config.py                      # 配置管理
│   ├── database.py                    # 数据库连接
│   └── exceptions.py                  # 自定义异常
│
├── 🎨 frontend/ - React 前端 (3000)
│   ├── src/
│   │   ├── components/                # React 组件
│   │   │   ├── ui/                    # shadcn/ui 基础组件
│   │   │   ├── auth/                  # 认证组件（待开发）
│   │   │   ├── payment/               # 支付组件（待开发）
│   │   │   └── subscription/          # 订阅组件（待开发）
│   │   ├── pages/                     # 页面组件
│   │   │   ├── HomePage.tsx           # 首页
│   │   │   ├── AuthPage.tsx           # 认证页面
│   │   │   ├── DashboardPage.tsx      # 用户仪表板
│   │   │   ├── SubscriptionPage.tsx   # 订阅管理
│   │   │   └── PaymentPage.tsx        # 支付页面
│   │   ├── services/                  # API 服务层
│   │   │   ├── api.ts                 # Axios 配置
│   │   │   ├── authService.ts         # 认证 API
│   │   │   ├── paymentService.ts      # 支付 API
│   │   │   └── subscriptionService.ts # 订阅 API
│   │   ├── hooks/                     # 自定义 Hooks
│   │   │   └── usePayment.ts          # 支付 Hook
│   │   ├── context/                   # React Context
│   │   │   └── AuthContext.tsx        # 认证上下文
│   │   ├── types/                     # TypeScript 类型
│   │   │   ├── auth.ts                # 认证类型
│   │   │   ├── payment.ts             # 支付类型
│   │   │   └── subscription.ts        # 订阅类型
│   │   ├── utils/                     # 工具函数
│   │   │   ├── constants.ts           # 常量定义
│   │   │   └── storage.ts             # LocalStorage 封装
│   │   ├── lib/                       # 库文件
│   │   │   └── utils.ts               # 工具函数
│   │   ├── App.tsx                    # 主应用
│   │   ├── main.tsx                   # 入口文件
│   │   └── router.tsx                 # 路由配置
│   ├── public/                        # 静态资源
│   ├── README.md                      # 前端文档
│   ├── QUICK_START.md                 # 快速开始
│   ├── package.json                   # 依赖管理
│   ├── vite.config.ts                 # Vite 配置
│   ├── tailwind.config.js             # Tailwind 配置
│   └── tsconfig.json                  # TypeScript 配置
│
├── 🗄️ alembic/ - 数据库迁移
│   ├── versions/                      # 迁移版本文件
│   ├── env.py                         # Alembic 环境配置
│   └── script.py.mako                 # 迁移脚本模板
│
├── 🐳 docker/ - Docker 配置
│   ├── docker-compose.yml             # Docker Compose 编排
│   ├── Dockerfile.init                # 数据库初始化镜像
│   └── .dockerignore                  # Docker 忽略文件
│
├── 🔨 scripts/ - 工具脚本
│   ├── create_admin.py                # 创建管理员
│   └── seed_plans.py                  # 初始化订阅计划
│
└── 🚀 启动脚本
    ├── start.sh                       # macOS/Linux 启动
    └── start.bat                      # Windows 启动
```

## 📋 文件组织原则

### 1. **按功能分层**
- 每个服务（auth/payment/quota）独立目录
- 统一的内部结构（api/core/models/schemas）

### 2. **文档集中管理**
- 所有文档放在 `docs/` 目录
- `docs/INDEX.md` 作为文档入口
- README.md 提供概览和快速开始

### 3. **前端独立项目**
- `frontend/` 作为独立的 React 项目
- 有自己的 package.json 和配置文件
- 有独立的文档（README + QUICK_START）

### 4. **配置文件分离**
- 环境变量：`.env.example`
- Docker：`docker/` 目录
- 数据库：`alembic/` 目录

## 🔍 快速查找指南

### 我想找...

#### 📖 文档
- **开始使用** → `README.md` 或 `docs/QUICK_START.md`
- **所有文档** → `docs/INDEX.md`
- **API 文档** → `docs/API_GUIDE.md`
- **前端文档** → `frontend/README.md`

#### 💻 代码
- **认证逻辑** → `auth_service/core/security.py`
- **支付逻辑** → `payment_service/providers/`
- **数据模型** → `*/models/`
- **API 路由** → `*/api/`

#### ⚙️ 配置
- **环境变量** → `.env.example`
- **数据库** → `alembic/`
- **Docker** → `docker/docker-compose.yml`

#### 🎨 前端
- **页面** → `frontend/src/pages/`
- **组件** → `frontend/src/components/`
- **API 调用** → `frontend/src/services/`
- **类型定义** → `frontend/src/types/`

## ✅ 文件组织检查清单

- [x] 删除根目录不必要的文件（`__init__.py`）
- [x] 文档统一放在 `docs/` 目录
- [x] 创建文档索引 `docs/INDEX.md`
- [x] 前端项目独立且结构清晰
- [x] README.md 提供清晰的导航
- [x] 每个服务遵循统一的结构

## 📝 维护建议

### 添加新功能时
1. 确定功能属于哪个服务
2. 在对应服务目录下创建文件
3. 遵循现有的目录结构

### 添加新文档时
1. 在 `docs/` 目录创建文档
2. 更新 `docs/INDEX.md` 添加链接
3. 在 README.md 中引用（如果需要）

### 前端开发时
1. 组件放在 `components/` 对应子目录
2. 页面放在 `pages/`
3. API 调用放在 `services/`
4. 类型定义放在 `types/`

---

**提示**: 保持这个结构，项目会更易于维护和扩展！
