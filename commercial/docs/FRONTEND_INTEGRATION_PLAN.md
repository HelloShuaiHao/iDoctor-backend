# CTAI_web 商业化功能集成方案

**日期**: 2025-10-18
**目标**: 将 commercial/frontend 的商业功能集成到 CTAI_web 医学影像处理前端

---

## 📊 现状分析

### Commercial Frontend (React + TypeScript)
- ✅ **完整的商业功能**: 认证、支付、订阅、配额管理
- ✅ **现代化技术栈**: React 19 + Vite + Tailwind + TypeScript
- ✅ **高质量 UI**: shadcn/ui + Radix UI + Element Plus
- ⚠️ **独立运行**: 端口 3000，与 CTAI_web 分离

### CTAI_web (Vue 2)
- ✅ **完整的医学影像处理**: 上传、处理、结果展示、标注
- ✅ **优秀的 UX**: Apple 风格设计，双语支持
- ❌ **无认证系统**: 直接访问后端 API
- ❌ **无配额管理**: 不显示使用量
- ❌ **无支付功能**: 无订阅管理

---

## 🎯 集成方案对比

### 方案 A: 混合部署（推荐）⭐

**架构**:
```
用户访问
   ↓
Nginx 反向代理
   ├─ /app/*        → CTAI_web (Vue 2, 医学影像处理)
   ├─ /commercial/* → Commercial Frontend (React, 商业功能)
   └─ /api/*        → Backend Services
```

**优点**:
- ✅ 快速集成（无需重写商业功能）
- ✅ 各自技术栈独立（Vue 和 React 不冲突）
- ✅ 商业功能完整保留（支付、订阅已验证）
- ✅ 便于后续维护（分离关注点）

**缺点**:
- ⚠️ 需要路由配置
- ⚠️ 两套前端需要共享认证状态

**工作量**: 2-3 天

---

### 方案 B: Vue 重写商业功能

**架构**:
```
CTAI_web (Vue 2)
   ├─ 原有医学影像功能
   └─ 新增商业功能（Vue 组件重写）
       ├─ 登录/注册页面
       ├─ 支付页面
       ├─ 订阅管理页面
       └─ 配额显示组件
```

**优点**:
- ✅ 统一技术栈（纯 Vue）
- ✅ 单一应用部署
- ✅ UX 一致性

**缺点**:
- ❌ 大量重复开发（~5-7 天）
- ❌ 商业模块已验证代码废弃
- ❌ 可能引入新 bug

**工作量**: 5-7 天

---

### 方案 C: 微前端架构（过度设计）

**架构**: 使用 qiankun 或 single-spa

**优点**:
- ✅ React 和 Vue 无缝集成
- ✅ 独立部署

**缺点**:
- ❌ 复杂度高
- ❌ 学习曲线陡峭
- ❌ 调试困难

**工作量**: 7-10 天

---

## ✅ 选定方案: **方案 A (混合部署)**

### 理由
1. **快速上线**: 商业功能已完整实现，无需重写
2. **风险最低**: 两个应用各自独立，互不影响
3. **易于维护**: React 和 Vue 分别维护
4. **用户体验**: 通过统一的导航和共享认证实现无缝跳转

---

## 🏗️ 实施计划

### 阶段 1: 认证集成（1 天）

#### 1.1 在 CTAI_web 中添加登录页面

**文件**: `CTAI_web/src/components/Login.vue` (新增)

```vue
<template>
  <div class="login-container">
    <el-card class="login-card">
      <el-tabs v-model="activeTab">
        <!-- 登录标签 -->
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" :rules="rules" ref="loginForm">
            <el-form-item prop="username">
              <el-input v-model="loginForm.username" placeholder="用户名或邮箱"></el-input>
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="密码"></el-input>
            </el-form-item>
            <el-button type="primary" @click="handleLogin" :loading="loading">登录</el-button>
          </el-form>
        </el-tab-pane>

        <!-- 注册标签 -->
        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" :rules="registerRules" ref="registerForm">
            <el-form-item prop="username">
              <el-input v-model="registerForm.username" placeholder="用户名"></el-input>
            </el-form-item>
            <el-form-item prop="email">
              <el-input v-model="registerForm.email" placeholder="邮箱"></el-input>
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="registerForm.password" type="password" placeholder="密码"></el-input>
            </el-form-item>
            <el-button type="success" @click="handleRegister" :loading="loading">注册</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      activeTab: 'login',
      loading: false,
      loginForm: { username: '', password: '' },
      registerForm: { username: '', email: '', password: '' },
      rules: {
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
        password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
      },
      registerRules: {
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
        email: [
          { required: true, message: '请输入邮箱', trigger: 'blur' },
          { type: 'email', message: '请输入有效邮箱', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, message: '密码至少6位', trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    async handleLogin() {
      this.$refs.loginForm.validate(async valid => {
        if (!valid) return

        this.loading = true
        try {
          const response = await axios.post('http://localhost:9001/auth/login', {
            username_or_email: this.loginForm.username,
            password: this.loginForm.password
          })

          // 保存 token
          localStorage.setItem('access_token', response.data.access_token)
          localStorage.setItem('refresh_token', response.data.refresh_token)

          this.$message.success('登录成功')
          this.$router.push('/')
        } catch (error) {
          this.$message.error(error.response?.data?.detail || '登录失败')
        } finally {
          this.loading = false
        }
      })
    },

    async handleRegister() {
      this.$refs.registerForm.validate(async valid => {
        if (!valid) return

        this.loading = true
        try {
          await axios.post('http://localhost:9001/auth/register', this.registerForm)
          this.$message.success('注册成功，请登录')
          this.activeTab = 'login'
        } catch (error) {
          this.$message.error(error.response?.data?.detail || '注册失败')
        } finally {
          this.loading = false
        }
      })
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
  padding: 20px;
}
</style>
```

#### 1.2 更新 api.js 添加 token 拦截器

**文件**: `CTAI_web/src/api.js`

```javascript
// 在现有代码基础上添加

// 请求拦截器：自动添加 token
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, error => {
  return Promise.reject(error)
})

// 响应拦截器：处理 token 过期
axios.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config

    // 如果是 401 且未重试过
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // 尝试刷新 token
        const refreshToken = localStorage.getItem('refresh_token')
        const response = await axios.post('http://localhost:9001/auth/refresh', {
          refresh_token: refreshToken
        })

        // 更新 token
        localStorage.setItem('access_token', response.data.access_token)
        localStorage.setItem('refresh_token', response.data.refresh_token)

        // 重试原请求
        originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`
        return axios(originalRequest)
      } catch (refreshError) {
        // 刷新失败，跳转登录
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/#/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)
```

#### 1.3 添加路由守卫

**文件**: `CTAI_web/src/main.js`

```javascript
// 在路由配置后添加

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')

  // 如果访问登录页，直接放行
  if (to.path === '/login') {
    next()
    return
  }

  // 其他页面需要登录
  if (!token) {
    next('/login')
  } else {
    next()
  }
})
```

---

### 阶段 2: 配额显示（0.5 天）

#### 2.1 在 Header 中添加配额显示

**文件**: `CTAI_web/src/components/Header.vue`

```vue
<!-- 在现有 Header 中添加配额显示 -->
<template>
  <div class="header">
    <!-- 现有导航 -->
    <div class="nav">...</div>

    <!-- 新增：用户信息和配额 -->
    <div class="user-section">
      <el-dropdown @command="handleCommand">
        <span class="el-dropdown-link">
          <i class="el-icon-user"></i>
          {{ username }}
          <i class="el-icon-arrow-down"></i>
        </span>
        <el-dropdown-menu slot="dropdown">
          <el-dropdown-item command="quota">
            📊 配额使用: {{ quotaUsed }}/{{ quotaLimit }}
          </el-dropdown-item>
          <el-dropdown-item command="subscription" divided>
            💳 订阅管理
          </el-dropdown-item>
          <el-dropdown-item command="logout" divided>
            🚪 退出登录
          </el-dropdown-item>
        </el-dropdown-menu>
      </el-dropdown>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      username: '',
      quotaUsed: 0,
      quotaLimit: 10
    }
  },
  async mounted() {
    await this.loadUserInfo()
    await this.loadQuota()
  },
  methods: {
    async loadUserInfo() {
      try {
        const response = await this.$http.get('http://localhost:9001/users/me')
        this.username = response.data.username
      } catch (error) {
        console.error('Failed to load user info:', error)
      }
    },

    async loadQuota() {
      try {
        const response = await this.$http.get('http://localhost:4200/admin/quotas/users/me')
        const apiQuota = response.data.quotas.find(q => q.type_key === 'api_calls_full_process')
        if (apiQuota) {
          this.quotaUsed = apiQuota.used
          this.quotaLimit = apiQuota.limit
        }
      } catch (error) {
        console.error('Failed to load quota:', error)
      }
    },

    handleCommand(command) {
      switch (command) {
        case 'quota':
          // 跳转到商业前端的配额页面
          window.location.href = 'http://localhost:3000/#/usage-stats'
          break
        case 'subscription':
          // 跳转到商业前端的订阅页面
          window.location.href = 'http://localhost:3000/#/subscription'
          break
        case 'logout':
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          this.$router.push('/login')
          break
      }
    }
  }
}
</script>
```

---

### 阶段 3: 配额检查与错误处理（0.5 天）

#### 3.1 在上传前检查配额

**文件**: `CTAI_web/src/components/Content.vue`

```vue
<script>
export default {
  methods: {
    async handleSubmit() {
      // 1. 先检查配额
      const hasQuota = await this.checkQuota()
      if (!hasQuota) {
        this.$confirm(
          '您的处理配额已用尽，请升级套餐以继续使用',
          '配额不足',
          {
            confirmButtonText: '立即升级',
            cancelButtonText: '取消',
            type: 'warning'
          }
        ).then(() => {
          // 跳转到订阅页面
          window.location.href = 'http://localhost:3000/#/subscription'
        })
        return
      }

      // 2. 继续原有上传逻辑
      this.doUpload()
    },

    async checkQuota() {
      try {
        const response = await this.$http.get('http://localhost:4200/admin/quotas/users/me')
        const apiQuota = response.data.quotas.find(q => q.type_key === 'api_calls_full_process')

        if (apiQuota) {
          return apiQuota.remaining > 0
        }
        return false
      } catch (error) {
        console.error('Failed to check quota:', error)
        return true // 检查失败时允许继续（可配置）
      }
    }
  }
}
</script>
```

#### 3.2 处理 402 配额耗尽错误

**文件**: `CTAI_web/src/api.js`

```javascript
// 在响应拦截器中添加

axios.interceptors.response.use(
  response => response,
  async error => {
    // ... 现有 401 处理 ...

    // 处理 402 Payment Required (配额耗尽)
    if (error.response?.status === 402) {
      const quotaInfo = error.response.data

      // 弹窗提示
      Vue.prototype.$confirm(
        `${quotaInfo.message}\n剩余配额: ${quotaInfo.remaining}`,
        '配额不足',
        {
          confirmButtonText: '立即升级',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(() => {
        window.location.href = 'http://localhost:3000/#/subscription'
      })

      return Promise.reject(error)
    }

    return Promise.reject(error)
  }
)
```

---

### 阶段 4: 跨应用导航（0.5 天）

#### 4.1 统一导航栏

在 CTAI_web Header 中添加到商业功能的链接：

```vue
<el-menu mode="horizontal">
  <el-menu-item index="1" @click="$router.push('/')">
    🏥 影像处理
  </el-menu-item>
  <el-menu-item index="2" @click="$router.push('/results')">
    📊 处理结果
  </el-menu-item>
  <el-menu-item index="3" @click="goToCommercial('/usage-stats')">
    📈 配额管理
  </el-menu-item>
  <el-menu-item index="4" @click="goToCommercial('/subscription')">
    💳 订阅套餐
  </el-menu-item>
</el-menu>

<script>
export default {
  methods: {
    goToCommercial(path) {
      // 跳转到商业前端，同时传递 token
      const token = localStorage.getItem('access_token')
      window.location.href = `http://localhost:3000/#${path}?token=${token}`
    }
  }
}
</script>
```

#### 4.2 商业前端接收 token

**文件**: `commercial/frontend/src/App.tsx`

```typescript
useEffect(() => {
  // 从 URL 参数读取 token（如果有）
  const urlParams = new URLSearchParams(window.location.search)
  const tokenFromUrl = urlParams.get('token')

  if (tokenFromUrl) {
    localStorage.setItem('access_token', tokenFromUrl)
    // 清除 URL 参数
    window.history.replaceState({}, '', window.location.pathname + window.location.hash)
  }
}, [])
```

---

### 阶段 5: Nginx 配置（0.5 天）

#### 5.1 配置反向代理

**文件**: `/etc/nginx/sites-available/idoctor` (生产环境)

```nginx
server {
    listen 80;
    server_name idoctor.com;

    # CTAI_web 主应用
    location / {
        root /var/www/ctai_web/dist;
        try_files $uri $uri/ /index.html;
    }

    # 商业功能前端
    location /commercial/ {
        alias /var/www/commercial_frontend/dist/;
        try_files $uri $uri/ /commercial/index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://localhost:4200/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 认证服务
    location /auth/ {
        proxy_pass http://localhost:9001/auth/;
    }

    # 支付服务
    location /payment/ {
        proxy_pass http://localhost:9002/;
    }
}
```

#### 5.2 开发环境配置

**文件**: `CTAI_web/vue.config.js` (新增)

```javascript
module.exports = {
  devServer: {
    port: 7500,
    proxy: {
      '/api': {
        target: 'http://localhost:4200',
        changeOrigin: true,
        pathRewrite: { '^/api': '' }
      },
      '/auth': {
        target: 'http://localhost:9001',
        changeOrigin: true
      },
      '/payment': {
        target: 'http://localhost:9002',
        changeOrigin: true
      }
    }
  }
}
```

---

## 📝 开发任务清单

### Week 1: 核心认证集成

- [ ] Day 1: 认证功能
  - [ ] 创建 Login.vue 组件
  - [ ] 更新 api.js 添加拦截器
  - [ ] 添加路由守卫
  - [ ] 测试登录/注册流程

- [ ] Day 2: 配额显示
  - [ ] Header 添加用户菜单
  - [ ] 获取配额 API
  - [ ] 配额警告提示
  - [ ] 上传前配额检查

- [ ] Day 3: 错误处理与跳转
  - [ ] 402 错误处理
  - [ ] 跨应用导航
  - [ ] token 共享机制
  - [ ] 测试完整流程

---

## 🧪 测试场景

### 测试 1: 新用户注册流程
1. 访问 `http://localhost:7500/#/login`
2. 点击"注册"标签
3. 填写用户名、邮箱、密码
4. 提交注册
5. ✅ 验证：自动分配配额，返回登录页

### 测试 2: 登录并查看配额
1. 登录成功后跳转首页
2. 查看 Header 用户菜单
3. ✅ 验证：显示配额使用情况（0/10）

### 测试 3: 上传 DICOM 并扣除配额
1. 上传 DICOM ZIP
2. 提交处理任务
3. 等待处理完成
4. ✅ 验证：配额变为 1/10

### 测试 4: 配额耗尽提示
1. 模拟配额用尽（调用 10 次处理）
2. 尝试第 11 次上传
3. ✅ 验证：显示"配额不足"弹窗
4. 点击"立即升级"
5. ✅ 验证：跳转到订阅页面（commercial frontend）

### 测试 5: 支付升级配额
1. 在商业前端选择套餐
2. 完成支付
3. 返回 CTAI_web
4. ✅ 验证：配额更新为新套餐限制

---

## 📊 时间估算

| 阶段 | 任务 | 时间 |
|------|------|------|
| 1 | 认证集成 | 1 天 |
| 2 | 配额显示 | 0.5 天 |
| 3 | 配额检查 | 0.5 天 |
| 4 | 跨应用导航 | 0.5 天 |
| 5 | Nginx 配置 | 0.5 天 |
| 6 | 测试与调试 | 0.5 天 |
| **总计** | | **3.5 天** |

---

## 🎯 成功标准

- ✅ 用户可以在 CTAI_web 登录/注册
- ✅ Header 实时显示配额使用情况
- ✅ 上传 DICOM 自动扣除配额
- ✅ 配额耗尽时阻止操作并引导升级
- ✅ 点击"订阅管理"跳转到商业前端
- ✅ 支付完成后配额自动更新
- ✅ token 在两个前端间无缝共享
- ✅ 用户体验流畅，无技术栈感知

---

## 🔄 后续优化（可选）

### Phase 2: 深度集成（Week 2）
- 在 CTAI_web 中嵌入配额图表（复用 commercial 的组件逻辑）
- 添加配额使用趋势分析
- 实时 WebSocket 配额更新

### Phase 3: 移动端优化
- 响应式设计优化
- 微信小程序版本

### Phase 4: 统一主题
- 统一 CTAI_web 和 commercial 的视觉风格
- 共享 CSS 变量和设计系统

---

**方案制定完成，准备开始实施！** 🚀
