<template>
  <div id="Content">
    <!-- 左侧步骤栏 -->
    <aside class="flow-aside">
      <el-steps
        direction="vertical"
        :active="currentStep"
        finish-status="success"
      >
        <el-step :title="$t('steps.step1')">
          <template #description>
            <el-button
              type="primary"
              size="mini"
              :loading="uploading"
              @click="triggerUpload"
            >
              {{ $t("actions.chooseFile") }}
            </el-button>
            <input
              ref="fileInput"
              type="file"
              accept=".zip"
              style="display: none"
              @change="handleFile"
            />
            <p v-if="fileName" class="hint">
              {{ $t("upload.selectedPrefix") }} {{ fileName }}
            </p>
          </template>
        </el-step>
        <el-step :title="$t('steps.step2')" :disabled="currentStep < 2">
          <template #description>
            <p v-if="currentStep === 1" class="muted">
              {{ $t("messages.waitUpload") }}
            </p>
            <p v-else>{{ $t("messages.clickProcessHint") }}</p>
          </template>
        </el-step>
        <el-step :title="$t('steps.step3')" :disabled="currentStep < 3">
          <template #description>
            <p v-if="currentStep < 3" class="muted">
              {{ $t("messages.waitProcess") }}
            </p>
            <p v-else>{{ $t("messages.enterResultHint") }}</p>
          </template>
        </el-step>
      </el-steps>
    </aside>

    <!-- 右侧主区 -->
    <section class="flow-main">
      <!-- Step 1 -->
      <div v-if="currentStep === 1" class="panel">
        <h3>{{ $t("upload.uploadZipTitle") }}</h3>
        <el-form label-width="100px" :model="form">
          <el-form-item :label="$t('form.patientName')">
            <el-input
              v-model="form.patient_name"
              :placeholder="$t('form.patientNamePlaceholder')"
              clearable
            />
          </el-form-item>
          <el-form-item :label="$t('form.studyDate')">
            <el-input
              v-model="form.study_date"
              :placeholder="$t('form.studyDatePlaceholder')"
              clearable
            />
          </el-form-item>
          <el-form-item :label="$t('form.zipFile')">
            <el-button @click="triggerUpload" :loading="uploading">
              {{ $t("actions.chooseFile") }}
            </el-button>
            <span v-if="fileName" style="margin-left: 8px">{{ fileName }}</span>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :disabled="!canUpload"
              :loading="uploading"
              @click="uploadZip"
            >
              {{ $t("actions.upload") }}
            </el-button>
            <el-button type="text" @click="goResultList">
              {{ $t("actions.viewAll") }}
            </el-button>
          </el-form-item>
          <el-form-item v-if="uploading" label=" " label-width="100px">
            <div
              style="
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
              "
            >
              <el-progress
                :percentage="Math.min(uploadPercent, 100)"
                :status="uploadPercent === 100 ? 'success' : undefined"
                style="width: 300px"
              />
              <span style="font-size: 12px; color: #666"
                >{{ $t("messages.waitUpload") }}
                {{ Math.min(uploadPercent, 100) }}%</span
              >
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 2 -->
      <!-- Step 2 -->
      <div v-else-if="currentStep === 2" class="panel">
        <div class="panel-header">
          <h3>{{ $t("labels.processData") }}</h3>
        </div>
        <el-alert
          :title="$t('messages.processApiTip')"
          type="info"
          show-icon
          style="margin-bottom: 16px"
        />

        <!-- 添加进度条 -->
        <el-progress
          v-if="processing"
          :percentage="progress"
          :status="progress === 100 ? 'success' : undefined"
          style="margin-bottom: 16px"
        />
        <p
          v-if="processing"
          style="font-size: 12px; color: #666; margin-bottom: 16px"
        >
          {{ progressMessage }}
        </p>

        <el-button type="primary" :loading="processing" @click="processData">
          {{ $t("actions.process") }}
        </el-button>
        <el-button type="text" style="margin-left: 8px" @click="backToUpload">
          {{ $t("actions.prevStep") }}
        </el-button>
      </div>

      <!-- Step 3 -->
      <div v-else-if="currentStep === 3" class="panel">
        <div class="panel-header">
          <h3>{{ $t("messages.processSuccess") }}</h3>
        </div>
        <el-result icon="success" :title="$t('messages.processSuccess')">
          <template #extra>
            <el-button type="primary" @click="goResultDetail">
              {{ $t("actions.viewResult") }}
            </el-button>
            <el-button @click="goResultList" style="margin-left: 8px">
              {{ $t("actions.viewAll") }}
            </el-button>
            <el-button
              type="text"
              style="margin-left: 8px"
              @click="backToProcess"
            >
              {{ $t("actions.prevStep") }}
            </el-button>
          </template>
        </el-result>
      </div>

      <el-empty v-else :description="$t('messages.noContent')" />
    </section>
  </div>
</template>

<script>
import { uploadDicomZip, processCase, getTaskStatus } from "@/api";

function todayYMD() {
  const d = new Date();
  const pad = (n) => (n < 10 ? "0" + n : "" + n);
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
}

export default {
  name: "Content",
  data() {
    return {
      currentStep: 1,
      uploading: false,
      processing: false,
      fileObj: null,
      fileName: "",
      form: {
        patient_name: "",
        study_date: todayYMD(),
      },
      // 处理后台异步任务的轮询
      taskId: null,
      pollTimer: null,
      progress: 0,
      progressMessage: "",
      // 前端计算的上传进度
      uploadPercent: 0,
    };
  },
  beforeDestroy() {
    if (this.pollTimer) clearInterval(this.pollTimer);
  },
  computed: {
    canUpload() {
      return !!(this.form.patient_name && this.form.study_date && this.fileObj);
    },
  },
  methods: {
    debug(err) {
      if (process.env.NODE_ENV !== "production") {
        /* eslint-disable-next-line no-console */
        console.error(err);
      }
    },
    triggerUpload() {
      this.$refs.fileInput && this.$refs.fileInput.click();
    },
    handleFile(e) {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      this.fileObj = f;
      this.fileName = f.name;
      this.$nextTick(() => (this.$refs.fileInput.value = ""));
    },
    async uploadZip() {
      if (!this.canUpload || this.uploading) return;

      // 1. 检查配额
      const hasQuota = await this.checkQuota();
      if (!hasQuota) {
        return; // 配额不足，已在 checkQuota 中显示提示
      }

      this.uploading = true;
      this.uploadPercent = 0;
      try {
        const res = await uploadDicomZip({
          patient_name: this.form.patient_name,
          study_date: this.form.study_date,
          file: this.fileObj,
          onProgress: (percent /*, loaded, total */) => {
            // 请求未完成前显示真实进度，接口返回后会再设为 100
            this.uploadPercent = percent < 100 ? percent : 99;
          },
        });
        this.uploadPercent = 100;
        this.$message.success(this.$t("messages.uploadSuccess"));
        this.currentStep = 2;
      } catch (e) {
        this.debug(e);
        this.$message.error(this.$t("messages.uploadFail"));
        this.uploadPercent = 0;
      } finally {
        this.uploading = false;
      }
    },
    async checkQuota() {
      try {
        const response = await this.$http.get('http://localhost:4200/admin/quotas/users/me');
        const quota = response.data.quotas.find(q => q.type_key === 'api_calls_full_process');

        if (!quota) {
          this.$message.error(this.$t('quota.checkFailed'));
          return false;
        }

        const available = quota.limit - quota.used;
        if (available <= 0) {
          // 配额耗尽
          await this.$confirm(
            this.$t('quota.insufficientMessage'),
            this.$t('quota.insufficient'),
            {
              confirmButtonText: this.$t('quota.upgradeNow'),
              cancelButtonText: this.$t('quota.cancel'),
              type: 'warning'
            }
          ).then(() => {
            // 跳转到商业前端订阅页面
            const token = localStorage.getItem('access_token');
            window.location.href = `http://localhost:3000/#/subscription?token=${token}`;
          }).catch(() => {
            // 用户取消，不做任何操作
          });
          return false;
        }

        return true;
      } catch (error) {
        console.error('Failed to check quota:', error);
        this.$message.error(this.$t('quota.checkFailed'));
        return false;
      }
    },
    async processData() {
      this.processing = true;
      this.progress = 0;
      this.progressMessage = this.$t("messages.waitProcess");
      try {
        const res = await processCase(
          this.form.patient_name,
          this.form.study_date
        );
        if (res && res.data && res.data.task_id) {
          this.taskId = res.data.task_id;
          this.startPolling();
        } else {
          this.$message.success(this.$t("messages.processSuccess"));
          this.currentStep = 3;
          this.processing = false;
        }
      } catch (e) {
        this.debug(e);
        // 处理 409 冲突错误（任务已提交或僵尸任务）
        if (e.response && e.response.status === 409) {
          const msg =
            (e.response.data && e.response.data.detail) ||
            this.$t("messages.processFail");
          this.$message.warning(msg);
        } else {
          this.$message.error(this.$t("messages.processFail"));
        }
        this.processing = false;
      }
    },
    startPolling() {
      if (this.pollTimer) clearInterval(this.pollTimer);
      this.pollTimer = setInterval(async () => {
        try {
          const res = await getTaskStatus(this.taskId);
          const status = res.data;
          this.progress = status.progress || 0;
          this.progressMessage = status.message || "";

          // 利用新增的时间戳字段显示运行时长
          if (status.started_at && status.status === "processing") {
            const elapsed = Math.floor(Date.now() / 1000 - status.started_at);
            this.progressMessage += ` (已运行 ${elapsed}秒)`;

            // 超过 5 分钟提示可能卡死
            if (elapsed > 300) {
              this.progressMessage += " - 任务运行时间过长，可能已卡死";
            }
          }

          if (status.status === "completed") {
            clearInterval(this.pollTimer);
            const duration = status.duration
              ? `耗时 ${Math.round(status.duration)}秒`
              : "";
            this.$message.success(
              this.$t("messages.processSuccess") +
                (duration ? ` (${duration})` : "")
            );
            this.currentStep = 3;
            this.processing = false;
            // 处理成功后刷新配额显示
            this.$root.$emit('quota-updated');
          } else if (status.status === "failed") {
            clearInterval(this.pollTimer);
            const errMsg = status.error ? `: ${status.error}` : "";
            this.$message.error(this.$t("messages.processFail") + errMsg);
            this.processing = false;
          }
        } catch (e) {
          this.debug(e);
          clearInterval(this.pollTimer);
          this.$message.error(this.$t("messages.processFail"));
          this.processing = false;
        }
      }, 3000);
    },
    goResultDetail() {
      this.$router.push(
        `/results/${this.form.patient_name}/${this.form.study_date}`
      );
    },
    goResultList() {
      this.$router.push("/results");
    },
    backToUpload() {
      this.currentStep = 1;
    },
    backToProcess() {
      this.currentStep = 2;
    },
  },
};
</script>


<style scoped>
#Content {
  width: 88%;
  max-width: 1400px;
  margin: 32px auto 80px;
  display: flex;
  gap: 48px;
  align-items: flex-start;
}
.flow-aside {
  width: 300px;
  background: #f8fafc;
  padding: 28px 20px 12px;
  border-radius: 18px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 24px;
  height: fit-content;
}
.flow-main {
  flex: 1;
  min-height: 560px;
}
.panel {
  background: #fff;
  border-radius: 18px;
  padding: 28px 32px 40px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.06);
}
.upload-box {
  border: 2px dashed #b9e6ea;
  border-radius: 16px;
  text-align: center;
  padding: 90px 40px;
  cursor: pointer;
  transition: border-color 0.25s, background 0.25s;
  background: #fafdfe;
}
.upload-box:hover {
  border-color: #21b3b9;
  background: #f2fbfc;
}
.upload-box i {
  font-size: 48px;
  color: #21b3b9;
  margin-bottom: 12px;
  display: block;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 18px;
}
.grid-item {
  position: relative;
  border: 2px solid transparent;
  background: #ffffff;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s;
}
.grid-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
}
.grid-item.active {
  border-color: #21b3b9;
  box-shadow: 0 0 0 3px rgba(33, 179, 185, 0.25);
}
.grid-item .el-image {
  width: 100%;
  height: 140px;
  display: block;
}
.meta {
  padding: 6px 10px 10px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #3b5560;
}
.meta .conf {
  color: #21b3b9;
  font-weight: 500;
}
.result-layout {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}
.result-images,
.result-metrics {
  background: #f9fcfd;
  border-radius: 16px;
  padding: 20px 24px 28px;
  flex: 1 1 420px;
  min-width: 380px;
}
.result-images h4,
.result-metrics h4 {
  margin: 0 0 12px;
}
.result-img {
  width: 100%;
  height: 280px;
  border-radius: 12px;
  background: #fff;
  margin-bottom: 18px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
.hint {
  margin-top: 6px;
  font-size: 12px;
  color: #21b3b9;
}
.muted {
  font-size: 12px;
  color: #98a6ad;
}
.diagnosis {
  margin-top: 20px;
}
</style>


<style>
:root {
  --accent: #0a84ff; /* System Blue */
  --accent-press: #0067d1;
  --bg-1: #f7f9fc;
  --bg-2: #eef2f6;
  --text: #0b1a2b;
  --glass: rgba(255, 255, 255, 0.6);
  --glass-border: rgba(255, 255, 255, 0.38);
  --radius-lg: 18px;
  --radius-md: 14px;
}
html,
body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
    "Helvetica Neue", Arial, "PingFang SC", "Noto Sans SC", "Microsoft YaHei",
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--text);
}
body {
  background: radial-gradient(
      1200px 420px at 50% -260px,
      rgba(10, 132, 255, 0.18) 0%,
      transparent 60%
    ),
    linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 100%);
  margin: 0;
  min-height: 100vh;
}
#app {
  min-height: 100vh;
}

/* 胶囊主按钮（ElementUI） */
.el-button--primary {
  background: var(--accent);
  border-color: transparent;
  color: #fff;
  border-radius: 999px;
  padding: 10px 18px;
  box-shadow: 0 6px 16px rgba(10, 132, 255, 0.25);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.2s ease;
}
.el-button--primary:hover {
  box-shadow: 0 10px 24px rgba(10, 132, 255, 0.35);
}
.el-button--primary:active {
  background: var(--accent-press);
  transform: translateY(1px) scale(0.99);
}

/* Steps 主色同步 */
.el-steps .el-step__head.is-process,
.el-steps .el-step__head.is-success {
  border-color: var(--accent);
  color: var(--accent);
}
.el-steps .el-step__line {
  background: rgba(10, 132, 255, 0.15);
}
.el-steps .el-step__line-inner {
  background: var(--accent) !important;
}

/* 暗色模式 */
@media (prefers-color-scheme: dark) {
  :root {
    --bg-1: #0f1220;
    --bg-2: #0a0d19;
    --text: #e8ebf0;
    --glass: rgba(22, 24, 32, 0.55);
    --glass-border: rgba(255, 255, 255, 0.14);
  }
  body {
    background: radial-gradient(
        1200px 420px at 50% -260px,
        rgba(10, 132, 255, 0.22) 0%,
        transparent 60%
      ),
      linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
    animation: none !important;
  }
}
</style>

<style scoped>
#Content {
  width: clamp(960px, 86vw, 1140px);
  margin: 32px auto 80px;
  display: flex;
  gap: 48px;
  align-items: flex-start;
}

/* 玻璃化侧栏与卡片 */
.flow-aside,
.panel,
.result-images,
.result-metrics {
  background: var(--glass);
  -webkit-backdrop-filter: saturate(180%) blur(18px);
  backdrop-filter: saturate(180%) blur(18px);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 26px rgba(16, 38, 73, 0.08),
    0 1px 0 rgba(255, 255, 255, 0.6) inset;
}
.flow-aside {
  width: 300px;
  padding: 28px 20px 12px;
  position: sticky;
  top: 24px;
  height: fit-content;
}
.panel {
  padding: 28px 32px 40px;
}

/* 上传框：更轻的胶囊风 */
.upload-box {
  border: 1.5px dashed rgba(10, 132, 255, 0.35);
  background: rgba(255, 255, 255, 0.55);
  border-radius: 16px;
  text-align: center;
  padding: 90px 40px;
  cursor: pointer;
  transition: border-color 0.25s, background 0.25s, transform 0.2s;
}
.upload-box:hover {
  border-color: var(--accent);
  background: rgba(255, 255, 255, 0.7);
  transform: translateY(-2px);
}
.upload-box i {
  font-size: 48px;
  color: var(--accent);
  margin-bottom: 12px;
  display: block;
}

/* 网格卡片微动效 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 18px;
}
.grid-item {
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.65);
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  transition: transform 0.22s, box-shadow 0.22s, border-color 0.22s;
}
.grid-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.1);
}
.grid-item.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(10, 132, 255, 0.22);
}
.grid-item .el-image {
  width: 100%;
  height: 140px;
  display: block;
}

/* 结果区图片与表格 */
.result-layout {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}
.result-img {
  width: 100%;
  height: 280px;
  border-radius: 12px;
  background: #fff;
  margin-bottom: 18px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
.result-metrics .el-table {
  background: transparent;
}
.result-metrics .el-table th,
.result-metrics .el-table td {
  background: transparent;
}

/* 微文案颜色 */
.hint {
  margin-top: 6px;
  font-size: 12px;
  color: #222; /* 深色 */
}
.muted {
  font-size: 12px;
  color: #98a6ad;
}

/* 标题行 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>

<style scoped>
#Footer {
  width: clamp(960px, 86vw, 1140px);
  margin: 24px auto 60px;
  height: 72px;
  background: var(--glass);
  -webkit-backdrop-filter: saturate(180%) blur(18px);
  backdrop-filter: saturate(180%) blur(18px);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
p {
  color: var(--text);
  margin: 0;
  opacity: 0.9;
}
</style>