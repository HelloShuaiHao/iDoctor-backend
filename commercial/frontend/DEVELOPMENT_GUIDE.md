# iDoctor 商业化前端 - 开发指南

> 完整的开发文档和API集成指南

---

## 📋 目录

- [最新更新](#最新更新)
- [快速开始](#快速开始)
- [项目架构](#项目架构)
- [API集成说明](#api集成说明)
- [页面功能清单](#页面功能清单)
- [开发规范](#开发规范)
- [常见问题](#常见问题)

---

## 🎉 最新更新

### v1.1.0 - 2025-10-18

#### ✅ 完成的功能

1. **配额管理系统集成**
   - ✅ 移除mock数据，连接真实后端API (`/admin/quotas`)
   - ✅ 实现配额摘要、使用历史、趋势统计的完整展示
   - ✅ 数据格式转换和错误处理优化

2. **支付记录页面**
   - ✅ 创建完整的支付历史展示页面
   - ✅ 支持交易明细、状态跟踪、发票下载
   - ✅ 统计卡片：总支出、交易数、成功率

3. **API配置优化**
   - ✅ 新增 `idoctorAPI` 实例（连接主应用4200端口）
   - ✅ 统一Token管理和自动刷新机制
   - ✅ 完善环境变量配置

4. **UI/UX改进**
   - ✅ Dashboard中移除"开发中"标签
   - ✅ 所有功能卡片可点击跳转
   - ✅ 响应式设计优化

---

## 🚀 快速开始

### 前置条件

确保以下服务已启动：

```bash
# 1. 认证服务 (端口 9001)
cd commercial/auth_service
python app.py

# 2. 支付服务 (端口 9002)
cd commercial/payment_service
python app.py

# 3. iDoctor 主应用 (端口 4200)
cd iDoctor-backend
uvicorn app:app --host 0.0.0.0 --port 4200 --workers 1
```

### 启动前端

```bash
cd commercial/frontend

# 1. 安装依赖（首次运行）
npm install

# 2. 启动开发服务器
npm run dev

# 3. 访问应用
# http://localhost:3000
```

---

## 🏗️ 项目架构

### 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **UI库**: shadcn/ui + Tailwind CSS
- **路由**: React Router v6
- **HTTP客户端**: Axios
- **状态管理**: React Context + Hooks

### 目录结构

```
frontend/
├── src/
│   ├── components/          # UI组件
│   │   ├── ui/              # shadcn/ui 基础组件
│   │   ├── layout/          # 布局组件
│   │   └── subscription/    # 订阅相关组件
│   ├── pages/               # 页面组件
│   │   ├── HomePage.tsx
│   │   ├── AuthPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── SubscriptionPage.tsx
│   │   ├── MySubscriptionPage.tsx
│   │   ├── PaymentPage.tsx
│   │   ├── PaymentHistoryPage.tsx  # ✨ 新增
│   │   ├── ApiKeysPage.tsx
│   │   └── UsageStatsPage.tsx
│   ├── services/            # API服务
│   │   ├── api.ts           # Axios实例配置
│   │   ├── authService.ts
│   │   ├── paymentService.ts
│   │   ├── quotaService.ts  # ✨ 已优化
│   │   └── subscriptionService.ts
│   ├── context/             # React Context
│   │   └── AuthContext.tsx
│   ├── hooks/               # 自定义Hooks
│   │   ├── useAuth.ts
│   │   ├── usePayment.ts
│   │   └── useTheme.ts
│   ├── types/               # TypeScript类型定义
│   │   ├── auth.ts
│   │   ├── payment.ts
│   │   ├── quota.ts
│   │   └── subscription.ts
│   └── utils/               # 工具函数
│       ├── constants.ts
│       └── storage.ts
├── .env.development         # 开发环境配置
├── .env.example             # 环境变量示例
└── package.json
```

---

## 🔌 API集成说明

### API实例配置

项目中创建了三个独立的Axios实例：

```typescript
// src/services/api.ts

// 1. 认证服务API (端口 9001)
export const authAPI = axios.create({
  baseURL: 'http://localhost:9001',
});

// 2. 支付服务API (端口 9002)
export const paymentAPI = axios.create({
  baseURL: 'http://localhost:9002',
});

// 3. iDoctor主应用API (端口 4200) ✨ 新增
export const idoctorAPI = axios.create({
  baseURL: 'http://localhost:4200',
  timeout: 30000, // 处理请求可能较慢
});
```

### Token管理

所有API实例都配置了：
- **请求拦截器**: 自动添加 `Authorization: Bearer <token>`
- **响应拦截器**: Token过期时自动刷新并重试请求
- **统一错误处理**: 401错误跳转登录页

### 配额API集成

#### 端点映射

| 前端方法 | 后端端点 | 说明 |
|---------|---------|------|
| `getQuotaSummary()` | `GET /admin/quotas/users/me` | 获取当前用户配额摘要 |
| `getQuotaUsageHistory()` | `GET /admin/quotas/usage-logs` | 获取配额使用历史 |
| `getUsageTrend()` | `GET /admin/quotas/statistics/{type}` | 获取使用趋势统计 |
| `getQuotaLimits()` | `GET /admin/quotas/users/me` | 获取配额限制 |

#### 数据格式转换

后端返回的数据格式与前端TypeScript类型定义不同，`quotaService.ts`中已实现自动转换：

```typescript
// 后端格式 → 前端格式
{
  type_key: "api_calls_full_process",  → quota_type: { id, name, ... }
  limit: 10,                           → limit: 10
  used: 5,                             → used: 5
  usage_percent: 50.0                  → percentage: 50.0
}
```

---

## 📱 页面功能清单

### 1. 主页 (HomePage)
- [x] 产品介绍
- [x] 特性展示
- [x] CTA按钮跳转

### 2. 认证页面 (AuthPage)
- [x] 用户注册
- [x] 用户登录
- [x] 表单验证
- [x] Token存储

### 3. 控制台 (DashboardPage)
- [x] 用户信息展示
- [x] 快速导航卡片
  - [x] 使用统计 → `/usage-stats`
  - [x] API密钥 → `/api-keys`
  - [x] 订阅管理 → `/my-subscription`
  - [x] 支付记录 → `/payment-history` ✨
- [x] 快速操作区域

### 4. 订阅计划 (SubscriptionPage)
- [x] 计划列表展示
- [x] 网格视图/对比视图切换
- [x] 价格和配额展示
- [x] 选择计划跳转支付

### 5. 我的订阅 (MySubscriptionPage)
- [x] 当前订阅状态
- [x] 配额使用进度
- [x] 订阅详情
- [x] 升级/取消操作

### 6. 支付页面 (PaymentPage)
- [x] 支付方式选择
- [x] 订单信息展示
- [x] 支付宝跳转
- [x] 微信二维码支付
- [x] 支付状态轮询

### 7. 支付记录 (PaymentHistoryPage) ✨ 新增
- [x] 交易记录列表
- [x] 状态筛选和展示
- [x] 统计卡片（总支出、交易数、成功率）
- [x] 发票下载（待后端实现）
- [ ] 分页加载
- [ ] 日期筛选

### 8. API密钥 (ApiKeysPage)
- [x] 密钥列表展示
- [x] 创建新密钥
- [x] 密钥复制
- [x] 密钥停用/删除
- [x] 过期状态提示

### 9. 使用统计 (UsageStatsPage)
- [x] 配额摘要展示
- [x] 使用进度条
- [x] 时间窗口标签
- [x] 刷新数据
- [ ] 使用趋势图表（待实现）

---

## 💻 开发规范

### 代码风格

- 使用TypeScript严格模式
- 使用函数组件 + Hooks
- Props接口定义使用`FC<Props>`
- 组件按功能分目录

### API调用规范

```typescript
// ✅ 推荐
const loadData = async () => {
  try {
    setLoading(true);
    setError(null);
    const data = await someService.getData();
    setData(data);
  } catch (err: any) {
    console.error('Failed to load data:', err);
    setError('加载失败');
  } finally {
    setLoading(false);
  }
};

// ❌ 不推荐
someService.getData().then(data => {
  setData(data);
});
```

### 组件命名

- 页面组件: `{Name}Page.tsx`
- UI组件: `{name}.tsx`
- 布局组件: `{Name}Layout.tsx`
- 服务: `{name}Service.ts`
- Hooks: `use{Name}.ts`

---

## 🐛 常见问题

### Q1: 端口3000被占用

```bash
# 查找并杀死占用进程
lsof -ti:3000 | xargs kill -9

# 或使用其他端口
npm run dev -- --port 3001
```

### Q2: API调用401错误

**原因**: Token过期或未登录

**解决**:
1. 检查localStorage中是否有`access_token`
2. 尝试重新登录
3. 检查后端认证服务是否正常

### Q3: 配额数据显示为空

**检查清单**:
1. ✅ iDoctor主应用(4200端口)是否启动
2. ✅ 是否启用了认证和配额中间件 (`ENABLE_AUTH=true`, `ENABLE_QUOTA=true`)
3. ✅ 用户是否已登录并有有效Token
4. ✅ 检查浏览器控制台Network标签查看API响应

### Q4: 支付页面跳转失败

**原因**: 支付服务未启动或订单创建失败

**解决**:
```bash
# 检查支付服务状态
curl http://localhost:9002/health

# 查看支付服务日志
cd commercial/payment_service
tail -f logs/payment.log
```

---

## 📚 相关文档

- [后端API文档](../docs/API_GUIDE.md)
- [配额系统文档](../docs/ACCESS_CONTROL_USAGE.md)
- [快速开始指南](./QUICK_START.md)
- [项目状态](../docs/PROJECT_STATUS.md)

---

## 🔄 更新日志

### v1.1.0 (2025-10-18)
- ✅ 新增idoctorAPI实例
- ✅ quotaService移除mock数据
- ✅ 新增PaymentHistoryPage
- ✅ 优化Dashboard导航

### v1.0.0 (2024-10-17)
- ✅ 项目初始化
- ✅ 认证流程实现
- ✅ 订阅计划展示
- ✅ 支付流程实现

---

**快速开始**: `npm run dev` → http://localhost:3000 🚀
