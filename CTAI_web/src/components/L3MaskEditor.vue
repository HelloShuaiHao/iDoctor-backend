<template>
  <el-dialog
    :visible.sync="innerVisible"
    append-to-body
    width="860px"
    :close-on-click-modal="false"
    :destroy-on-close="true"
    :title="$t('editor.l3MaskTitle')"
    @closed="handleClosed"
  >
    <div class="stage-wrapper" v-loading="generating">
      <div v-if="imageUrl" class="canvas-stage" :style="stageStyle">
        <img
          :src="imageUrl"
          ref="img"
          class="base-img"
          @load="onImgLoad"
          draggable="false"
        />
        <canvas
          ref="canvas"
          class="draw-canvas"
          @mousedown="onDown"
          @mousemove="onMove"
          @mouseup="onUp"
          @mouseleave="onUp"
        ></canvas>
      </div>
      <el-empty v-else :description="$t('editor.noSagittal')" />
    </div>

    <div class="tips">
      {{ $t('editor.tips') }}
    </div>

    <span slot="footer" class="footer-bar">
      <div class="left">
        <el-button size="mini" :loading="generating" @click="fetchSagittal(1)">
          {{ $t('actions.retry') }}
        </el-button>
        <el-button size="mini" :disabled="!rects.length" @click="undo">
          {{ $t('actions.undo') }}
        </el-button>
        <el-button size="mini" :disabled="!rects.length" @click="clearRects">
          {{ $t('actions.clear') }}
        </el-button>
      </div>
      <div class="right">
        <el-button size="mini" @click="close">
          {{ $t('actions.cancel') }}
        </el-button>
        <el-button
          type="primary"
          size="mini"
          :disabled="!rects.length || uploading || !imageUrl"
          :loading="uploading"
          @click="saveAndUpload"
        >
          {{ $t('actions.saveUpload') }}
        </el-button>
      </div>
    </span>
  </el-dialog>
</template>
<script>
import { generateSagittal, getL3ImageUrl, uploadL3Mask } from "@/api";

export default {
  name: "L3MaskEditor",
  props: {
    visible: { type: Boolean, default: false },
    patient: { type: String, required: true },
    date: { type: String, required: true },
  },
  data() {
    return {
      innerVisible: this.visible,
      generating: false,
      uploading: false,
      imageUrl: "",
      sagittalRelPath: "", // eg: L3_png/sagittal_midResize.png
      filename: "sagittal_midResize.png",
      naturalWidth: 0,
      naturalHeight: 0,
      scale: 1,
      rects: [], // 坐标存原始图尺寸
      drawing: false,
      startPoint: null,
      currentRect: null,
    };
  },
  watch: {
    visible(v) {
      this.innerVisible = v;
      if (v) this.init();
    },
    innerVisible(v) {
      this.$emit("update:visible", v);
    },
  },
  computed: {
    stageStyle() {
      return {
        width: this.naturalWidth * this.scale + "px",
        height: this.naturalHeight * this.scale + "px",
      };
    },
  },
  methods: {
    init() {
      this.rects = [];
      this.currentRect = null;
      this.fetchSagittal(0);
    },
    async fetchSagittal(force = 0) {
      this.generating = true;
      this.imageUrl = "";
      try {
        const res = await generateSagittal(this.patient, this.date, force);
        const data = res.data || {};
        if (data.sagittal_png) {
          this.sagittalRelPath = data.sagittal_png; // L3_png/xxx.png
          const parts = data.sagittal_png.split("/");
          const folder = parts[0];
          this.filename = parts[1] || "sagittal_midResize.png";
          this.imageUrl = getL3ImageUrl(
            this.patient,
            this.date,
            folder,
            this.filename
          );
        }
      } catch {
        this.$message.error("生成侧视图失败");
      } finally {
        this.generating = false;
      }
    },
    onImgLoad() {
      const img = this.$refs.img;
      if (!img) return;
      this.naturalWidth = img.naturalWidth;
      this.naturalHeight = img.naturalHeight;
      this.computeScale();
      this.resizeCanvas();
      this.redraw();
    },
    computeScale() {
      const maxDisplayWidth = 760; // dialog 内容宽度约 860，留边距
      const wScale = maxDisplayWidth / this.naturalWidth;
      this.scale = Math.min(1, wScale); // 不放大，只等比缩小
    },
    resizeCanvas() {
      const cv = this.$refs.canvas;
      if (!cv) return;
      cv.width = this.naturalWidth * this.scale;
      cv.height = this.naturalHeight * this.scale;
    },
    canvasToImageCoords(evt) {
      const cv = this.$refs.canvas;
      const rect = cv.getBoundingClientRect();
      const xDisp = evt.clientX - rect.left;
      const yDisp = evt.clientY - rect.top;
      // 转回原始图坐标
      return {
        x: Math.max(0, Math.min(this.naturalWidth, xDisp / this.scale)),
        y: Math.max(0, Math.min(this.naturalHeight, yDisp / this.scale)),
      };
    },
    onDown(e) {
      if (!this.imageUrl) return;
      const { x, y } = this.canvasToImageCoords(e);
      this.drawing = true;
      this.startPoint = { x, y };
      this.currentRect = null;
    },
    onMove(e) {
      if (!this.drawing) return;
      const { x, y } = this.canvasToImageCoords(e);
      this.currentRect = {
        x1: this.startPoint.x,
        y1: this.startPoint.y,
        x2: x,
        y2: y,
      };
      this.redraw();
    },
    onUp() {
      if (!this.drawing) return;
      this.drawing = false;
      if (this.currentRect) {
        const r = this.normalize(this.currentRect);
        if (r.x2 - r.x1 > 3 && r.y2 - r.y1 > 3) this.rects.push(r);
      }
      this.currentRect = null;
      this.redraw();
    },
    normalize(r) {
      return {
        x1: Math.min(r.x1, r.x2),
        y1: Math.min(r.y1, r.y2),
        x2: Math.max(r.x1, r.x2),
        y2: Math.max(r.y1, r.y2),
      };
    },
    redraw() {
      const cv = this.$refs.canvas;
      if (!cv) return;
      const ctx = cv.getContext("2d");
      ctx.clearRect(0, 0, cv.width, cv.height);
      ctx.save();
      ctx.scale(this.scale, this.scale);
      // 已完成矩形
      for (const r of this.rects) {
        ctx.strokeStyle = "rgba(0,200,0,0.95)";
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
        ctx.strokeRect(r.x1, r.y1, r.x2 - r.x1, r.y2 - r.y1);
        ctx.fillStyle = "rgba(0,200,0,0.18)";
        ctx.fillRect(r.x1, r.y1, r.x2 - r.x1, r.y2 - r.y1);
      }
      // 正在绘制
      if (this.currentRect) {
        const r = this.normalize(this.currentRect);
        ctx.strokeStyle = "rgba(255,180,0,0.95)";
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.strokeRect(r.x1, r.y1, r.x2 - r.x1, r.y2 - r.y1);
        ctx.setLineDash([]);
      }
      ctx.restore();
    },
    undo() {
      if (!this.rects.length) return;
      this.rects.pop();
      this.redraw();
    },
    clearRects() {
      this.rects = [];
      this.currentRect = null;
      this.redraw();
    },
    async saveAndUpload() {
      if (!this.rects.length) {
        this.$message.warning("请先绘制至少一个矩形");
        return;
      }
      this.uploading = true;
      try {
        const blob = await this.buildMaskBlob();
        const file = new File([blob], this.filename, { type: "image/png" });
        const res = await uploadL3Mask(this.patient, this.date, file);
        const data = res.data || {};
        if (data.status === "ok") {
          this.$message.success("上传成功");
          this.$emit("uploaded", { overlay: data.overlay });
          this.close();
        } else {
          this.$message.error(data.message || "上传失败");
        }
      } catch {
        this.$message.error("上传失败");
      } finally {
        this.uploading = false;
      }
    },
    buildMaskBlob() {
      return new Promise((resolve, reject) => {
        const c = document.createElement("canvas");
        c.width = this.naturalWidth;
        c.height = this.naturalHeight;
        const ctx = c.getContext("2d");
        ctx.fillStyle = "black";
        ctx.fillRect(0, 0, c.width, c.height);
        ctx.fillStyle = "white";
        for (const r of this.rects) {
          ctx.fillRect(r.x1, r.y1, r.x2 - r.x1, r.y2 - r.y1);
        }
        c.toBlob(
          (b) => (b ? resolve(b) : reject(new Error("toBlob失败"))),
          "image/png",
          1
        );
      });
    },
    close() {
      this.innerVisible = false;
    },
    handleClosed() {
      this.rects = [];
      this.currentRect = null;
      this.imageUrl = "";
    },
  },
};
</script>

<style scoped>
.stage-wrapper {
  min-height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.canvas-stage {
  position: relative;
  background: #000;
  border: 1px solid #444;
  border-radius: 6px;
  overflow: hidden;
}
.base-img {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  user-select: none;
}
.draw-canvas {
  position: absolute;
  left: 0;
  top: 0;
  cursor: crosshair;
  z-index: 2;
}
.footer-bar {
  display: flex;
  justify-content: space-between;
  width: 100%;
}
.footer-bar .left > * {
  margin-right: 6px;
}
.tips {
  margin-top: 10px;
  font-size: 12px;
  color: #888;
  text-align: center;
  line-height: 1.4;
}
</style>