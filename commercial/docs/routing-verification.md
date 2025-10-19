# iDoctor 前端路由验证文档

本文档详细说明两个前端应用（CTAI_web 和 Commercial Frontend）之间的路由问题和解决方案。

## 目录

- [应用架构](#应用架构)
- [路由问题分析](#路由问题分析)
- [已修复的问题](#已修复的问题)
- [需要注意的问题](#需要注意的问题)
- [验证步骤](#验证步骤)
- [故障排查](#故障排查)

---

## 应用架构

### 应用配置

| 应用 | 框架 | 路由模式 | 本地端口 | 生产URL |
|------|------|---------|---------|---------|
| CTAI_web | Vue 2 | Hash Router (`#`) | 7500 | http://ai.bygpu.com:55304 |
| Commercial Frontend | React | Browser Router | 3000 | http://ai.bygpu.com:55305 |

### 路由跳转场景

**场景 1: CTAI_web → Commercial**
- 触发位置: `CTAI_web/src/components/Header.vue` 用户菜单
- 操作: 用户点击"订阅管理"菜单项
- 目标页面: Commercial 前端的订阅页面
- Token 传递: URL 参数 `?token=xxx`

**场景 2: Commercial → CTAI_web**
- 触发位置: `Commercial/src/pages/HomePage.tsx`
- 操作: 用户点击"进入主应用"按钮
- 目标页面: CTAI_web 主页
- Token 传递: 不需要（已在localStorage）

---

## 路由问题分析

### 问题 1: CTAI_web 硬编码了 localhost URL ❌

**位置**: `CTAI_web/src/components/Header.vue:212`

**原代码**:
```javascript
window.location.href = `http://localhost:3000/#/subscription?token=${token}`;
```

**问题**:
- 生产环境中仍跳转到 localhost:3000
- 导致在服务器上无法正常跳转

**修复状态**: ✅ 已修复

**修复后**:
```javascript
const commercialUrl = process.env.VUE_APP_COMMERCIAL_URL || 'http://localhost:3000';
window.location.href = `${commercialUrl}/#/subscription?token=${token}`;
```

---

### 问题 2: 环境变量配置错误 ❌

**位置**: `CTAI_web/.env.production`

**原配置**:
```bash
VUE_APP_COMMERCIAL_URL=http://localhost:3000
```

**问题**: 生产环境配置使用了本地URL

**修复状态**: ✅ 已修复

**修复后**:
```bash
VUE_APP_COMMERCIAL_URL=http://ai.bygpu.com:55305
```

---

### 问题 3: Hash Router vs Browser Router 兼容性 ⚠️

**问题描述**:
- CTAI_web 使用 Vue Hash Router，URL格式: `http://example.com/#/subscription`
- Commercial 使用 React Browser Router，URL格式: `http://example.com/subscription`
- 当 CTAI_web 跳转时使用 `${url}/#/subscription?token=xxx`

**当前行为**:
```
CTAI_web 跳转:
http://ai.bygpu.com:55305/#/subscription?token=abc123

Commercial 接收:
- URL: http://ai.bygpu.com:55305/#/subscription?token=abc123
- React Router 看到: / (因为 hash 部分被忽略)
- 页面显示: 首页，而不是订阅页
```

**影响**:
- ❌ 跳转后显示首页而不是订阅页
- ❌ Token 无法被 React 应用读取（在 hash 部分）

**解决方案选项**:

#### 选项 A: 使用 Browser Router 跳转（推荐）✨

修改 CTAI_web 跳转逻辑为:
```javascript
// 去掉 hash (#)
window.location.href = `${commercialUrl}/subscription?token=${token}`;
```

**优点**:
- ✅ 符合现代 web 应用标准
- ✅ SEO 友好
- ✅ URL 更简洁

**缺点**:
- ⚠️ 需要 Nginx 配置 `try_files`（已配置）

#### 选项 B: Commercial 改用 Hash Router

修改 Commercial 使用 HashRouter:
```typescript
import { HashRouter } from 'react-router-dom';
```

**优点**:
- ✅ 兼容 CTAI_web 的 hash 模式
- ✅ 不需要服务器配置

**缺点**:
- ❌ URL 不美观 (`#/subscription`)
- ❌ SEO 不友好
- ❌ 不符合现代标准

**推荐**: **选项 A - 使用 Browser Router**

---

### 问题 4: Token 接收逻辑缺失 ❌

**问题**: Commercial 前端没有从 URL 参数读取 token 的逻辑

**当前行为**:
1. CTAI_web 跳转时在 URL 中传递 token
2. Commercial 前端加载，但不读取 URL 参数
3. 用户需要重新登录

**需要添加的功能**:

在 `Commercial/src/context/AuthContext.tsx` 中添加:
```typescript
useEffect(() => {
  const initAuth = async () => {
    // 1. 检查 URL 参数中的 token
    const searchParams = new URLSearchParams(window.location.search);
    const urlToken = searchParams.get('token');

    if (urlToken) {
      // 保存 token 到 localStorage
      localStorage.setItem('access_token', urlToken);
      // 清除 URL 参数
      window.history.replaceState({}, '', window.location.pathname);
    }

    // 2. 正常的认证检查
    if (authService.isAuthenticated()) {
      try {
        const userData = await authService.getCurrentUser();
        setUser(userData);
      } catch (error) {
        console.error('获取用户信息失败:', error);
        authService.logout();
      }
    }
    setLoading(false);
  };

  initAuth();
}, []);
```

**修复状态**: ⚠️ 待实现

---

### 问题 5: Nginx 反向代理对 React Router 的支持 ✅

**Nginx 配置验证**:

```nginx
location / {
    root /var/www/idoctor-commercial/dist;
    try_files $uri $uri/ /index.html;  # ✅ 正确配置
    index index.html;
}
```

**验证点**:
- ✅ `try_files` 指令存在
- ✅ fallback 到 `/index.html`
- ✅ 支持刷新任意路由

**测试场景**:
1. 访问 `http://ai.bygpu.com:55305/subscription`
2. 刷新页面
3. 预期: 正常显示订阅页面（不是 404）

---

## 已修复的问题

### ✅ 修复 1: CTAI_web 环境变量

**文件**: `CTAI_web/.env.production`

**修改**:
```diff
- VUE_APP_COMMERCIAL_URL=http://localhost:3000
+ VUE_APP_COMMERCIAL_URL=http://ai.bygpu.com:55305
```

### ✅ 修复 2: Header.vue 使用环境变量

**文件**: `CTAI_web/src/components/Header.vue`

**修改**:
```diff
  case 'subscription':
    const token = localStorage.getItem('access_token');
-   window.location.href = `http://localhost:3000/#/subscription?token=${token}`;
+   const commercialUrl = process.env.VUE_APP_COMMERCIAL_URL || 'http://localhost:3000';
+   window.location.href = `${commercialUrl}/#/subscription?token=${token}`;
    break;
```

### ✅ 修复 3: Commercial 前端环境变量

**文件**: `commercial/frontend/.env.production`

**配置**:
```bash
VITE_AUTH_API_URL=/api/auth
VITE_PAYMENT_API_URL=/api/payment
VITE_IDOCTOR_API_URL=/api/idoctor
VITE_IDOCTOR_APP_URL=http://ai.bygpu.com:55304
```

---

## 需要注意的问题

### ⚠️ 待修复 1: Hash Router 兼容性

**现状**: CTAI_web 跳转使用 `${url}/#/subscription`

**建议修改为**:
```javascript
// Header.vue line 213
window.location.href = `${commercialUrl}/subscription?token=${token}`;
// 去掉 /#
```

### ⚠️ 待实现 2: Token 接收逻辑

**需要在 Commercial 前端添加 URL 参数处理**

**实现位置**: `commercial/frontend/src/context/AuthContext.tsx`

**代码**: 见上方"问题 4"部分

### ⚠️ 待验证 3: CORS 配置

**验证点**:
- Commercial 前端通过 Nginx 访问后端 API
- URL: `http://ai.bygpu.com:55305/api/auth/*`
- 是否正确代理到 `localhost:9001`

---

## 验证步骤

### Step 1: 本地开发环境验证

```bash
# 1. 启动所有服务
cd commercial/docker
docker-compose up -d

cd ../frontend
npm run dev  # 端口 3000

cd ../../CTAI_web
npm run serve  # 端口 7500

# 2. 测试跳转
# 访问: http://localhost:7500
# 登录后点击用户菜单 -> "订阅管理"
# 应跳转到: http://localhost:3000/subscription?token=xxx
```

### Step 2: 生产环境验证

```bash
# 1. 构建 Commercial 前端
cd commercial/frontend
npm run build

# 2. 部署
bash ../scripts/deploy-frontend.sh

# 3. 构建 CTAI_web
cd ../../CTAI_web
npm run build

# 4. 部署 CTAI_web (假设有部署脚本)
# ...

# 5. 访问测试
# 访问: http://ai.bygpu.com:55304
# 登录 -> 用户菜单 -> "订阅管理"
# 应跳转到: http://ai.bygpu.com:55305/subscription?token=xxx
```

### Step 3: React Router 深度链接验证

```bash
# 1. 直接访问子路由
curl -I http://ai.bygpu.com:55305/subscription
# 预期: HTTP 200

curl -I http://ai.bygpu.com:55305/api-keys
# 预期: HTTP 200

curl -I http://ai.bygpu.com:55305/payment-history
# 预期: HTTP 200

# 2. 浏览器测试
# 访问 http://ai.bygpu.com:55305/subscription
# 刷新页面 (F5)
# 预期: 正常显示页面，不是 404
```

### Step 4: Token 传递验证

**手动测试**:
```javascript
// 在浏览器控制台执行
localStorage.setItem('access_token', 'test_token_123');
window.location.href = 'http://localhost:3000/subscription?token=new_token_456';

// 检查:
localStorage.getItem('access_token')
// 预期: 'new_token_456'
```

### Step 5: API 代理验证

```bash
# 测试 Nginx 反向代理
curl http://ai.bygpu.com:55305/api/auth/health
# 预期: {"status":"ok","service":"auth"}

curl http://ai.bygpu.com:55305/api/payment/health
# 预期: {"status":"ok","service":"payment"}

# 浏览器开发者工具 Network 标签
# 发送请求应该显示:
# Request URL: http://ai.bygpu.com:55305/api/auth/login
# (不是 localhost:9001)
```

---

## 故障排查

### 问题: 跳转后显示首页而不是订阅页

**原因**: Hash Router 兼容性问题

**解决**:
```javascript
// CTAI_web/src/components/Header.vue
// 去掉 /#
window.location.href = `${commercialUrl}/subscription?token=${token}`;
```

### 问题: Token 未自动登录

**原因**: 缺少 URL 参数处理逻辑

**解决**: 在 AuthContext 添加 URL 参数读取（见上文）

### 问题: 刷新页面返回 404

**原因**: Nginx 配置缺少 `try_files`

**解决**: 已在 Nginx 配置中添加
```nginx
try_files $uri $uri/ /index.html;
```

### 问题: API 请求 CORS 错误

**原因**:
1. 前端直接访问 localhost:9001
2. Nginx 代理配置错误

**解决**:
1. 检查 `.env.production` 使用相对路径 `/api/auth`
2. 重新构建前端
3. 验证 Nginx 配置

---

## 总结

### 关键修改清单

- [x] CTAI_web `.env.production` - 更新 Commercial URL
- [x] CTAI_web `Header.vue` - 使用环境变量
- [x] Commercial `.env.production` - API 相对路径
- [ ] CTAI_web `Header.vue` - 去掉 hash 路由（建议）
- [ ] Commercial `AuthContext.tsx` - 添加 URL token 处理

### 部署后验证清单

- [ ] CTAI_web → Commercial 跳转正常
- [ ] Commercial → CTAI_web 跳转正常
- [ ] Token 自动登录生效
- [ ] React Router 深度链接可刷新
- [ ] API 代理无 CORS 错误
- [ ] Nginx 日志无异常

---

**最后更新**: 2025-01-19
**文档版本**: 1.0
**相关文档**: [Nginx 部署指南](./nginx-deployment.md)
