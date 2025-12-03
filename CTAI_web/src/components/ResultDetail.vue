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
        <!-- 腰大肌指标 -->
        <div class="pill">
          <span class="k">{{ $t("fields.psoasHu") }}</span>
          <span class="v">{{ fmt(summary.psoas_hu_mean) }}</span>
        </div>
        <div class="pill">
          <span class="k">{{ $t("fields.psoasArea") }}</span>
          <span class="v">{{ fmt(summary.psoas_area_mm2) }}</span>
        </div>
        <div class="pill" v-if="summary.major_volume_mm3 != null">
          <span class="k">腰大肌体积</span>
          <span class="v">{{ fmtVolume(summary.major_volume_mm3) }}</span>
        </div>
        <div class="pill" v-if="summary.mass_psoas_g != null">
          <span class="k">腰大肌质量</span>
          <span class="v">{{ fmt(summary.mass_psoas_g) }} g</span>
        </div>

        <!-- 全肌肉指标 -->
        <div class="pill">
          <span class="k">{{ $t("fields.comboHu") }}</span>
          <span class="v">{{ fmt(summary.combo_hu_mean) }}</span>
        </div>
        <div class="pill">
          <span class="k">{{ $t("fields.comboArea") }}</span>
          <span class="v">{{ fmt(summary.combo_area_mm2) }}</span>
        </div>
        <div class="pill" v-if="summary.full_volume_mm3 != null">
          <span class="k">全肌肉体积</span>
          <span class="v">{{ fmtVolume(summary.full_volume_mm3) }}</span>
        </div>
        <div class="pill" v-if="summary.mass_combo_g != null">
          <span class="k">全肌肉质量</span>
          <span class="v">{{ fmt(summary.mass_combo_g) }} g</span>
        </div>

        <!-- 脂肪指标 -->
        <div class="pill" v-if="summary.sat_hu_mean != null">
          <span class="k">SAT HU值</span>
          <span class="v">{{ fmt(summary.sat_hu_mean) }}</span>
        </div>
        <div class="pill" v-if="summary.sat_area_mm2 != null">
          <span class="k">SAT 面积</span>
          <span class="v">{{ fmt(summary.sat_area_mm2) }}</span>
        </div>
        <div class="pill" v-if="summary.vat_hu_mean != null">
          <span class="k">VAT HU值</span>
          <span class="v">{{ fmt(summary.vat_hu_mean) }}</span>
        </div>
        <div class="pill" v-if="summary.vat_area_mm2 != null">
          <span class="k">VAT 面积</span>
          <span class="v">{{ fmt(summary.vat_area_mm2) }}</span>
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
        <el-table-column
          prop="sat_hu_mean"
          label="SAT HU"
          :formatter="fmtCell"
          v-if="hasColumn('sat_hu_mean')"
        />
        <el-table-column
          prop="sat_area_mm2"
          label="SAT 面积"
          :formatter="fmtCell"
          v-if="hasColumn('sat_area_mm2')"
        />
        <el-table-column
          prop="vat_hu_mean"
          label="VAT HU"
          :formatter="fmtCell"
          v-if="hasColumn('vat_hu_mean')"
        />
        <el-table-column
          prop="vat_area_mm2"
          label="VAT 面积"
          :formatter="fmtCell"
          v-if="hasColumn('vat_area_mm2')"
        />
      </el-table>

      <el-empty v-else :description="$t('result.emptyMetrics')" />
    </section>

    <section class="card">
      <div class="card-title">{{ $t("result.keyImages") }}</div>

      <!-- 肌肉覆盖图 (放在上方) -->
      <div v-if="middle_images.length">
        <h4 style="font-size: 14px; color: #666; margin-bottom: 8px;">肌肉覆盖图</h4>
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

      <!-- 综合覆盖图(包含肌肉+脂肪) - 可折叠 -->
      <div v-if="allOverlayImages.length" style="margin-top: 20px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <h4 style="font-size: 14px; color: #666; margin: 0;">综合覆盖图 (肌肉 + 脂肪)</h4>
          <el-button
            size="mini"
            @click="allOverlayCollapsed = !allOverlayCollapsed"
            :icon="allOverlayCollapsed ? 'el-icon-arrow-down' : 'el-icon-arrow-up'"
          >
            {{ allOverlayCollapsed ? '展开' : '收起' }} ({{ allOverlayImages.length }} 张)
          </el-button>
        </div>
        <div v-show="!allOverlayCollapsed" class="img-grid">
          <div v-for="(img, index) in allOverlayImages" :key="img" class="img-item">
            <el-image
              :src="allOverlayPreviewList[index]"
              fit="cover"
              :preview-src-list="allOverlayPreviewList"
              lazy
            />
            <div class="caption">{{ img }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 3D可视化 -->
    <section class="card">
      <div class="card-title" style="display: flex; justify-content: space-between; align-items: center;">
        <span>3D模型可视化</span>
        <div>
          <el-select
            v-model="selectedMaskType"
            size="mini"
            placeholder="选择类型"
            style="width: 120px; margin-right: 10px;"
            @change="check3DModelsAvailability"
          >
            <el-option label="腰大肌" value="psoas" />
            <el-option label="全肌肉" value="muscle" />
          </el-select>
          <el-button
            size="mini"
            type="primary"
            :loading="reconstructing3D"
            @click="trigger3DReconstruction"
            icon="el-icon-refresh"
          >
            {{ reconstructing3D ? '重建中...' : '重建3D模型' }}
          </el-button>
        </div>
      </div>

      <!-- 进度条 -->
      <div v-if="reconstructing3D" style="margin: 16px 0">
        <el-progress
          :percentage="reconstruction3DProgress"
          :status="reconstruction3DProgress === 100 ? 'success' : undefined"
        />
        <p style="font-size: 12px; color: #666; margin-top: 8px">
          {{ reconstruction3DMessage }}
        </p>
      </div>

      <!-- 提示信息 -->
      <div v-if="!show3DViewer && !reconstructing3D" style="padding: 20px; text-align: center; color: #999;">
        <i class="el-icon-info" style="font-size: 48px; margin-bottom: 10px;"></i>
        <p>暂无3D模型，请点击"重建3D模型"按钮生成</p>
      </div>

      <!-- 3D查看器 -->
      <model-3d-viewer
        v-if="show3DViewer && !reconstructing3D"
        :patient="patient"
        :date="date"
        :selected-mask-type="selectedMaskType"
        :key="`3d-viewer-${selectedMaskType}-${modelRefreshKey}`"
      />
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
        <img
          :src="l3ImageUrl"
          :class="['l3-preview-img', { 'no-flip': isL3HighlightImage }]"
          @error="handleL3ImageError"
        />
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
  check3DModels,
  reconstruct3D,
} from "@/api";
import L3MaskEditor from "./L3MaskEditor.vue";
import MiddleMaskEditor from "./MiddleMaskEditor.vue";
import Model3DViewer from "./Model3DViewer.vue";
import axios from 'axios';

export default {
  name: "ResultDetail",
  components: { L3MaskEditor, MiddleMaskEditor, Model3DViewer },
    data() {
    return {
      loading: true,
      csv_files: {},
      middle_images: [],
      allOverlayImages: [], // 综合覆盖图(肌肉+脂肪)
      allOverlayCollapsed: true, // 综合覆盖图折叠状态
      rows: [],
      summary: null,
      previewList: [],
      allOverlayPreviewList: [],
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
      l3ImageUrlIndex: 0, // 当前尝试的L3图片路径索引
      l3PossibleUrls: [], // 所有可能的L3图片路径
      show3DViewer: false, // 是否显示3D可视化
      selectedMaskType: 'psoas', // 选择的掩码类型
      reconstructing3D: false, // 是否正在重建3D
      reconstruction3DProgress: 0, // 3D重建进度
      reconstruction3DMessage: '', // 3D重建消息
      reconstruction3DTaskId: null, // 3D重建任务ID
      reconstruction3DTimer: null, // 3D重建轮询定时器
      modelRefreshKey: 0, // 用于强制刷新3D模型组件
    };
  },
  beforeDestroy() {
    // 组件销毁时清除定时器
    if (this.l3PollTimer) {
      clearInterval(this.l3PollTimer);
    }
    if (this.reconstruction3DTimer) {
      clearInterval(this.reconstruction3DTimer);
    }
  },
  computed: {
    patient() {
      return this.$route.params.patient;
    },
    date() {
      return this.$route.params.date;
    },
    isL3HighlightImage() {
      // 判断当前显示的是否是verseg新方法生成的图片（已预翻转）
      return this.l3ImageUrl && (
        this.l3ImageUrl.includes('verseg/sagittal_midResize')
      );
    },
  },
  async created() {
    await this.fetchResults();
    // 检查是否有3D模型可用
    this.check3DModelsAvailability();
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

        // 加载综合覆盖图(肌肉+脂肪)
        await this.loadAllOverlayImages();

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

        // 自动加载 L3 图片（如果存在）
        this.loadL3Image();
      } catch (e) {
        this.$message.error(this.$t("messages.fetchFail"));
      } finally {
        this.loading = false;
      }
    },
    async loadAllOverlayImages() {
      try {
        const BASE_URL = process.env.VUE_APP_BASE_URL || "http://localhost:4200";
        const token = localStorage.getItem('access_token');
        const params = new URLSearchParams();
        params.append('t', Date.now());
        if (token) {
          params.append('token', token);
        }
        const url = `${BASE_URL}/list_output_folder/${encodeURIComponent(this.patient)}/${this.date}/all_overlay?${params.toString()}`;
        const res = await axios.get(url);
        if (res.data && res.data.files) {
          this.allOverlayImages = res.data.files.filter(f => f.endsWith('.png'));
          this.allOverlayPreviewList = this.allOverlayImages.map(img =>
            getL3ImageUrl(this.patient, this.date, 'all_overlay', img)
          );
        }
      } catch (e) {
        // all_overlay 可能不存在,静默处理
        this.allOverlayImages = [];
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
        sat_hu_mean: "sat_hu_mean",
        sat_area_mm2: "sat_area_mm2",
        vat_hu_mean: "vat_hu_mean",
        vat_area_mm2: "vat_area_mm2",
        major_volume_mm3: "major_volume_mm3",
        full_volume_mm3: "full_volume_mm3",
        mass_psoas_g: "mass_psoas_g",
        mass_combo_g: "mass_combo_g",
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
            sat_hu_mean: num(get(col.sat_hu_mean)),
            sat_area_mm2: num(get(col.sat_area_mm2)),
            vat_hu_mean: num(get(col.vat_hu_mean)),
            vat_area_mm2: num(get(col.vat_area_mm2)),
            major_volume_mm3: num(get(col.major_volume_mm3)),
            full_volume_mm3: num(get(col.full_volume_mm3)),
            mass_psoas_g: num(get(col.mass_psoas_g)),
            mass_combo_g: num(get(col.mass_combo_g)),
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
        "sat_hu_mean",
        "sat_area_mm2",
        "vat_hu_mean",
        "vat_area_mm2",
      ];
      const s = {};

      // 计算平均值
      for (const k of keys) {
        const vals = rows
          .map((r) => r[k])
          .filter((v) => typeof v === "number" && !Number.isNaN(v));
        s[k] = vals.length
          ? vals.reduce((a, b) => a + b, 0) / vals.length
          : null;
      }

      // 体积和质量数据(所有行都相同,取第一行)
      if (rows[0]) {
        s.major_volume_mm3 = rows[0].major_volume_mm3;
        s.full_volume_mm3 = rows[0].full_volume_mm3;
        s.mass_psoas_g = rows[0].mass_psoas_g;
        s.mass_combo_g = rows[0].mass_combo_g;
      }

      return s;
    },
    hasColumn(colName) {
      return this.rows.length > 0 && this.rows[0][colName] != null;
    },
    fmtVolume(mm3) {
      if (mm3 == null || Number.isNaN(mm3)) return '-';
      const ml = mm3 / 1000;
      return `${mm3.toFixed(0)} mm³ (${ml.toFixed(2)} mL)`;
    },
    imageUrl(filename) {
      return getImageUrl(this.patient, this.date, filename);
    },
    getL3ImageUrl(patient, date, folder, filename) {
      return getL3ImageUrl(patient, date, folder, filename);
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
      // 定义所有可能的L3图片位置（按优先级排序）
      const possibleLocations = [
        // verseg新方法生成的文件 - 高亮版本（最优先）
        { folder: 'verseg', filename: 'sagittal_midResize_0000_L3_highlight.png' },
        { folder: 'verseg', filename: 'sagittal_midResize_0000_L3_overlay.png' },
        { folder: 'verseg', filename: 'sagittal_midResize_0000_whole_overlay.png' },
        { folder: 'verseg', filename: 'sagittal_midResize_0000_vertebra_overlay.png' },
        // 旧方法可能的位置
        { folder: 'verseg', filename: 'L3_clean.png' },
        { folder: 'verseg', filename: 'L3_overlay.png' },
        { folder: 'L3_overlay', filename: 'L3_clean.png' },
        { folder: 'L3_clean', filename: 'L3_clean.png' },
        { folder: 'L3', filename: 'L3_clean.png' },
        { folder: 'L3', filename: 'L3_overlay.png' },
      ];

      // 生成所有可能的URL
      this.l3PossibleUrls = possibleLocations.map(loc =>
        getL3ImageUrl(this.patient, this.date, loc.folder, loc.filename, false)
      );

      // 从第一个开始尝试
      this.l3ImageUrlIndex = 0;
      this.tryNextL3Image();
    },
    tryNextL3Image() {
      if (this.l3ImageUrlIndex < this.l3PossibleUrls.length) {
        this.l3ImageUrl = this.l3PossibleUrls[this.l3ImageUrlIndex];
      } else {
        // 所有位置都尝试过了，没有找到图片
        this.l3ImageUrl = "";
      }
    },
    handleL3ImageError() {
      // 当前图片加载失败，尝试下一个位置
      this.l3ImageUrlIndex++;
      this.tryNextL3Image();
    },
    setL3Overlay(relPath) {
      if (!relPath) return;
      const parts = relPath.split("/");
      const folder = parts.shift();
      const filename = parts.join("/") || "L3_clean.png";
      // 强制刷新：使用缓存破坏
      this.l3ImageUrl = getL3ImageUrl(this.patient, this.date, folder, filename, true);
    },
    versionedL3Url(folder, filename) {
      // L3 图片需要缓存破坏，因为会被更新
      return getL3ImageUrl(this.patient, this.date, folder, filename, true);
    },
    async check3DModelsAvailability() {
      try {
        console.log('[3D检查] ========== 开始检查3D模型可用性 ==========');
        console.log('[3D检查] 当前状态:', {
          patient: this.patient,
          date: this.date,
          selectedMaskType: this.selectedMaskType,
          show3DViewer: this.show3DViewer,
          reconstructing3D: this.reconstructing3D
        });

        const result = await check3DModels(this.patient, this.date);
        console.log('[3D检查] API返回结果:', result);

        if (result.available && result.models && result.models.length > 0) {
          console.log('[3D检查] ✅ 找到模型，数量:', result.models.length);
          console.log('[3D检查] 模型详情:', result.models);

          // 检查是否有当前选择类型的模型
          const hasSelectedType = result.models.some(m => m.mask_type === this.selectedMaskType);
          console.log('[3D检查] 是否有选中类型的模型:', hasSelectedType);
          console.log('[3D检查] 选中的类型:', this.selectedMaskType);

          console.log('[3D检查] 设置 show3DViewer =', hasSelectedType);
          this.show3DViewer = hasSelectedType;
          console.log('[3D检查] show3DViewer 已设置为:', this.show3DViewer);

          if (hasSelectedType) {
            // 找到对应模型的体积信息
            const model = result.models.find(m => m.mask_type === this.selectedMaskType);
            console.log('[3D检查] 找到对应模型:', model);
            if (model && model.volume_mm3) {
              console.log(`[3D检查] ${this.selectedMaskType} 体积: ${model.volume_mm3} mm³ (${model.volume_ml} mL)`);
            }
          } else {
            console.warn('[3D检查] ⚠️ 没有找到 ' + this.selectedMaskType + ' 类型的模型');
          }
        } else {
          console.log('[3D检查] ❌ 没有可用的3D模型');
          this.show3DViewer = false;
        }

        console.log('[3D检查] ========== 检查完成 ==========');
        console.log('[3D检查] 最终状态:', {
          show3DViewer: this.show3DViewer,
          reconstructing3D: this.reconstructing3D
        });
      } catch (error) {
        console.error('[3D检查] ❌ 检查3D模型失败:', error);
        this.show3DViewer = false;
      }
    },
    async trigger3DReconstruction() {
      this.reconstructing3D = true;
      this.reconstruction3DProgress = 0;
      this.reconstruction3DMessage = '正在提交3D重建任务...';

      try {
        const result = await reconstruct3D(this.patient, this.date, this.selectedMaskType);

        if (result.task_id) {
          this.reconstruction3DTaskId = result.task_id;
          this.$message.success(result.message || '3D重建任务已提交');

          // 开始轮询任务状态
          this.start3DReconstructionPolling();
        } else {
          // 同步完成（不太可能）
          this.$message.success('3D重建完成');
          this.reconstructing3D = false;
          await this.check3DModelsAvailability();
          this.modelRefreshKey++; // 强制刷新3D查看器
        }
      } catch (error) {
        console.error('3D重建失败:', error);
        const errorMsg = error.response?.data?.detail || error.message || '3D重建失败';
        this.$message.error(errorMsg);
        this.reconstructing3D = false;
      }
    },
    start3DReconstructionPolling() {
      // 每3秒查询一次任务状态
      this.reconstruction3DTimer = setInterval(async () => {
        try {
          const res = await getTaskStatus(this.reconstruction3DTaskId);
          const status = res.data;

          this.reconstruction3DProgress = status.progress || 0;
          this.reconstruction3DMessage = status.message || '';

          if (status.status === 'completed') {
            // 任务完成
            clearInterval(this.reconstruction3DTimer);
            const duration = status.duration ? `耗时 ${Math.round(status.duration)}秒` : '';
            this.$message.success(`3D重建完成 ${duration}`);

            // 刷新3D模型列表
            await this.check3DModelsAvailability();
            this.modelRefreshKey++; // 强制刷新3D查看器
            this.reconstructing3D = false;
          } else if (status.status === 'failed') {
            // 任务失败
            clearInterval(this.reconstruction3DTimer);
            const errMsg = status.error ? `: ${status.error}` : '';
            this.$message.error(`3D重建失败${errMsg}`);
            this.reconstructing3D = false;
          }
          // status === "processing" 时继续轮询
        } catch (e) {
          clearInterval(this.reconstruction3DTimer);
          this.$message.error('查询3D重建状态失败');
          this.reconstructing3D = false;
        }
      }, 3000); // 3秒轮询一次
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
.l3-preview-img.no-flip {
  /* highlight图片已在后端预翻转，不需要前端再翻转 */
  transform: none;
}
.l3-preview-tip {
  font-size: 12px;
  color: #888;
  margin-top: 6px;
}
</style>