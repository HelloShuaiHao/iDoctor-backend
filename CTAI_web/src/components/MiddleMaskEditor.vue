<template>
  <el-dialog
    :visible.sync="innerVisible"
    :title="$t('middleEditor.title')"
    width="960px"
    append-to-body
    :close-on-click-modal="false"
    @closed="onClosed"
  >
    <div class="top-bar">
      <div class="modes">
        <el-button
          size="mini"
          :type="mode === 'psoas' ? 'primary' : 'default'"
          @click="setMode('psoas')"
          >{{ $t("middleEditor.modePsoas") }}</el-button
        >
        <el-button
          size="mini"
          :type="mode === 'combo' ? 'primary' : 'default'"
          @click="setMode('combo')"
          >{{ $t("middleEditor.modeCombo") }}</el-button
        >
        <span class="tip">{{ $t("middleEditor.polyHint") }}</span>
      </div>
      <div class="ops">
        <el-button size="mini" :disabled="!canUndo" @click="undo">{{
          currentPoly.length ? $t("actions.undoPoint") : $t("actions.undo")
        }}</el-button>
        <el-button
          size="mini"
          :disabled="!polys[mode].length"
          @click="clearMode"
          >{{ $t("actions.clear") }}</el-button
        >
      </div>
    </div>

    <div class="stage-wrapper" v-loading="loading">
      <div
        v-if="imgUrl"
        class="stage"
        :style="stageStyle"
        @keydown.stop.prevent="onKey"
        tabindex="0"
      >
        <img
          :src="imgUrl"
          class="base-img"
          draggable="false"
          @load="onImgLoad"
        />
        <canvas
          ref="canvas"
          class="poly-canvas"
          @mousedown.prevent="onCanvasDown"
          @mousemove="onCanvasMove"
          @mouseleave="onCanvasLeave"
        ></canvas>
      </div>
      <el-empty v-else description="No image" />
    </div>

    <span slot="footer" class="dlg-footer">
      <el-button size="mini" @click="innerVisible = false">{{
        $t("actions.cancel")
      }}</el-button>
      <el-button type="primary" size="mini" :loading="saving" @click="save">
        {{ $t("actions.saveUpload") }}
      </el-button>
    </span>
  </el-dialog>
</template>

<script>
// ...existing code...
import { uploadMiddleManualMask, getAxisalImageUrl } from "@/api";

export default {
  name: "MiddleMaskEditor",
  props: {
    visible: { type: Boolean, default: false },
    patient: { type: String, required: true },
    date: { type: String, required: true },
    axisalFilename: { type: String, required: true },
  },
  data() {
    return {
      innerVisible: this.visible,
      imgUrl: "",
      loading: false,
      saving: false,
      naturalWidth: 0,
      naturalHeight: 0,
      scale: 1,
      mode: "psoas",
      polys: { psoas: [], combo: [] }, // 每个元素：[{x,y},...]
      currentPoly: [],
      hoverPoint: null,
    };
  },
  computed: {
    stageStyle() {
      return {
        width: this.naturalWidth * this.scale + "px",
        height: this.naturalHeight * this.scale + "px",
      };
    },
    canUndo() {
      return this.currentPoly.length || this.polys[this.mode].length;
    },
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
  methods: {
    init() {
      this.mode = "psoas";
      this.polys = { psoas: [], combo: [] };
      this.currentPoly = [];
      this.loadImage();
      this.$nextTick(() => {
        const st = this.$el.querySelector(".stage");
        st && st.focus();
      });
    },
    loadImage() {
      if (!this.axisalFilename) return;
      this.imgUrl =
        getAxisalImageUrl(this.patient, this.date, this.axisalFilename) +
        "?t=" +
        Date.now();
    },
    onImgLoad(e) {
      const img = e.target;
      this.naturalWidth = img.naturalWidth;
      this.naturalHeight = img.naturalHeight;
      this.computeScale();
      this.resizeCanvas();
      this.redraw();
    },
    computeScale() {
      const maxW = 780;
      this.scale = Math.min(1, maxW / this.naturalWidth);
    },
    resizeCanvas() {
      const cv = this.$refs.canvas;
      if (!cv) return;
      cv.width = this.naturalWidth * this.scale;
      cv.height = this.naturalHeight * this.scale;
    },
    evtToImg(e) {
      const rect = this.$refs.canvas.getBoundingClientRect();
      return {
        x: Math.max(
          0,
          Math.min(this.naturalWidth, (e.clientX - rect.left) / this.scale)
        ),
        y: Math.max(
          0,
          Math.min(this.naturalHeight, (e.clientY - rect.top) / this.scale)
        ),
      };
    },
    distance(a, b) {
      const dx = a.x - b.x,
        dy = a.y - b.y;
      return Math.sqrt(dx * dx + dy * dy);
    },
    onCanvasDown(e) {
      if (!this.imgUrl) return;
      const p = this.evtToImg(e);
      if (!this.currentPoly.length) {
        // 新多边形起点
        this.currentPoly.push(p);
      } else {
        const first = this.currentPoly[0];
        const CLOSE_DIST = 10 / this.scale; // 触碰阈值
        if (
          this.currentPoly.length >= 2 &&
          this.distance(p, first) <= CLOSE_DIST
        ) {
          // 闭合
          this.finishCurrent();
        } else {
          this.currentPoly.push(p);
        }
      }
      this.redraw();
    },
    onCanvasMove(e) {
      if (!this.currentPoly.length) {
        this.hoverPoint = null;
      } else {
        const p = this.evtToImg(e);
        this.hoverPoint = p;
      }
      this.redraw();
    },
    onCanvasLeave() {
      this.hoverPoint = null;
      this.redraw();
    },
    finishCurrent() {
      if (this.currentPoly.length >= 3) {
        this.polys[this.mode].push(this.currentPoly.slice());
      }
      this.currentPoly = [];
      this.hoverPoint = null;
      this.redraw();
    },
    setMode(m) {
      if (this.mode !== m) {
        this.mode = m;
        this.currentPoly = [];
        this.hoverPoint = null;
        this.redraw();
      }
    },
    undo() {
      if (this.currentPoly.length) {
        this.currentPoly.pop();
        this.redraw();
      } else if (this.polys[this.mode].length) {
        this.polys[this.mode].pop();
        this.redraw();
      }
    },
    clearMode() {
      this.polys[this.mode] = [];
      this.currentPoly = [];
      this.redraw();
    },
    redraw() {
      const cv = this.$refs.canvas;
      if (!cv) return;
      const ctx = cv.getContext("2d");
      ctx.clearRect(0, 0, cv.width, cv.height);
      ctx.save();
      ctx.scale(this.scale, this.scale);
      const drawPolys = (list, stroke, fill) => {
        for (const poly of list) {
          if (poly.length < 2) continue;
          ctx.beginPath();
          ctx.moveTo(poly[0].x, poly[0].y);
          for (let i = 1; i < poly.length; i++)
            ctx.lineTo(poly[i].x, poly[i].y);
          ctx.closePath();
          ctx.fillStyle = fill;
          ctx.fill();
          ctx.strokeStyle = stroke;
          ctx.lineWidth = 2;
          ctx.stroke();
          // 顶点
          ctx.fillStyle = stroke;
          for (const pt of poly) {
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      };
      drawPolys(this.polys.psoas, "rgba(0,170,0,0.95)", "rgba(0,170,0,0.25)");
      drawPolys(
        this.polys.combo,
        "rgba(10,132,255,0.95)",
        "rgba(10,132,255,0.22)"
      );

      // 正在绘制的多边形
      if (this.currentPoly.length) {
        ctx.beginPath();
        ctx.moveTo(this.currentPoly[0].x, this.currentPoly[0].y);
        for (let i = 1; i < this.currentPoly.length; i++) {
          ctx.lineTo(this.currentPoly[i].x, this.currentPoly[i].y);
        }
        if (this.hoverPoint) {
          ctx.lineTo(this.hoverPoint.x, this.hoverPoint.y);
        }
        ctx.strokeStyle = "rgba(255,180,0,0.95)";
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "rgba(255,180,0,0.25)";
        if (this.currentPoly.length >= 2 && this.hoverPoint) {
          ctx.lineTo(this.currentPoly[0].x, this.currentPoly[0].y);
          ctx.fill();
        }
        // 顶点
        ctx.fillStyle = "rgba(255,180,0,0.95)";
        for (const pt of this.currentPoly) {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 3.2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.restore();
    },
    onKey(e) {
      if (e.key === "Escape") {
        this.currentPoly = [];
        this.redraw();
      } else if (e.key === "Backspace" || e.key === "Delete") {
        if (this.currentPoly.length) {
          this.currentPoly.pop();
          this.redraw();
        }
      }
    },
    async save() {
      if (!this.polys.psoas.length && !this.polys.combo.length) {
        this.$message.warning(this.$t("middleEditor.emptyWarn"));
        return;
      }
      this.saving = true;
      try {
        // 提取 base_name（与后端写入一致，例如 slice_105.png）
        const base = this.axisalFilename.replace(/\.png$/i, "");
        const psoasFile = this.polys.psoas.length
          ? await this.buildMaskFile(this.polys.psoas, `${base}_psoas.png`)
          : null;
        const comboFile = this.polys.combo.length
          ? await this.buildMaskFile(this.polys.combo, `${base}_combo.png`)
          : null;

        // 后端已修复 NaN/Inf JSON 序列化问题，clean_floats 会自动清理统计结果中的非法浮点数
        const res = await uploadMiddleManualMask(
          this.patient,
          this.date,
          psoasFile,
          comboFile
        );

        if (res && res.data && res.data.error) {
          console.error("[MiddleMaskEditor] backend error:", res.data.error);
          this.$message.error(res.data.error);
        } else {
          this.$message.success(this.$t("messages.maskUploadSuccess"));
          this.$emit("uploaded");
          this.innerVisible = false;
        }
      } catch (e) {
        console.error("[MiddleMaskEditor] upload failed:", e);
        this.$message.error(
          this.$t("messages.maskUploadFail") +
            (e.message ? `: ${e.message}` : "")
        );
      } finally {
        this.saving = false;
      }
    },

    buildMaskFile(polygons, name) {
      return new Promise((resolve, reject) => {
        try {
          const c = document.createElement("canvas");
          c.width = this.naturalWidth;
          c.height = this.naturalHeight;
          const ctx = c.getContext("2d");
          ctx.fillStyle = "black";
          ctx.fillRect(0, 0, c.width, c.height);
          ctx.fillStyle = "white";
          for (const poly of polygons) {
            if (poly.length < 3) continue;
            ctx.beginPath();
            ctx.moveTo(poly[0].x, poly[0].y);
            for (let i = 1; i < poly.length; i++)
              ctx.lineTo(poly[i].x, poly[i].y);
            ctx.closePath();
            ctx.fill();
          }
          c.toBlob(
            (b) => {
              if (!b) {
                reject(new Error("Canvas toBlob failed"));
                return;
              }
              resolve(new File([b], name, { type: "image/png" }));
            },
            "image/png",
            1
          );
        } catch (err) {
          reject(err);
        }
      });
    },
    onClosed() {
      this.polys = { psoas: [], combo: [] };
      this.currentPoly = [];
    },
  },
};
</script>

<style scoped>
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.modes,
.ops {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.tip {
  font-size: 12px;
  color: #5b6875;
  max-width: 430px;
  line-height: 1.35;
}
.stage-wrapper {
  min-height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stage {
  position: relative;
  background: #000;
  border: 1px solid #333;
  border-radius: 10px;
  overflow: hidden;
  outline: none;
}
.base-img {
  position: absolute;
  inset: 0;
  width: 100%;
  user-select: none;
  -webkit-user-drag: none;
  pointer-events: none;
}
.poly-canvas {
  position: absolute;
  inset: 0;
  cursor: crosshair;
}
.dlg-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>