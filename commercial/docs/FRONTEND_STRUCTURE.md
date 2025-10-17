# 前端项目结构规划

> **版本**: v1.0.0
> **创建时间**: 2025-10-17
> **目的**: 为 iDoctor 商业化模块创建测试前端

---

## 📁 项目位置

**推荐方案**: 在 `commercial/` 目录下创建 `frontend/` 文件夹

```
iDoctor-backend/
└── commercial/              # 商业化模块
    ├── auth_service/        # 认证服务 (端口 9001)
    ├── payment_service/     # 支付服务 (端口 9002)
    ├── quota_service/       # 配额服务
    ├── frontend/            # 🆕 前端测试界面
    ├── shared/              # 共享模块
    ├── docker/              # Docker 配置
    ├── docs/                # 文档
    ├── scripts/             # 脚本
    └── alembic/             # 数据库迁移
```

**选择理由**:
1. ✅ 前端和商业化后端模块紧密关联，便于统一管理
2. ✅ 支持独立部署或集成部署
3. ✅ 符合微服务架构原则
4. ✅ Docker Compose 可以统一编排前后端服务

---

## 🏗️ 前端项目完整结构

### 技术栈
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **UI 组件库**: Ant Design / Tailwind CSS + shadcn/ui
- **状态管理**: React Context / Zustand (可选)
- **HTTP 客户端**: Axios
- **路由**: React Router v6

### 目录结构

```
commercial/frontend/
│
├── public/                          # 静态资源
│   ├── index.html                   # HTML 模板
│   ├── favicon.ico                  # 网站图标
│   └── assets/                      # 公共图片/字体
│       ├── logo.png
│       └── images/
│
├── src/                             # 源代码目录
│   │
│   ├── components/                  # React 组件
│   │   ├── common/                  # 通用组件
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Loading.tsx
│   │   │
│   │   ├── auth/                    # 认证相关组件
│   │   │   ├── LoginForm.tsx        # 登录表单
│   │   │   ├── RegisterForm.tsx     # 注册表单
│   │   │   ├── UserProfile.tsx      # 用户信息
│   │   │   └── ApiKeyManager.tsx    # API 密钥管理
│   │   │
│   │   ├── payment/                 # 支付相关组件
│   │   │   ├── PaymentForm.tsx      # 支付表单
│   │   │   ├── QRCodeDisplay.tsx    # 二维码展示
│   │   │   ├── PaymentStatus.tsx    # 支付状态查询
│   │   │   └── RefundForm.tsx       # 退款申请
│   │   │
│   │   └── subscription/            # 订阅相关组件
│   │       ├── PlanList.tsx         # 订阅计划列表
│   │       ├── PlanCard.tsx         # 计划卡片
│   │       ├── SubscriptionStatus.tsx # 订阅状态
│   │       └── PlanComparison.tsx   # 计划对比
│   │
│   ├── pages/                       # 页面组件
│   │   ├── HomePage.tsx             # 首页
│   │   ├── AuthPage.tsx             # 认证页面（登录/注册）
│   │   ├── DashboardPage.tsx        # 用户仪表板
│   │   ├── SubscriptionPage.tsx     # 订阅管理页面
│   │   ├── PaymentPage.tsx          # 支付页面
│   │   └── NotFoundPage.tsx         # 404 页面
│   │
│   ├── services/                    # API 服务层
│   │   ├── api.ts                   # Axios 实例配置
│   │   ├── authService.ts           # 认证 API 调用
│   │   ├── paymentService.ts        # 支付 API 调用
│   │   ├── subscriptionService.ts   # 订阅 API 调用
│   │   └── apiKeyService.ts         # API Key 管理
│   │
│   ├── hooks/                       # 自定义 React Hooks
│   │   ├── useAuth.ts               # 认证状态管理
│   │   ├── usePayment.ts            # 支付流程管理
│   │   └── useSubscription.ts       # 订阅状态管理
│   │
│   ├── context/                     # React Context
│   │   ├── AuthContext.tsx          # 认证上下文
│   │   └── PaymentContext.tsx       # 支付上下文
│   │
│   ├── utils/                       # 工具函数
│   │   ├── storage.ts               # LocalStorage 封装
│   │   ├── validators.ts            # 表单验证
│   │   ├── formatters.ts            # 数据格式化
│   │   └── constants.ts             # 常量定义
│   │
│   ├── types/                       # TypeScript 类型定义
│   │   ├── auth.ts                  # 认证相关类型
│   │   ├── payment.ts               # 支付相关类型
│   │   ├── subscription.ts          # 订阅相关类型
│   │   └── api.ts                   # API 响应类型
│   │
│   ├── styles/                      # 样式文件
│   │   ├── index.css                # 全局样式
│   │   ├── variables.css            # CSS 变量
│   │   └── components/              # 组件样式（如使用 CSS Modules）
│   │
│   ├── App.tsx                      # 主应用组件
│   ├── main.tsx                     # 应用入口
│   └── router.tsx                   # 路由配置
│
├── docs/                            # 前端文档
│   ├── README.md                    # 前端使用说明
│   ├── API_INTEGRATION.md           # 后端 API 集成指南
│   ├── DEVELOPMENT.md               # 开发指南
│   └── DEPLOYMENT.md                # 部署指南
│
├── tests/                           # 测试文件
│   ├── unit/                        # 单元测试
│   ├── integration/                 # 集成测试
│   └── setup.ts                     # 测试配置
│
├── .env.example                     # 环境变量示例
├── .env.development                 # 开发环境变量
├── .env.production                  # 生产环境变量
├── .gitignore                       # Git 忽略配置
├── package.json                     # 依赖管理
├── tsconfig.json                    # TypeScript 配置
├── vite.config.ts                   # Vite 配置
├── tailwind.config.js               # Tailwind 配置（如使用）
└── README.md                        # 项目说明
```

---

## 📝 核心文件内容规划

### 1. 环境变量 (`.env.example`)

```env
# API 服务端点
VITE_AUTH_API_URL=http://localhost:9001
VITE_PAYMENT_API_URL=http://localhost:9002

# 应用配置
VITE_APP_NAME=iDoctor 商业化测试平台
VITE_APP_VERSION=1.0.0

# 开发配置
VITE_DEV_MODE=true
VITE_MOCK_PAYMENT=true
```

### 2. 主要功能模块

#### 认证模块 (Auth)
- **登录/注册表单**: 用户名/邮箱登录，密码强度验证
- **Token 管理**: LocalStorage 存储，自动刷新
- **用户信息展示**: 个人资料、账户状态
- **API Key 管理**: 创建、查看、撤销 API 密钥

#### 支付模块 (Payment)
- **订阅计划展示**: 卡片式展示，支持对比
- **支付方式选择**: 支付宝/微信支付
- **支付流程**:
  - 支付宝：显示支付链接或跳转
  - 微信：显示二维码扫码支付
- **支付状态轮询**: 自动查询支付结果
- **退款申请**: 输入退款金额和理由

#### 订阅管理模块 (Subscription)
- **计划列表**: 获取所有可用订阅计划
- **订阅状态**: 查看当前订阅、到期时间
- **升级/降级**: 订阅计划变更

---

## 🎨 UI/UX 设计原则

### 页面布局
1. **顶部导航栏**: Logo + 主导航 + 用户菜单
2. **侧边栏**: 功能菜单（可选，仪表板页面）
3. **主内容区**: 响应式布局，移动端友好
4. **底部**: 版权信息、帮助链接

### 核心页面流程

#### 首页 (HomePage)
```
┌─────────────────────────────────────┐
│  [Logo]  首页  订阅  API  [登录]    │
├─────────────────────────────────────┤
│                                     │
│      iDoctor 商业化平台             │
│      AI 医疗影像分析服务             │
│                                     │
│      [查看订阅计划]  [立即注册]      │
│                                     │
├─────────────────────────────────────┤
│  功能特性 | 价格对比 | 使用案例      │
└─────────────────────────────────────┘
```

#### 认证页面 (AuthPage)
```
┌─────────────────────────────────────┐
│           用户登录/注册              │
├─────────────────────────────────────┤
│  [登录] [注册]  <-- Tab 切换         │
│                                     │
│  邮箱/用户名: [____________]         │
│  密码:       [____________]         │
│                                     │
│  [ 登录 ]  忘记密码?                │
│                                     │
│  或使用 API Key 认证                │
└─────────────────────────────────────┘
```

#### 订阅计划页面 (SubscriptionPage)
```
┌─────────────────────────────────────┐
│           选择订阅计划               │
├─────────────────────────────────────┤
│  ┌─────┐  ┌─────┐  ┌─────┐          │
│  │基础版│  │专业版│  │企业版│          │
│  │¥99/月│  │¥299/月│ │¥999/月│       │
│  │     │  │     │  │     │          │
│  │[选择]│  │[选择]│  │[选择]│          │
│  └─────┘  └─────┘  └─────┘          │
│                                     │
│  功能对比表格...                     │
└─────────────────────────────────────┘
```

#### 支付页面 (PaymentPage)
```
┌─────────────────────────────────────┐
│            完成支付                  │
├─────────────────────────────────────┤
│  订单信息:                           │
│  - 订阅计划: 专业版                  │
│  - 金额: ¥299.00                    │
│                                     │
│  支付方式:                           │
│  ( ) 支付宝  ( ) 微信支付            │
│                                     │
│  [微信支付二维码]                    │
│   或                                │
│  [支付宝跳转链接]                    │
│                                     │
│  支付状态: 等待支付...               │
└─────────────────────────────────────┘
```

---

## 🔧 技术实现要点

### API 调用封装

```typescript
// src/services/api.ts
import axios from 'axios';

const authAPI = axios.create({
  baseURL: import.meta.env.VITE_AUTH_API_URL,
  timeout: 10000,
});

// 请求拦截器：添加 Token
authAPI.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：处理 Token 过期
authAPI.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token 过期，尝试刷新
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        // 刷新 Token 逻辑
      } else {
        // 跳转登录页
      }
    }
    return Promise.reject(error);
  }
);
```

### 认证状态管理

```typescript
// src/hooks/useAuth.ts
export const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const login = async (credentials) => {
    const response = await authService.login(credentials);
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);
    setUser(response.user);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return { user, login, logout, loading };
};
```

### 支付流程处理

```typescript
// src/hooks/usePayment.ts
export const usePayment = () => {
  const [paymentStatus, setPaymentStatus] = useState('idle');

  const createPayment = async (paymentData) => {
    const response = await paymentService.createPayment(paymentData);

    if (response.payment_method === 'wechat') {
      // 显示微信二维码
      displayQRCode(response.qr_code);
    } else if (response.payment_method === 'alipay') {
      // 跳转支付宝
      window.location.href = response.payment_url;
    }

    // 开始轮询支付状态
    pollPaymentStatus(response.id);
  };

  const pollPaymentStatus = async (paymentId) => {
    const interval = setInterval(async () => {
      const status = await paymentService.getPaymentStatus(paymentId);
      setPaymentStatus(status.status);

      if (status.status === 'completed' || status.status === 'failed') {
        clearInterval(interval);
      }
    }, 2000); // 每2秒查询一次
  };

  return { paymentStatus, createPayment };
};
```

---

## 📦 依赖包列表

### 核心依赖 (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.2",
    "antd": "^5.12.0",
    "@ant-design/icons": "^5.2.6",
    "qrcode.react": "^3.1.0",
    "zustand": "^4.4.7"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8",
    "typescript": "^5.3.3",
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "tailwindcss": "^3.3.6",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}
```

---

## 🚀 开发流程

### 1. 初始化项目
```bash
cd commercial
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### 2. 安装额外依赖
```bash
npm install axios react-router-dom antd @ant-design/icons qrcode.react
npm install -D tailwindcss postcss autoprefixer
```

### 3. 配置环境变量
```bash
cp .env.example .env.development
```

### 4. 启动开发服务器
```bash
npm run dev
```

### 5. 构建生产版本
```bash
npm run build
```

---

## 🐳 Docker 集成

### Dockerfile (frontend/Dockerfile)

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx 配置 (frontend/nginx.conf)

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/auth {
        proxy_pass http://auth-service:9001;
    }

    location /api/payment {
        proxy_pass http://payment-service:9002;
    }
}
```

### 更新 Docker Compose (commercial/docker/docker-compose.yml)

```yaml
services:
  # ... 现有服务 ...

  frontend:
    build: ../frontend
    ports:
      - "3000:80"
    environment:
      - VITE_AUTH_API_URL=http://localhost:9001
      - VITE_PAYMENT_API_URL=http://localhost:9002
    depends_on:
      - auth-service
      - payment-service
```

---

## 📊 开发优先级

### Phase 1: 基础框架 (1-2天)
- [x] 项目初始化和依赖安装
- [x] 路由配置
- [x] API 服务封装
- [x] 基础布局组件

### Phase 2: 认证模块 (2-3天)
- [ ] 登录/注册表单
- [ ] Token 管理和自动刷新
- [ ] 用户信息展示
- [ ] API Key 管理界面

### Phase 3: 订阅&支付模块 (3-4天)
- [ ] 订阅计划列表和对比
- [ ] 支付表单和方式选择
- [ ] 二维码/链接展示
- [ ] 支付状态轮询
- [ ] 退款功能

### Phase 4: 优化&测试 (1-2天)
- [ ] 响应式布局优化
- [ ] 错误处理和用户提示
- [ ] 集成测试
- [ ] 文档完善

---

## ✅ 验收标准

### 功能完整性
- ✅ 用户可以注册/登录/登出
- ✅ 用户可以查看和管理 API Key
- ✅ 用户可以浏览订阅计划
- ✅ 用户可以完成支付流程（支付宝/微信）
- ✅ 用户可以查看支付状态
- ✅ 用户可以申请退款

### 用户体验
- ✅ 界面美观，响应式设计
- ✅ 加载状态明确
- ✅ 错误提示友好
- ✅ 操作流程顺畅

### 代码质量
- ✅ TypeScript 类型完整
- ✅ 组件可复用性高
- ✅ API 调用统一封装
- ✅ 错误处理完善

---

## 📞 后续计划

1. **集成主应用**: 将商业化模块集成到 iDoctor 主应用
2. **用户仪表板**: 显示 API 使用量、配额统计
3. **管理后台**: 管理员管理订阅计划、用户
4. **数据可视化**: 使用图表展示使用趋势

---

**下一步**: 根据此规划创建前端项目，是否开始初始化？
