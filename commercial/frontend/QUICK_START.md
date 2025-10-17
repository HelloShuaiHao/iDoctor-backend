# 前端快速开始指南

> iDoctor 商业化平台 - 前端测试应用

---

## 🚀 快速启动

### 前置条件

确保后端服务已启动：

```bash
cd ../docker
docker compose ps
# 应该看到 auth_service 和 payment_service 运行中
```

### 启动前端

```bash
# 1. 安装依赖（首次运行）
npm install

# 2. 启动开发服务器
npm run dev

# 服务器将在 http://localhost:3000 启动
```

---

## 🧪 功能测试指南

### 1. 订阅计划展示 ✅

**测试步骤**:
1. 访问 http://localhost:3000
2. 点击导航栏的"订阅计划"
3. 查看三个订阅计划卡片（免费版、专业版、企业版）
4. 点击右上角切换"网格视图"和"对比视图"
5. 测试"选择计划"按钮

**预期结果**:
- ✅ 显示 3 个订阅计划
- ✅ 价格和配额信息正确显示
- ✅ "专业版"显示"最受欢迎"徽章
- ✅ 响应式布局在移动端正常

### 2. 用户认证流程 ✅

**测试步骤**:
1. 点击"注册"
2. 填写邮箱、用户名、密码
3. 提交注册
4. 自动登录后跳转到控制台

**预期结果**:
- ✅ 注册成功
- ✅ 自动登录
- ✅ 导航栏显示用户名

### 3. 选择订阅计划

**测试步骤**:
1. 在订阅计划页面点击"选择计划"
2. 如果未登录，将跳转到登录页
3. 登录后，将跳转到支付页面（开发中）

**预期结果**:
- ✅ 未登录用户被引导登录
- ✅ 登录用户跳转到支付页面

---

## 📁 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # shadcn/ui 基础组件
│   │   └── subscription/    # 订阅相关组件 ✨
│   │       ├── PlanCard.tsx
│   │       ├── PlanList.tsx
│   │       └── PlanComparison.tsx
│   ├── pages/
│   │   ├── HomePage.tsx
│   │   ├── AuthPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── SubscriptionPage.tsx  # 订阅页面 ✨
│   │   └── PaymentPage.tsx
│   ├── services/
│   │   ├── api.ts               # Axios 配置
│   │   ├── authService.ts
│   │   ├── paymentService.ts
│   │   └── subscriptionService.ts
│   ├── context/
│   │   └── AuthContext.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── usePayment.ts
│   └── types/
│       ├── auth.ts
│       ├── payment.ts
│       └── subscription.ts
└── docs/
    └── FRONTEND_STATUS.md       # 开发进度文档
```

---

## 🛠️ 开发命令

```bash
# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview

# TypeScript 类型检查
npx tsc --noEmit

# ESLint 检查
npm run lint
```

---

## 🔗 API 端点

### 认证服务 (端口 9001)
- Swagger 文档: http://localhost:9001/docs
- 健康检查: http://localhost:9001/health

### 支付服务 (端口 9002)
- Swagger 文档: http://localhost:9002/docs
- 订阅计划列表: http://localhost:9002/plans/
- 健康检查: http://localhost:9002/health

---

## ✅ 已完成功能

### Phase 1: 基础框架 ✅
- React 18 + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- React Router 路由
- Axios API 客户端
- 认证上下文 (AuthContext)

### Phase 2: 订阅计划展示 ✅
- 订阅计划列表展示
- 网格视图和对比视图切换
- 计划选择和支付跳转
- 响应式设计
- API 对接完成

---

## 🚧 开发中功能

### Phase 3: 支付功能
- 支付方式选择器
- 支付宝跳转
- 微信二维码支付
- 支付状态轮询
- 退款申请

---

## 🐛 故障排查

### 问题 1: 端口 3000 被占用
```bash
# 查找占用端口的进程
lsof -ti:3000

# 杀死进程
lsof -ti:3000 | xargs kill -9

# 或使用其他端口
npm run dev -- --port 3001
```

### 问题 2: 后端服务未启动
```bash
cd ../docker
docker compose up -d

# 检查服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 问题 3: API 调用失败
- 检查后端服务是否运行
- 检查 `.env` 配置
- 查看浏览器控制台错误
- 检查网络请求（Network 标签）

---

## 📞 技术支持

- **后端 API 文档**: `../docs/API_GUIDE.md`
- **项目进度**: `../docs/PROJECT_STATUS.md`
- **前端开发状态**: `./docs/FRONTEND_STATUS.md`
- **前端架构规划**: `../docs/FRONTEND_STRUCTURE.md`

---

## 💡 开发提示

### 添加新页面
1. 在 `src/pages/` 创建页面组件
2. 在 `src/main.tsx` 添加路由
3. 在导航栏添加链接

### 添加新 API 服务
1. 在 `src/types/` 定义类型
2. 在 `src/services/` 创建服务模块
3. 使用 `authAPI` 或 `paymentAPI` 实例

### 添加新组件
1. 基础 UI 组件放在 `src/components/ui/`
2. 业务组件按功能分目录
3. 使用 TypeScript 定义 Props 接口

---

**快速开始**: `npm run dev` 然后访问 http://localhost:3000 🚀
