<template>
  <div class="login-container">
    <!-- 背景效果 - 与Header一致 -->
    <div class="bg-arc"></div>

    <div class="login-card">
      <!-- Logo和标题 -->
      <div class="login-header">
        <div class="logo-area">
          <i class="el-icon-collection-tag logo-icon"></i>
        </div>
        <h1 class="login-title">{{ $t('system.name') }}</h1>
        <p class="login-subtitle">{{ $t('login.subtitle') }}</p>
      </div>

      <!-- 登录表单 -->
      <el-form
        :model="loginForm"
        :rules="loginRules"
        ref="loginForm"
        class="login-form"
        @submit.native.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            :placeholder="$t('login.usernamePlaceholder')"
            prefix-icon="el-icon-user"
            clearable
            size="large"
          ></el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            :placeholder="$t('login.passwordPlaceholder')"
            prefix-icon="el-icon-lock"
            show-password
            size="large"
            @keyup.enter.native="handleLogin"
          ></el-input>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="handleLogin"
            :loading="loading"
            class="login-button"
            size="large"
          >
            {{ loading ? $t('login.loggingIn') : $t('login.loginButton') }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 注册提示 -->
      <div class="register-hint">
        <span class="hint-text">{{ $t('login.noAccount') }}</span>
        <a href="javascript:void(0)" @click="goToRegister" class="register-link">
          {{ $t('login.registerNow') }}
        </a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Login',
  data() {
    return {
      loading: false,
      loginForm: {
        username: '',
        password: ''
      },
      loginRules: {
        username: [
          { required: true, message: this.$t('login.usernameRequired'), trigger: 'blur' }
        ],
        password: [
          { required: true, message: this.$t('login.passwordRequired'), trigger: 'blur' }
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
          const authBaseUrl = process.env.VUE_APP_AUTH_BASE_URL || 'http://localhost:9001'
          // authBaseUrl 已包含 /api/auth，只需添加 /login
          const response = await this.$http.post(`${authBaseUrl}/login`, {
            username_or_email: this.loginForm.username,
            password: this.loginForm.password
          })

          // 保存 token 到 localStorage
          localStorage.setItem('access_token', response.data.access_token)
          localStorage.setItem('refresh_token', response.data.refresh_token)

          this.$message({
            message: this.$t('login.loginSuccess'),
            type: 'success',
            duration: 2000
          })

          // 发送登录成功事件，让Header组件刷新用户信息
          this.$root.$emit('user-logged-in')

          // 跳转到首页（使用路由，不刷新页面）
          // 使用 catch 捕获重定向警告，避免控制台报错
          setTimeout(() => {
            this.$router.push('/').catch(() => {})
          }, 500)
        } catch (error) {
          console.error('Login error:', error)
          this.$message({
            message: error.response?.data?.detail || this.$t('login.loginFailed'),
            type: 'error',
            duration: 3000
          })
        } finally {
          this.loading = false
        }
      })
    },

    goToRegister() {
      // 跳转到商业前端主页
      const commercialUrl = process.env.VUE_APP_COMMERCIAL_URL || 'http://localhost:3000'
      window.location.href = commercialUrl
    }
  }
}
</script>

<style scoped>
/* 容器 - 与Header背景保持一致 */
.login-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
  overflow: hidden;
  background: #f1f9ff;
}

/* 背景效果 - 复用Header的bg-arc样式 */
.bg-arc {
  position: absolute;
  inset: 0;
  background: radial-gradient(
      at 20% 25%,
      rgba(10, 132, 255, 0.25),
      rgba(10, 132, 255, 0) 55%
    ),
    radial-gradient(
      at 85% 70%,
      rgba(52, 199, 89, 0.28),
      rgba(52, 199, 89, 0) 60%
    ),
    linear-gradient(180deg, #f1f9ff 0%, #ffffff 60%);
  pointer-events: none;
  z-index: 0;
}

/* 登录卡片 - 玻璃态效果与Header.bar一致 */
.login-card {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 420px;
  padding: 48px 40px;
  backdrop-filter: saturate(160%) blur(20px);
  -webkit-backdrop-filter: saturate(160%) blur(20px);
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
  animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Logo和标题区域 */
.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.logo-area {
  margin-bottom: 16px;
}

.logo-icon {
  font-size: 56px;
  color: #0a84ff;
  filter: drop-shadow(0 4px 12px rgba(10, 132, 255, 0.3));
}

.login-title {
  margin: 0 0 8px 0;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 0.5px;
  background: linear-gradient(100deg, #0a84ff 0%, #0a6dff 45%, #005ac8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-subtitle {
  margin: 0;
  font-size: 14px;
  color: #51606f;
  letter-spacing: 0.3px;
}

/* 表单样式 */
.login-form {
  margin-bottom: 24px;
}

.login-form >>> .el-form-item {
  margin-bottom: 20px;
}

.login-form >>> .el-input__inner {
  height: 48px;
  line-height: 48px;
  border-radius: 12px;
  padding: 0 16px 0 40px;
  font-size: 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.7);
  transition: all 0.3s;
}

.login-form >>> .el-input__inner:focus {
  border-color: #0a84ff;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(10, 132, 255, 0.1);
}

.login-form >>> .el-input__prefix {
  left: 12px;
  font-size: 18px;
  color: #0a84ff;
}

.login-form >>> .el-input__suffix {
  right: 12px;
}

/* 登录按钮 */
.login-button {
  width: 100%;
  height: 50px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
  border-radius: 12px;
  background: linear-gradient(135deg, #0a84ff 0%, #0067d1 100%);
  border: none;
  box-shadow: 0 8px 20px rgba(10, 132, 255, 0.3);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.login-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(10, 132, 255, 0.4);
}

.login-button:active {
  transform: translateY(0);
}

/* 注册提示 */
.register-hint {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.hint-text {
  font-size: 14px;
  color: #51606f;
  margin-right: 8px;
}

.register-link {
  font-size: 14px;
  font-weight: 600;
  color: #0a84ff;
  text-decoration: none;
  transition: all 0.2s;
  position: relative;
}

.register-link::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, #0a84ff 0%, #0067d1 100%);
  transition: width 0.3s;
}

.register-link:hover {
  color: #0067d1;
}

.register-link:hover::after {
  width: 100%;
}

/* 响应式 */
@media (max-width: 500px) {
  .login-card {
    padding: 36px 28px;
    border-radius: 20px;
  }

  .logo-icon {
    font-size: 48px;
  }

  .login-title {
    font-size: 28px;
  }

  .login-form >>> .el-input__inner {
    height: 44px;
    line-height: 44px;
  }

  .login-button {
    height: 46px;
    font-size: 15px;
  }
}

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
  .login-container {
    background: #11181f;
  }

  .bg-arc {
    background: radial-gradient(
        at 18% 25%,
        rgba(10, 132, 255, 0.35),
        rgba(10, 132, 255, 0) 55%
      ),
      radial-gradient(
        at 85% 70%,
        rgba(52, 199, 89, 0.35),
        rgba(52, 199, 89, 0) 60%
      ),
      linear-gradient(180deg, #1c2530 0%, #11181f 60%);
  }

  .login-card {
    background: rgba(30, 40, 52, 0.75);
    border-color: rgba(255, 255, 255, 0.1);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
  }

  .login-subtitle,
  .hint-text {
    color: #8fa2b4;
  }

  .login-form >>> .el-input__inner {
    background: rgba(55, 65, 78, 0.6);
    color: #e6f1ff;
    border-color: rgba(255, 255, 255, 0.12);
  }

  .login-form >>> .el-input__inner:focus {
    background: rgba(55, 65, 78, 0.8);
    border-color: #0a84ff;
  }

  .register-hint {
    border-top-color: rgba(255, 255, 255, 0.08);
  }
}
</style>
