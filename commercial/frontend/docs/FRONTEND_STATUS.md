# 前端开发状态与规划

> iDoctor 商业化平台 - 完整前端开发计划
>
> **目标**: 搭建完整的前端应用，连接所有后台功能

---

## 📊 当前状态概览

### ✅ 已完成

#### Phase 1 - 基础框架

#### 1. 项目基础架构
- [x] React 18 + TypeScript + Vite 项目初始化
- [x] Tailwind CSS v3 + shadcn/ui 组件库
- [x] React Router v6 路由系统
- [x] Axios HTTP 客户端配置
- [x] 环境变量配置

#### 2. 基础组件库
- [x] Button - 按钮组件
- [x] Input - 输入框组件
- [x] Card - 卡片组件
- [x] Tabs - 选项卡组件
- [x] Label - 标签组件
- [x] Alert - 警告提示组件

#### 3. API 服务层
- [x] Axios 实例配置（认证 + 支付）
- [x] 请求/响应拦截器
- [x] Token 自动刷新机制
- [x] authService - 认证服务 API
- [x] paymentService - 支付服务 API
- [x] subscriptionService - 订阅服务 API

#### 4. 状态管理
- [x] AuthContext - 认证上下文
- [x] useAuth Hook - 认证状态管理
- [x] usePayment Hook - 支付流程管理

#### 5. 基础页面
- [x] HomePage - 首页
- [x] AuthPage - 登录/注册页面
- [x] DashboardPage - 用户控制台（基础版）
- [x] SubscriptionPage - 订阅页面（占位）
- [x] PaymentPage - 支付页面（占位）

#### 6. TypeScript 类型系统
- [x] Auth 类型定义
- [x] Payment 类型定义
- [x] Subscription 类型定义

#### Phase 2 - 订阅计划展示 ✨
- [x] PlanCard - 订阅计划卡片组件
- [x] PlanList - 计划列表组件（支持网格/列表布局）
- [x] PlanComparison - 计划对比表格组件
- [x] SubscriptionPage - 完整的订阅页面
- [x] 视图切换功能（网格 vs 对比）
- [x] API 对接 (GET /plans/)
- [x] 后端测试数据初始化（3个订阅计划）

---

## 🚧 待开发功能规划

### ✅ Phase 2: 订阅计划功能 【已完成】

#### 2.1 订阅计划展示 ✅
**组件清单**:
- [x] `PlanList.tsx` - 订阅计划列表容器
- [x] `PlanCard.tsx` - 单个计划卡片
- [x] `PlanComparison.tsx` - 计划对比表格
- [x] `SubscriptionPage.tsx` - 订阅页面完善

**已实现功能**:
- ✅ 获取所有订阅计划 (API: GET /plans/)
- ✅ 卡片式展示（基础版/专业版/企业版）
- ✅ 显示价格、周期、配额信息
- ✅ 响应式布局（移动端适配）
- ✅ 视图切换（网格视图 vs 对比视图）
- ✅ 加载状态和错误处理
- ✅ 计划选择和支付跳转
- ✅ 自动识别"最受欢迎"计划
- ✅ FAQ 常见问题展示

**技术实现**:
```typescript
// ✅ 订阅服务 API 对接
const plans = await subscriptionService.getPlans();

// ✅ 计划卡片展示（包含特性解析）
<PlanCard
  plan={plan}
  isCurrentPlan={currentPlanId === plan.id}
  isPopular={plan.id === popularPlanId}
  onSelect={() => handleSelectPlan(plan)}
/>

// ✅ 视图切换
{viewMode === 'grid' ? (
  <PlanList onSelectPlan={handleSelectPlan} />
) : (
  <PlanComparison onSelectPlan={handleSelectPlan} />
)}
```

**测试状态**:
- ✅ TypeScript 编译无错误
- ✅ 后端 API 已初始化测试数据（3个订阅计划）
- ✅ 前端组件渲染正常

#### 2.2 订阅管理
**组件清单**:
- [ ] `SubscriptionStatus.tsx` - 当前订阅状态
- [ ] `SubscriptionPage.tsx` (完善) - 订阅管理页面

**功能需求**:
- 当前订阅信息展示
- 到期时间提醒
- 自动续费开关
- 升级/降级入口
- 订阅历史记录

#### 2.3 订阅购买流程
**流程**: 选择计划 → 选择支付方式 → 完成支付 → 激活订阅

**组件需求**:
- [ ] 订阅确认对话框
- [ ] 购买成功反馈页面

**后端 API 对接**:
```typescript
GET  /plans/                    // 获取订阅计划
GET  /subscriptions/            // 获取用户订阅
POST /subscriptions/            // 创建订阅（购买）
```

---

### Phase 3: 支付功能完善 💳 【优先级：高】

#### 3.1 支付方式选择
**组件清单**:
- [ ] `PaymentMethodSelector.tsx` - 支付方式选择器

**功能需求**:
- 支付宝选项（显示图标）
- 微信支付选项（显示图标）
- 单选按钮组
- 方式切换动画

#### 3.2 支付流程组件
**组件清单**:
- [ ] `PaymentForm.tsx` - 支付表单
- [ ] `QRCodeDisplay.tsx` - 二维码展示（微信）
- [ ] `PaymentStatus.tsx` - 支付状态查询

**功能需求**:
```typescript
// PaymentForm
- 订单信息摘要
- 支付方式选择
- 金额确认
- 支付按钮

// QRCodeDisplay  
- 微信支付二维码展示（使用 qrcode.react）
- 支付状态实时更新
- 支付成功/失败提示

// PaymentStatus
- 支付状态轮询（每2秒）
- 进度指示器
- 支付成功/失败页面
```

#### 3.3 支付页面完善
**重构 PaymentPage.tsx**:
- [ ] 订单创建流程
- [ ] 支付方式展示
- [ ] 支付宝：跳转链接处理
- [ ] 微信：二维码扫码支付
- [ ] 支付状态轮询
- [ ] 支付完成回调处理

**支付流程示意**:
```
用户选择订阅计划
    ↓
进入支付页面
    ↓
选择支付方式（支付宝/微信）
    ↓
创建支付订单 (POST /payments/)
    ↓
展示支付界面
├─ 支付宝：跳转到 payment_url
└─ 微信：显示 qr_code 二维码
    ↓
轮询支付状态 (GET /payments/{id})
    ↓
支付完成 → 激活订阅
```

#### 3.4 退款功能
**组件清单**:
- [ ] `RefundForm.tsx` - 退款申请表单
- [ ] `RefundStatus.tsx` - 退款状态

**后端 API 对接**:
```typescript
POST /payments/                      // 创建支付订单
GET  /payments/{payment_id}          // 查询支付状态
POST /payments/{payment_id}/refund   // 申请退款
```

---

### Phase 4: API Key 管理 🔑 【优先级：中】

#### 4.1 API Key 列表
**组件清单**:
- [ ] `APIKeyList.tsx` - API Key 列表
- [ ] `APIKeyItem.tsx` - 单个 Key 项

**功能需求**:
- 显示所有 API Key
- Key 前缀展示（安全，只显示前8位）
- 创建时间、到期时间
- 状态标记（激活/停用）
- 操作按钮（复制/停用/删除）

#### 4.2 API Key 创建
**组件清单**:
- [ ] `CreateAPIKeyForm.tsx` - 创建表单
- [ ] `APIKeyDisplay.tsx` - 一次性显示完整 Key

**功能需求**:
- API Key 名称输入
- 到期时间选择（可选）
- 创建成功后显示完整 Key（仅一次）
- 复制 Key 功能
- 安全提示

#### 4.3 API Key 管理页面
**新增页面**:
- [ ] `APIKeyPage.tsx` - API Key 管理页面

**功能需求**:
- API Key 列表展示
- 创建新 Key 入口
- 停用/删除 Key
- 使用说明文档
- 使用示例代码

**后端 API 对接**:
```typescript
POST   /api-keys/                      // 创建 API Key
GET    /api-keys/                      // 获取列表
PATCH  /api-keys/{key_id}/deactivate   // 停用
DELETE /api-keys/{key_id}              // 删除
```

---

### Phase 5: 用户中心完善 👤 【优先级：中】

#### 5.1 用户信息管理
**组件清单**:
- [ ] `UserProfile.tsx` - 用户信息展示/编辑
- [ ] `AvatarUpload.tsx` - 头像上传（可选）

**功能需求**:
- 用户信息展示
- 个人信息编辑
- 邮箱修改
- 用户名修改

#### 5.2 账户设置
**组件清单**:
- [ ] `AccountSettings.tsx` - 账户设置
- [ ] `PasswordChange.tsx` - 密码修改

**功能需求**:
- 密码修改
- 账户安全设置
- 两步验证（可选）

#### 5.3 用户中心页面
**新增页面**:
- [ ] `ProfilePage.tsx` - 用户中心页面

**后端 API 对接**:
```typescript
GET /users/me     // 获取用户信息
PUT /users/me     // 更新用户信息
```

---

### Phase 6: 使用统计与监控 📊 【优先级：低】

#### 6.1 使用统计仪表板
**组件清单**:
- [ ] `UsageDashboard.tsx` - 统计仪表板
- [ ] `StatsCard.tsx` - 统计卡片
- [ ] `UsageChart.tsx` - 使用趋势图表

**功能需求**:
- API 调用次数统计
- 配额使用情况
- 使用趋势图表（使用 recharts）
- 剩余配额提醒

**图表库选择**:
- recharts (推荐) 或 chart.js

#### 6.2 使用记录
**组件清单**:
- [ ] `UsageHistory.tsx` - 使用记录列表

**功能需求**:
- 使用记录列表
- 时间范围筛选
- 按类型筛选
- 导出功能（CSV）

#### 6.3 配额警告
**组件清单**:
- [ ] `QuotaWarning.tsx` - 配额警告提示

**后端 API 对接** (需要后端开发):
```typescript
GET /quota/usage/stats    // 获取使用统计
GET /quota/usage/history  // 获取使用记录
```

---

### Phase 7: 支付历史与发票 🧾 【优先级：低】

#### 7.1 支付历史
**组件清单**:
- [ ] `PaymentHistory.tsx` - 支付历史列表
- [ ] `PaymentHistoryItem.tsx` - 历史项

**功能需求**:
- 支付记录列表
- 支付时间、金额、状态
- 支付方式标记
- 查看详情入口
- 分页功能

#### 7.2 支付详情
**组件清单**:
- [ ] `PaymentDetail.tsx` - 支付详情页

**功能需求**:
- 订单详细信息
- 支付流水号
- 退款记录（如有）

#### 7.3 发票管理（可选）
**组件清单**:
- [ ] `InvoiceList.tsx` - 发票列表
- [ ] `InvoiceRequest.tsx` - 申请发票

**后端 API 对接**:
```typescript
GET /payments/            // 获取支付历史

// 发票管理（待后端开发）
GET  /invoices/           
POST /invoices/
```

---

### Phase 8: 通知与消息系统 🔔 【优先级：低】

#### 8.1 通知中心
**组件清单**:
- [ ] `NotificationCenter.tsx` - 通知中心
- [ ] `NotificationItem.tsx` - 通知项

**功能需求**:
- 系统通知列表
- 未读消息提醒
- 消息标记已读
- 消息删除
- 通知分类

#### 8.2 消息类型
- 支付成功通知
- 订阅到期提醒
- 配额不足警告
- 系统维护通知

#### 8.3 实时通知（可选）
- [ ] WebSocket 集成
- [ ] 浏览器推送通知
- [ ] 邮件通知

**后端 API 对接** (需要后端开发):
```typescript
GET    /notifications/           // 获取通知列表
PATCH  /notifications/{id}/read  // 标记已读
DELETE /notifications/{id}       // 删除通知
```

---

## 🎨 通用组件开发

### 基础组件（高优先级）
- [ ] `Loading.tsx` - 全局加载指示器
- [ ] `Toast.tsx` - 全局提示通知
- [ ] `Modal.tsx` - 通用弹窗对话框
- [ ] `EmptyState.tsx` - 空状态展示

### 数据展示组件
- [ ] `Table.tsx` - 数据表格
- [ ] `Pagination.tsx` - 分页组件
- [ ] `Skeleton.tsx` - 骨架屏

### 图表组件（可选）
- [ ] `LineChart.tsx` - 折线图
- [ ] `BarChart.tsx` - 柱状图
- [ ] `PieChart.tsx` - 饼图

### 错误处理
- [ ] `ErrorBoundary.tsx` - 错误边界
- [ ] `ErrorPage.tsx` - 错误页面

---

## 📁 完整文件清单

### 新增组件文件

```
src/components/
│
├── subscription/                    # 订阅相关
│   ├── PlanList.tsx
│   ├── PlanCard.tsx
│   ├── PlanComparison.tsx
│   └── SubscriptionStatus.tsx
│
├── payment/                         # 支付相关
│   ├── PaymentForm.tsx
│   ├── PaymentMethodSelector.tsx
│   ├── QRCodeDisplay.tsx
│   ├── PaymentStatus.tsx
│   ├── RefundForm.tsx
│   ├── PaymentHistory.tsx
│   └── PaymentDetail.tsx
│
├── auth/                            # 认证相关
│   ├── UserProfile.tsx
│   ├── AccountSettings.tsx
│   ├── PasswordChange.tsx
│   ├── APIKeyList.tsx
│   ├── APIKeyItem.tsx
│   ├── CreateAPIKeyForm.tsx
│   └── APIKeyDisplay.tsx
│
├── dashboard/                       # 仪表板
│   ├── UsageDashboard.tsx
│   ├── UsageHistory.tsx
│   ├── QuotaWarning.tsx
│   ├── StatsCard.tsx
│   └── UsageChart.tsx
│
└── common/                          # 通用组件
    ├── Loading.tsx
    ├── Toast.tsx
    ├── Modal.tsx
    ├── EmptyState.tsx
    ├── ErrorBoundary.tsx
    ├── Table.tsx
    ├── Pagination.tsx
    └── Skeleton.tsx
```

### 新增页面文件

```
src/pages/
├── ProfilePage.tsx         # 用户中心
├── APIKeyPage.tsx          # API Key 管理
├── HistoryPage.tsx         # 历史记录
└── NotificationPage.tsx    # 通知中心
```

### 新增工具文件

```
src/utils/
├── format.ts               # 数据格式化
├── currency.ts             # 货币处理
├── date.ts                 # 日期处理
└── chart.ts                # 图表工具
```

### 新增 Hooks

```
src/hooks/
├── useSubscription.ts      # 订阅管理
├── useAPIKey.ts           # API Key 管理
├── useNotification.ts     # 通知管理
└── useUsageStats.ts       # 使用统计
```

---

## 🗓️ 开发时间线（4-6周）

### Week 1: 订阅功能
**目标**: 完成订阅计划展示和购买流程

- **Day 1-2**: 订阅计划展示组件
  - [ ] 创建 PlanList, PlanCard 组件
  - [ ] 对接 GET /plans/ API
  - [ ] 实现响应式布局

- **Day 3-4**: 订阅管理和状态
  - [ ] 创建 SubscriptionStatus 组件
  - [ ] 完善 SubscriptionPage 页面
  - [ ] 对接订阅 API

- **Day 5**: 订阅购买流程
  - [ ] 实现购买确认流程
  - [ ] 集成支付系统
  - [ ] 测试完整流程

---

### Week 2: 支付功能
**目标**: 完成完整的支付流程

- **Day 1-2**: 支付组件开发
  - [ ] PaymentForm 组件
  - [ ] PaymentMethodSelector 组件
  - [ ] QRCodeDisplay 组件（微信）

- **Day 3-4**: 支付流程实现
  - [ ] 支付宝跳转逻辑
  - [ ] 微信扫码支付
  - [ ] 支付状态轮询

- **Day 5**: 支付历史和退款
  - [ ] PaymentHistory 组件
  - [ ] RefundForm 组件
  - [ ] 测试支付流程

---

### Week 3: API Key 和用户中心
**目标**: 完成 API Key 管理和用户信息管理

- **Day 1-2**: API Key 管理
  - [ ] APIKeyList 组件
  - [ ] CreateAPIKeyForm 组件
  - [ ] APIKeyPage 页面

- **Day 3-4**: 用户中心
  - [ ] UserProfile 组件
  - [ ] AccountSettings 组件
  - [ ] ProfilePage 页面

- **Day 5**: 测试和优化
  - [ ] 功能测试
  - [ ] 用户体验优化

---

### Week 4: 通用组件和优化
**目标**: 完成通用组件和性能优化

- **Day 1-2**: 通用组件开发
  - [ ] Loading, Toast, Modal
  - [ ] Table, Pagination
  - [ ] ErrorBoundary

- **Day 3-4**: 性能优化
  - [ ] 代码分割
  - [ ] 懒加载
  - [ ] Bundle 优化

- **Day 5**: 最终测试
  - [ ] E2E 测试
  - [ ] 兼容性测试
  - [ ] 文档完善

---

### Week 5-6: 数据统计和扩展功能（可选）
**目标**: 使用统计、通知系统等

- **Week 5**:
  - [ ] UsageDashboard 组件
  - [ ] 图表集成
  - [ ] 使用记录

- **Week 6**:
  - [ ] 通知中心
  - [ ] 发票管理（可选）
  - [ ] 最终优化

---

## ✅ 验收标准

### 核心功能（必须）
- ✅ 用户可以注册、登录、登出
- ✅ 用户可以查看和选择订阅计划
- ✅ 用户可以完成支付流程（支付宝/微信）
- ✅ 用户可以查看支付状态和历史
- ✅ 用户可以管理 API Key
- ✅ 用户可以修改个人信息

### 扩展功能（可选）
- ⭐ 用户可以查看使用统计
- ⭐ 用户可以接收系统通知
- ⭐ 用户可以申请发票
- ⭐ 用户可以导出数据

### 用户体验
- ✅ 界面美观，响应式设计
- ✅ 加载状态明确
- ✅ 错误提示友好
- ✅ 操作流程顺畅
- ✅ 移动端体验良好

### 技术质量
- ✅ TypeScript 类型完整
- ✅ 组件可复用性高
- ✅ API 调用统一封装
- ✅ 错误处理完善
- ✅ 性能优化到位
- ✅ 代码规范统一

---

## 🚀 立即开始的任务

### 本周任务（Week 1）
**优先级 1: 订阅计划展示**
```bash
# 1. 创建组件
touch src/components/subscription/PlanList.tsx
touch src/components/subscription/PlanCard.tsx
touch src/components/subscription/PlanComparison.tsx

# 2. 实现功能
- 对接 GET /plans/ API
- 卡片式布局
- 响应式设计
```

**优先级 2: 支付流程基础**
```bash
# 1. 创建组件
touch src/components/payment/PaymentForm.tsx
touch src/components/payment/PaymentMethodSelector.tsx
touch src/components/payment/QRCodeDisplay.tsx

# 2. 实现功能
- 支付方式选择
- 创建支付订单
- 二维码展示
```

---

## 📞 需要的后端支持

### 已有 API ✅
- **认证相关** - 完整
- **支付相关** - 完整
- **订阅计划** - 完整

### 待开发 API ⏳
- **使用统计 API** (GET /quota/usage/stats)
- **配额管理 API** (GET /quota/)
- **通知系统 API** (GET /notifications/)
- **发票管理 API** (GET /invoices/) - 可选

---

## 📝 开发规范

### 组件命名
- 使用 PascalCase
- 功能描述性命名
- 例: `PaymentMethodSelector.tsx`

### 文件组织
- 相关组件放在同一目录
- 使用 index.ts 导出
- 保持目录结构清晰

### 代码规范
- 使用 TypeScript strict 模式
- 使用 ESLint + Prettier
- 编写单元测试（可选）

### API 调用
- 统一使用 services/ 层
- 错误处理统一
- 加载状态统一

---

**当前阶段**: Phase 2 已完成 ✅ (订阅计划展示功能)

**下一阶段**: Phase 3 - 支付功能完善 🎯

**已完成进度**:
- ✅ Phase 1: 基础框架
- ✅ Phase 2: 订阅计划展示

**待开发**: Phase 3-8 (支付、API Key、用户中心、统计等)

**预计完成时间**: 3-5 周（剩余核心功能）

**最近更新**: 2025-10-17 - 完成订阅计划展示和对比功能
