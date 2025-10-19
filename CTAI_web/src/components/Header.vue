<template>
  <header id="Header">
    <!-- 背景可留 / 可移除 -->
    <div class="bg-arc"></div>

    <div class="bar">
      <div class="brand">
        <i class="el-icon-collection-tag icon"></i>
        <span class="brand-text">{{ $t("app.title") }}</span>
      </div>

      <div class="info">
        <span class="time">
          <i class="el-icon-time"></i>
          9:00-18:00
        </span>
        <el-select
          v-model="lang"
          size="mini"
          class="lang-select"
          @change="changeLang"
          popper-class="lang-popper"
        >
          <el-option label="中文" value="zh" />
          <el-option label="English" value="en" />
        </el-select>

        <!-- 用户下拉菜单 -->
        <el-dropdown v-if="username" @command="handleUserCommand" trigger="click">
          <span class="user-menu">
            <i class="el-icon-user-solid"></i>
            {{ username }}
            <span v-if="quotaLimit !== null" class="quota-badge">
              {{ $t('user.quotaBadge', { used: quotaUsed, limit: quotaLimit }) }}
            </span>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item command="quota">
              <i class="el-icon-pie-chart"></i> {{ $t('user.quotaDetail') }}
            </el-dropdown-item>
            <el-dropdown-item command="subscription">
              <i class="el-icon-bank-card"></i> {{ $t('user.subscription') }}
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <i class="el-icon-switch-button"></i> {{ $t('user.logout') }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>
    </div>

    <!-- 居中放大的标题 -->
    <div class="hero">
      <h1 class="hero-title">
        {{ $t("app.title") }}
      </h1>
      <p class="hero-sub" v-if="subtitle">
        {{ subtitle }}
      </p>
    </div>
  </header>
</template>

<script>
import { getLocale, setLocale } from "@/i18n";

export default {
  name: "Header",
  data() {
    return {
      lang: getLocale(),
      subtitle: "", // 可加副标题 key
      username: null,
      quotaUsed: 0,
      quotaLimit: null,
      allQuotas: [], // 存储所有配额信息
    };
  },
  mounted() {
    // 如果用户已登录，加载用户信息和配额
    const token = localStorage.getItem('access_token');
    if (token) {
      this.loadUserInfo();
      this.loadQuota();
    }

    // 监听配额更新事件
    this.$root.$on('quota-updated', () => {
      this.loadQuota();
    });

    // 监听用户登录事件
    this.$root.$on('user-logged-in', () => {
      this.loadUserInfo();
      this.loadQuota();
    });
  },
  beforeDestroy() {
    // 移除事件监听
    this.$root.$off('quota-updated');
    this.$root.$off('user-logged-in');
  },
  methods: {
    changeLang(v) {
      setLocale(v);
    },
    async loadUserInfo() {
      try {
        const response = await this.$http.get('http://localhost:9001/users/me');
        this.username = response.data.username;
      } catch (error) {
        console.error('Failed to load user info:', error);
        // 如果获取用户信息失败（token 可能过期），清除登录状态
        if (error.response && error.response.status === 401) {
          localStorage.removeItem('access_token');
          this.$router.push('/login');
        }
      }
    },
    async loadQuota() {
      try {
        const response = await this.$http.get('http://localhost:4200/admin/quotas/users/me');

        // 存储所有配额信息
        this.allQuotas = response.data.quotas || [];

        // 主配额用于徽章显示
        const quota = response.data.quotas.find(q => q.type_key === 'api_calls_full_process');
        if (quota) {
          this.quotaUsed = quota.used;
          this.quotaLimit = quota.limit;
        }
      } catch (error) {
        console.error('Failed to load quota:', error);
      }
    },
    handleUserCommand(command) {
      switch (command) {
        case 'quota':
          // 显示所有配额详情
          if (this.allQuotas.length === 0) {
            this.$message.warning(this.$t('quota.checkFailed'));
            return;
          }

          // 构建配额详情消息（按类别分组）
          let message = '<div style="text-align: left; font-size: 13px; line-height: 1.8;">';

          // API 调用配额
          const apiQuotas = this.allQuotas.filter(q => q.type_key.startsWith('api_calls_'));
          if (apiQuotas.length > 0) {
            message += '<div style="font-weight: 600; margin-bottom: 8px; color: #0a84ff;">📊 API 配额</div>';
            apiQuotas.forEach(q => {
              const percent = q.usage_percent || 0;
              const color = percent > 80 ? '#f56c6c' : percent > 50 ? '#e6a23c' : '#67c23a';
              message += `<div style="margin-bottom: 6px;">`;
              message += `  <span style="color: #606266;">${q.name}:</span> `;
              message += `  <span style="font-weight: 600; color: ${color};">${q.used}/${q.limit}</span> `;
              message += `  <span style="color: #909399; font-size: 11px;">${q.unit}</span>`;
              message += `</div>`;
            });
          }

          // 存储配额
          const storageQuotas = this.allQuotas.filter(q => q.type_key.startsWith('storage_'));
          if (storageQuotas.length > 0) {
            message += '<div style="font-weight: 600; margin: 12px 0 8px; color: #0a84ff;">💾 存储配额</div>';
            storageQuotas.forEach(q => {
              const percent = q.usage_percent || 0;
              const color = percent > 80 ? '#f56c6c' : percent > 50 ? '#e6a23c' : '#67c23a';
              message += `<div style="margin-bottom: 6px;">`;
              message += `  <span style="color: #606266;">${q.name}:</span> `;
              message += `  <span style="font-weight: 600; color: ${color};">${q.used.toFixed(2)}/${q.limit}</span> `;
              message += `  <span style="color: #909399; font-size: 11px;">${q.unit}</span>`;
              message += `  <span style="color: #909399; font-size: 11px;">(${percent.toFixed(1)}%)</span>`;
              message += `</div>`;
            });
          }

          // 其他配额
          const otherQuotas = this.allQuotas.filter(q =>
            !q.type_key.startsWith('api_calls_') && !q.type_key.startsWith('storage_')
          );
          if (otherQuotas.length > 0) {
            message += '<div style="font-weight: 600; margin: 12px 0 8px; color: #0a84ff;">📦 其他配额</div>';
            otherQuotas.forEach(q => {
              const percent = q.usage_percent || 0;
              const color = percent > 80 ? '#f56c6c' : percent > 50 ? '#e6a23c' : '#67c23a';
              message += `<div style="margin-bottom: 6px;">`;
              message += `  <span style="color: #606266;">${q.name}:</span> `;
              message += `  <span style="font-weight: 600; color: ${color};">${q.used}/${q.limit}</span> `;
              message += `  <span style="color: #909399; font-size: 11px;">${q.unit}</span>`;
              message += `</div>`;
            });
          }

          message += '</div>';

          this.$alert(
            message,
            this.$t('user.quotaDetail'),
            {
              confirmButtonText: 'OK',
              dangerouslyUseHTMLString: true,
              customClass: 'quota-detail-dialog'
            }
          );
          break;
        case 'subscription':
          // 跳转到商业前端的订阅管理页面
          const token = localStorage.getItem('access_token');
          const commercialUrl = process.env.VUE_APP_COMMERCIAL_URL || 'http://localhost:3000';
          // 使用 Browser Router 格式（不使用 hash）
          window.location.href = `${commercialUrl}/subscription?token=${token}`;
          break;
        case 'logout':
          // 退出登录
          this.$confirm(
            this.$t('确定要退出登录吗？'),
            this.$t('提示'),
            {
              confirmButtonText: this.$t('确定'),
              cancelButtonText: this.$t('取消'),
              type: 'warning'
            }
          ).then(() => {
            localStorage.removeItem('access_token');
            this.username = null;
            this.quotaUsed = 0;
            this.quotaLimit = null;
            this.$message.success(this.$t('已退出登录'));
            this.$router.push('/login');
          }).catch(() => {});
          break;
      }
    },
    // 提供一个公共方法供其他组件调用以刷新配额
    refreshQuota() {
      this.loadQuota();
    }
  },
};
</script>

<style scoped>
/* 布局 */
#Header {
  position: relative;
  width: 100%;
  padding: 14px 40px 42px;
  box-sizing: border-box;
  overflow: hidden;
}

/* 背景柔和弧形 */
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
  -webkit-mask: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.9),
    rgba(0, 0, 0, 0)
  );
  mask: linear-gradient(to bottom, rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0));
  pointer-events: none;
  z-index: 0;
}

/* 顶部条 */
.bar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  padding: 6px 20px;
  backdrop-filter: saturate(160%) blur(14px);
  -webkit-backdrop-filter: saturate(160%) blur(14px);
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 18px;
  box-shadow: 0 6px 24px -8px rgba(0, 0, 0, 0.1);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 18px;
  letter-spacing: 0.5px;
  color: #0a84ff;
}

.brand .icon {
  font-size: 22px;
  color: #0a84ff;
}

.info {
  display: flex;
  align-items: center;
  gap: 22px;
  font-size: 14px;
  color: #46515f;
}

.time i {
  margin-right: 4px;
  font-size: 16px;
  color: #0a84ff;
}

/* 中心主标题块 */
.hero {
  position: relative;
  z-index: 1;
  margin-top: 34px;
  text-align: center;
  padding: 8px 16px 12px;
}

.hero-title {
  margin: 0;
  font-size: clamp(34px, 5.2vw, 56px);
  line-height: 1.08;
  font-weight: 700;
  letter-spacing: 0.02em;
  background: linear-gradient(100deg, #0a84ff 0%, #0a6dff 45%, #005ac8 100%);
  -webkit-background-clip: text;
  color: transparent;
  filter: drop-shadow(0 4px 14px rgba(10, 132, 255, 0.25));
}

.hero-sub {
  margin: 10px 0 0;
  font-size: 15px;
  color: #51606f;
  letter-spacing: 0.5px;
}

/* 语言选择器 */
.lang-select ::v-deep .el-input__inner {
  border-radius: 999px;
  padding: 0 14px;
  height: 32px;
  line-height: 32px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(0, 0, 0, 0.08);
  transition: background 0.2s, border-color 0.2s;
}
.lang-select ::v-deep .el-input__inner:hover {
  background: #ffffff;
}

/* 用户菜单 */
.user-menu {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  color: #0a84ff;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, box-shadow 0.2s;
}
.user-menu:hover {
  background: #ffffff;
  border-color: rgba(10, 132, 255, 0.3);
  box-shadow: 0 2px 8px rgba(10, 132, 255, 0.15);
}
.user-menu i {
  font-size: 14px;
}

/* 配额徽章 */
.quota-badge {
  display: inline-block;
  padding: 2px 8px;
  background: linear-gradient(135deg, #0a84ff 0%, #0067d1 100%);
  color: #ffffff;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  margin-left: 2px;
}

/* 响应式 */
@media (max-width: 900px) {
  #Header {
    padding: 12px 18px 40px;
  }
  .bar {
    flex-wrap: wrap;
    gap: 14px;
  }
  .hero-title {
    font-size: clamp(32px, 9vw, 50px);
  }
}

/* 配额详情对话框样式 */
::v-deep .quota-detail-dialog {
  width: 480px;
  max-width: 90vw;
}
::v-deep .quota-detail-dialog .el-message-box__message {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 10px;
}
::v-deep .quota-detail-dialog .el-message-box__message::-webkit-scrollbar {
  width: 6px;
}
::v-deep .quota-detail-dialog .el-message-box__message::-webkit-scrollbar-thumb {
  background: rgba(10, 132, 255, 0.3);
  border-radius: 3px;
}
::v-deep .quota-detail-dialog .el-message-box__message::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
}

/* 深色模式 */
@media (prefers-color-scheme: dark) {
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
  .bar {
    background: rgba(30, 40, 52, 0.55);
    border-color: rgba(255, 255, 255, 0.08);
    box-shadow: 0 6px 28px -10px rgba(0, 0, 0, 0.6);
  }
  .info {
    color: #b7c3d1;
  }
  .hero-sub {
    color: #8fa2b4;
  }
  .lang-select ::v-deep .el-input__inner {
    background: rgba(55, 65, 78, 0.55);
    color: #e6f1ff;
    border-color: rgba(255, 255, 255, 0.15);
  }
}
</style>