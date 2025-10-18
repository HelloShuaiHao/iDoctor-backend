<template>
  <div class="detail">
    <div class="head">
      <el-button
        class="back-btn"
        icon="el-icon-arrow-left"
        @click="goBack"
        plain
        >{{ $t("actions.back") }}</el-button
      >

      <div class="case-title">
        <h1>
          <span class="pid">{{ patient }}</span>
          <span class="sep">•</span>
          <span class="date">{{ date }}</span>
        </h1>
      </div>

      <!-- 预留右侧操作位（可加刷新 / 导出） -->
      <div class="head-actions">
        <!-- <el-button size="mini" @click="fetchResults" :loading="loading" plain>Refresh</el-button> -->
      </div>
    </div>

    <section class="card" v-loading="loading">
      <div class="card-title">{{ $t("result.keyMetrics") }}</div>

      <div v-if="summary" class="summary">
        <div class="pill">
          <span class="k">{{ $t("fields.psoasHu") }}</span>
          <span class="v">{{ fmt(summary.psoas_hu_mean) }}</span>
        </div>
        <div class="pill">
          <span class="k">{{ $t("fields.psoasArea") }}</span>
          <span class="v">{{ fmt(summary.psoas_area_mm2) }}</span>
        </div>
        <div class="pill">
          <span class="k">{{ $t("fields.comboHu") }}</span>
          <span class="v">{{ fmt(summary.combo_hu_mean) }}</span>
        </div>
        <div class="pill">
          <span class="k">{{ $t("fields.comboArea") }}</span>
          <span class="v">{{ fmt(summary.combo_area_mm2) }}</span>
        </div>
      </div>

      <el-table
        v-if="rows.length"
        :data="rows"
        border
        size="small"
        style="width: 100%; margin-top: 10px"
      >
        <el-table-column
          prop="filename"
          :label="$t('fields.slice')"
          width="160"
        />
        <el-table-column
          prop="psoas_hu_mean"
          :label="$t('fields.psoasHu')"
          :formatter="fmtCell"
        />
        <el-table-column
          prop="psoas_area_mm2"
          :label="$t('fields.psoasArea')"
          :formatter="fmtCell"
        />
        <el-table-column
          prop="combo_hu_mean"
          :label="$t('fields.comboHu')"
          :formatter="fmtCell"
        />
        <el-table-column
          prop="combo_area_mm2"
          :label="$t('fields.comboArea')"
          :formatter="fmtCell"
        />
      </el-table>

      <el-empty v-else :description="$t('result.emptyMetrics')" />
    </section>

    <section class="card">
      <div class="card-title">{{ $t("result.keyImages") }}</div>
      <div class="img-grid">
        <div v-for="img in middle_images" :key="img" class="img-item">
          <el-image
            :src="imageUrl(img)"
            fit="cover"
            :preview-src-list="previewList"
          />
          <div class="caption">{{ img }}</div>
        </div>
      </div>
      <div class="mid-ops" v-if="axisalMainName">
        <el-button
          size="mini"
          @click="openMiddleEditor"
          style="margin-top: 14px"
        >
          {{ $t("actions.manualMiddleMask") }}
        </el-button>
      </div>
    </section>

    <section class="card" style="margin-bottom: 18px">
      <div class="card-title">{{ $t("result.l3Ops") }}</div>
      <el-button type="primary" :loading="l3Detecting" @click="handleL3Detect">
        {{ $t("actions.detectL3") }}
      </el-button>

      <el-button style="margin-left: 12px" @click="openMaskEditor">
        {{ $t("actions.manualL3") }}
      </el-button>

      <el-button
        type="success"
        :loading="l3Continuing"
        style="margin-left: 12px"
        @click="handleContinueAfterL3"
      >
        {{ $t("actions.continue") }}
      </el-button>

      <!-- 添加进度条 -->
      <div v-if="l3Continuing" style="margin-top: 16px">
        <el-progress
          :percentage="l3Progress"
          :status="l3Progress === 100 ? 'success' : undefined"
        />
        <p style="font-size: 12px; color: #666; margin-top: 8px">
          {{ l3ProgressMessage }}
        </p>
      </div>

      <div v-if="l3ImageUrl" class="l3-preview">
        <img :src="l3ImageUrl" class="l3-preview-img" />
        <div class="l3-preview-tip">
          {{ $t("result.l3Preview") }}
        </div>
      </div>
    </section>
    <middle-mask-editor
      v-if="axisalMainName"
      :axisal-filename="axisalMainName"
      :patient="patient"
      :date="date"
      :visible.sync="middleEditorVisible"
      @uploaded="onMiddleUploaded"
    />
    <l3-mask-editor
      :patient="patient"
      :date="date"
      :visible.sync="maskEditorVisible"
      @uploaded="onMaskUploaded"
    />
  </div>
</template>

<script>
import {
  getKeyResults,
  getImageUrl,
  l3Detect,
  uploadL3Mask,
  continueAfterL3,
  getL3ImageUrl,
  getTaskStatus,
} from "@/api";
import L3MaskEditor from "./L3MaskEditor.vue";
import MiddleMaskEditor from "./MiddleMaskEditor.vue";

export default {
  name: "ResultDetail",
  components: { L3MaskEditor, MiddleMaskEditor },
  data() {
    return {
      loading: true,
      csv_files: {},
      middle_images: [],
      rows: [],
      summary: null,
      previewList: [],
      l3Detecting: false,
      l3Continuing: false,
      l3ImageUrl: "",
      maskEditorVisible: false,
      middleEditorVisible: false,
      middleMainName: "", // slice_xxx_middle.png
      axisalMainName: "", // slice_xxx.png (用于原图标注)
      l3TaskId: null,
      l3PollTimer: null,
      l3Progress: 0,
      l3ProgressMessage: "",
    };
  },
  beforeDestroy() {
    // 组件销毁时清除定时器
    if (this.l3PollTimer) {
      clearInterval(this.l3PollTimer);
    }
  },
  computed: {
    patient() {
      return this.$route.params.patient;
    },
    date() {
      return this.$route.params.date;
    },
  },
  async created() {
    await this.fetchResults();
  },
  methods: {
    async fetchResults() {
      this.loading = true;
      try {
        const res = await getKeyResults(this.patient, this.date);
        const data = (res && res.data) || {};
        this.csv_files = data.csv_files || {};
        this.middle_images = data.middle_images || [];
        this.previewList = this.middle_images.map((n) => this.imageUrl(n));
        const keys = Object.keys(this.csv_files || {});
        const csvName = keys.find((n) => /middle[_-]?only/i.test(n)) || keys[0];
        if (csvName) {
          this.rows = this.extractKeyRows(this.csv_files[csvName]);
          this.summary = this.makeSummary(this.rows);
          // middle 主图名称：取第一行 filename (含 _middle.png)
          if (this.rows.length) {
            this.middleMainName = this.rows[0].filename;
          } else if (this.middle_images.length) {
            this.middleMainName = this.middle_images[0];
          }
        } else {
          this.rows = [];
          this.summary = null;
          this.middleMainName = this.middle_images[0] || "";
        }
        // 推导 axisal 原图名
        this.axisalMainName = this.middleMainName
          ? this.middleMainName.replace("_middle.png", ".png")
          : "";
      } catch (e) {
        this.$message.error(this.$t("messages.fetchFail"));
      } finally {
        this.loading = false;
      }
    },
    openMiddleEditor() {
      this.middleEditorVisible = true;
    },
    onMiddleUploaded() {
      // 重新取最新 middle 相关数据
      this.fetchResults();
    },
    openMaskEditor() {
      this.maskEditorVisible = true;
    },
    onMaskUploaded(payload) {
      if (payload && payload.overlay) {
        this.setL3Overlay(payload.overlay);
      } else {
        this.$message.success(this.$t("messages.maskUploadSuccess"));
        this.loadL3Image();
      }
    },
    extractKeyRows(csvText) {
      if (!csvText) return [];
      const lines = csvText.trim().split(/\r?\n/).filter(Boolean);
      if (lines.length < 2) return [];
      const headers = lines[0].split(",").map((h) => h.trim());
      const idx = (name) =>
        headers.findIndex((h) => h.toLowerCase() === name.toLowerCase());
      const keyCols = {
        filename: "filename",
        psoas_hu_mean: "psoas_hu_mean",
        psoas_area_mm2: "psoas_area_mm2",
        combo_hu_mean: "combo_hu_mean",
        combo_area_mm2: "combo_area_mm2",
      };
      const col = {};
      for (const k in keyCols) col[k] = idx(keyCols[k]);
      return lines
        .slice(1)
        .map((line) => {
          const cells = line.split(",").map((c) => c.trim());
          const get = (i) => (i >= 0 && i < cells.length ? cells[i] : "");
          const num = (v) => (v === "" ? null : Number(v));
          return {
            filename: get(col.filename),
            psoas_hu_mean: num(get(col.psoas_hu_mean)),
            psoas_area_mm2: num(get(col.psoas_area_mm2)),
            combo_hu_mean: num(get(col.combo_hu_mean)),
            combo_area_mm2: num(get(col.combo_area_mm2)),
          };
        })
        .filter((r) => r.filename);
    },
    makeSummary(rows) {
      if (!rows.length) return null;
      const keys = [
        "psoas_hu_mean",
        "psoas_area_mm2",
        "combo_hu_mean",
        "combo_area_mm2",
      ];
      const s = {};
      for (const k of keys) {
        const vals = rows
          .map((r) => r[k])
          .filter((v) => typeof v === "number" && !Number.isNaN(v));
        s[k] = vals.length
          ? vals.reduce((a, b) => a + b, 0) / vals.length
          : null;
      }
      return s;
    },
    imageUrl(filename) {
      return getImageUrl(this.patient, this.date, filename);
    },
    fmt(n) {
      return n == null || Number.isNaN(n) ? "-" : Number(n).toFixed(2);
    },
    fmtCell(row, col, cellValue) {
      return this.fmt(cellValue);
    },
    goBack() {
      if (window.history.length > 1) this.$router.back();
      else this.$router.push("/results");
    },
    goList() {
      if (this.$route.path !== "/results") this.$router.push("/results");
    },
    async handleL3Detect() {
      this.l3Detecting = true;
      try {
        const res = await l3Detect(this.patient, this.date);
        this.$message.success(this.$t("messages.l3DetectSuccess"));
        if (res && res.data && res.data.l3_overlay) {
          this.setL3Overlay(res.data.l3_overlay);
        } else {
          this.loadL3Image();
        }
      } catch (e) {
        this.$message.error(this.$t("messages.l3DetectFail"));
      } finally {
        this.l3Detecting = false;
      }
    },
    beforeMaskUpload(file) {
      if (!file.name.endsWith(".png")) {
        this.$message.error(this.$t("messages.pngOnly"));
        return false;
      }
      return true;
    },
    async customMaskUpload({ file, onSuccess, onError }) {
      try {
        await uploadL3Mask(this.patient, this.date, file);
        this.$message.success(this.$t("messages.maskUploadSuccess"));
        this.loadL3Image();
        onSuccess();
      } catch (e) {
        this.$message.error(this.$t("messages.maskUploadFail"));
        onError(e);
      }
    },
    onMaskUploadSuccess() {},
    async handleContinueAfterL3() {
      this.l3Continuing = true;
      this.l3Progress = 0;
      this.l3ProgressMessage = this.$t("messages.waitProcess");

      try {
        // 1. 提交任务
        const res = await continueAfterL3(this.patient, this.date);

        if (res && res.data && res.data.task_id) {
          this.l3TaskId = res.data.task_id;
          this.$message.success(
            res.data.message || this.$t("messages.uploadSuccess")
          );

          // 2. 开始轮询任务状态
          this.startL3Polling();
        } else {
          // 向后兼容：同步处理
          this.$message.success(this.$t("messages.l3ContinueSuccess"));
          if (res && res.data && res.data.l3_overlay) {
            this.setL3Overlay(res.data.l3_overlay);
          } else {
            this.loadL3Image();
          }
          await this.fetchResults();
          this.l3Continuing = false;
        }
      } catch (e) {
        // 处理 409 冲突错误（任务已提交或僵尸任务）
        if (e.response && e.response.status === 409) {
          const msg =
            (e.response.data && e.response.data.detail) ||
            this.$t("messages.l3ContinueFail");
          this.$message.warning(msg);
        } else {
          this.$message.error(this.$t("messages.l3ContinueFail"));
        }
        this.l3Continuing = false;
      }
    },

    startL3Polling() {
      // 每 5 秒查询一次任务状态
      this.l3PollTimer = setInterval(async () => {
        try {
          const res = await getTaskStatus(this.l3TaskId);
          const status = res.data;

          this.l3Progress = status.progress || 0;
          this.l3ProgressMessage = status.message || "";

          // 利用新增的时间戳字段显示运行时长
          if (status.started_at && status.status === "processing") {
            const elapsed = Math.floor(Date.now() / 1000 - status.started_at);
            this.l3ProgressMessage += ` (已运行 ${elapsed}秒)`;

            // 超过 5 分钟提示可能卡死
            if (elapsed > 300) {
              this.l3ProgressMessage += " - 任务运行时间过长，可能已卡死";
            }
          }

          if (status.status === "completed") {
            // 任务完成
            clearInterval(this.l3PollTimer);
            const duration = status.duration
              ? `耗时 ${Math.round(status.duration)}秒`
              : "";
            this.$message.success(
              this.$t("messages.l3ContinueSuccess") +
                (duration ? ` (${duration})` : "")
            );

            // 处理结果
            if (status.result && status.result.l3_overlay) {
              this.setL3Overlay(status.result.l3_overlay);
            } else {
              this.loadL3Image();
            }

            // 刷新数据
            await this.fetchResults();
            this.l3Continuing = false;
          } else if (status.status === "failed") {
            // 任务失败
            clearInterval(this.l3PollTimer);
            const errMsg = status.error ? `: ${status.error}` : "";
            this.$message.error(this.$t("messages.l3ContinueFail") + errMsg);
            this.l3Continuing = false;
          }
          // status === "processing" 时继续轮询
        } catch (e) {
          clearInterval(this.l3PollTimer);
          this.$message.error(this.$t("messages.l3ContinueFail"));
          this.l3Continuing = false;
        }
      }, 5000); // 5 秒轮询一次
    },
    loadL3Image() {
      this.l3ImageUrl = this.versionedL3Url("L3_overlay", "L3_clean.png");
    },
    setL3Overlay(relPath) {
      if (!relPath) return;
      const parts = relPath.split("/");
      const folder = parts.shift();
      const filename = parts.join("/") || "L3_clean.png";
      this.l3ImageUrl = this.versionedL3Url(folder, filename);
    },
    versionedL3Url(folder, filename) {
      const base = getL3ImageUrl(this.patient, this.date, folder, filename);
      return `${base}?t=${Date.now()}`;
    },
  },
};
</script>

<style scoped>
.detail {
  width: clamp(960px, 86vw, 1140px);
  margin: 24px auto 80px;
}

.title {
  display: inline-block;
  padding: 8px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  font-weight: 800;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
}
.head {
  display: flex;
  align-items: center;
  gap: 30px;
  flex-wrap: wrap;
  margin-bottom: 26px;
  padding: 14px 28px 16px;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(14px) saturate(160%);
  -webkit-backdrop-filter: blur(14px) saturate(160%);
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 26px;
  box-shadow: 0 8px 28px -10px rgba(0, 0, 0, 0.1);
}
.card {
  background: #fff;
  border-radius: 14px;
  padding: 16px 18px 18px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
  margin-bottom: 18px;
  color: #111827;
}
.card-title {
  font-weight: 800;
  margin-bottom: 8px;
  color: #0f172a;
}

.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px 12px;
}
.pill {
  background: #f6f9ff;
  border: 1px solid #e6eeff;
  border-radius: 999px;
  padding: 8px 14px;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
.pill .k {
  color: #5a6;
  opacity: 0.9;
}
.pill .v {
  font-weight: 700;
  color: #1f2;
}

.img-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.img-item {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: #f9fafb;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
}
.img-item .el-image {
  width: 100%;
  height: 180px;
}
.caption {
  position: absolute;
  left: 8px;
  bottom: 8px;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 999px;
}
.mid-ops {
  margin-top: 4px;
}
.l3-preview {
  margin-top: 12px;
}
.l3-preview-img {
  max-width: 300px;
  display: block;
  transform: rotate(180deg) scaleX(-1);
  transform-origin: center;
}
.l3-preview-tip {
  font-size: 12px;
  color: #888;
  margin-top: 6px;
}
</style>