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
          :class="{ 'click-mode': sam2ClickMode }"
          @mousedown="onDown"
          @mousemove="onMove"
          @mouseup="onUp"
          @mouseleave="onUp"
        ></canvas>
      </div>
      <el-empty v-else :description="$t('editor.noSagittal')" />
    </div>

    <div class="tips">
      <template v-if="sam2ClickMode">
        <span style="color: #67C23A; font-weight: bold;">SAM2交互模式:</span>
        左键点击肌肉区域(前景点)，右键点击背景区域，然后点击"执行分割"
      </template>
      <template v-else>
        {{ $t('editor.tips') }}
      </template>
    </div>

    <span slot="footer" class="footer-bar">
      <div class="left">
        <el-button size="mini" :loading="generating" @click="fetchSagittal(1)">
          {{ $t('actions.retry') }}
        </el-button>
        <el-button
          size="mini"
          :type="sam2ClickMode ? 'success' : 'warning'"
          icon="el-icon-magic-stick"
          :disabled="!imageUrl || sam2Processing"
          @click="toggleSam2ClickMode"
        >
          {{ sam2ClickMode ? '点击模式(已启用)' : 'SAM2交互分割' }}
        </el-button>
        <el-button
          v-if="sam2ClickMode"
          size="mini"
          type="primary"
          :disabled="clickPoints.length === 0 || sam2Processing"
          :loading="sam2Processing"
          @click="runSam2SegmentWithClicks"
        >
          {{ sam2Processing ? `分割中...` : `执行分割(${clickPoints.length}个点)` }}
        </el-button>
        <el-button
          v-if="sam2ClickMode"
          size="mini"
          :disabled="clickPoints.length === 0"
          @click="clearClickPoints"
        >
          清除点击
        </el-button>
        <el-button v-if="!sam2ClickMode" size="mini" :disabled="!rects.length" @click="undo">
          {{ $t('actions.undo') }}
        </el-button>
        <el-button v-if="!sam2ClickMode" size="mini" :disabled="!rects.length" @click="clearRects">
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
import { generateSagittal, getL3ImageUrl, uploadL3Mask, sam2Segment } from "@/api";

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
      sam2Processing: false, // SAM2 分割处理中
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
      // SAM2交互模式
      sam2ClickMode: false, // 是否处于SAM2点击模式
      clickPoints: [], // 用户点击的点 [{x, y, label}]
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

      // SAM2点击模式: 记录点击点
      if (this.sam2ClickMode) {
        e.preventDefault();
        const { x, y } = this.canvasToImageCoords(e);
        const label = e.button === 2 ? 0 : 1; // 右键=背景(0), 左键=前景(1)
        this.clickPoints.push({ x, y, label });
        this.redraw();
        return;
      }

      // 矩形绘制模式
      const { x, y } = this.canvasToImageCoords(e);
      this.drawing = true;
      this.startPoint = { x, y };
      this.currentRect = null;
    },
    onMove(e) {
      if (this.sam2ClickMode) return; // SAM2模式不需要move
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
      if (this.sam2ClickMode) return; // SAM2模式不需要up
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
      if (!cv) {
        console.warn('Canvas ref not found, cannot redraw');
        return;
      }
      const ctx = cv.getContext("2d");
      ctx.clearRect(0, 0, cv.width, cv.height);
      ctx.save();
      ctx.scale(this.scale, this.scale);

      console.log('Redrawing:', {
        mode: this.sam2ClickMode ? 'SAM2' : 'Rectangle',
        clickPointsCount: this.clickPoints.length,
        rectsCount: this.rects.length,
        scale: this.scale
      });

      // SAM2点击模式: 绘制点击点
      if (this.sam2ClickMode) {
        for (const pt of this.clickPoints) {
          // label=1(前景)绿色, label=0(背景)红色
          const color = pt.label === 1 ? 'rgba(0,255,0,0.8)' : 'rgba(255,0,0,0.8)';
          const outerColor = pt.label === 1 ? 'rgba(0,200,0,1)' : 'rgba(200,0,0,1)';

          // 绘制外圈
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 8, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.strokeStyle = outerColor;
          ctx.lineWidth = 2;
          ctx.stroke();

          // 绘制中心点
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 2, 0, 2 * Math.PI);
          ctx.fillStyle = 'white';
          ctx.fill();
        }
      } else {
        // 矩形模式: 绘制矩形
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
    // 切换SAM2点击模式
    toggleSam2ClickMode() {
      this.sam2ClickMode = !this.sam2ClickMode;
      if (this.sam2ClickMode) {
        // 进入点击模式时清空点击点
        this.clickPoints = [];
        // 禁用右键菜单
        const canvas = this.$refs.canvas;
        if (canvas) {
          canvas.oncontextmenu = (e) => {
            e.preventDefault();
            return false;
          };
        }
        this.$message.info('已进入SAM2交互模式，左键点击肌肉区域，右键点击背景区域');
      } else {
        // 退出点击模式
        const canvas = this.$refs.canvas;
        if (canvas) {
          canvas.oncontextmenu = null;
        }
      }
      this.redraw();
    },
    // 清除点击点
    clearClickPoints() {
      this.clickPoints = [];
      this.redraw();
    },
    // SAM2交互分割（带点击点）
    async runSam2SegmentWithClicks() {
      if (this.clickPoints.length === 0) {
        this.$message.warning('请至少点击一个点');
        return;
      }

      this.sam2Processing = true;

      try {
        // 将当前图像转换为Blob
        const response = await fetch(this.imageUrl);
        const imageBlob = await response.blob();

        // 调用SAM2 API with click points
        const result = await sam2Segment({
          imageFile: imageBlob,
          imageType: 'L3',
          patientId: this.patient,
          sliceIndex: this.date,
          clickPoints: this.clickPoints // 传递点击点
        });

        // 显示处理时间和置信度
        const timeMsg = result.cached ? '(缓存)' : `(${result.processing_time_ms}ms)`;
        this.$message.success(
          `AI分割完成 ${timeMsg} 置信度: ${(result.confidence_score * 100).toFixed(1)}%`
        );

        // 解码mask_data (base64 PNG)
        console.log('SAM2 result:', {
          confidence: result.confidence_score,
          time: result.processing_time_ms,
          cached: result.cached,
          bbox: result.bounding_box,
          maskDataLength: result.mask_data ? result.mask_data.length : 0
        });

        const maskImage = new Image();
        maskImage.onload = () => {
          console.log('Mask image loaded successfully');

          // 先退出SAM2模式，进入矩形编辑模式
          this.sam2ClickMode = false;
          this.clickPoints = [];

          // 然后分析mask图像，提取白色区域作为矩形
          // 这样redraw会使用矩形模式来绘制
          this.extractRectsFromMask(maskImage);
        };
        maskImage.onerror = (e) => {
          console.error('Mask image load error:', e);
          throw new Error('Mask图像加载失败');
        };
        maskImage.src = `data:image/png;base64,${result.mask_data}`;

      } catch (error) {
        console.error('SAM2 分割失败:', error);
        this.$message.error(error.message || 'AI分割失败，请重试');
      } finally {
        this.sam2Processing = false;
      }
    },
    // SAM2 一键分割 (自动模式 - 已弃用)
    async runSam2Segment() {
      // 如果已有标注，需要确认
      if (this.rects.length > 0) {
        try {
          await this.$confirm(
            '使用AI分割将替换当前标注，是否继续？',
            '提示',
            {
              confirmButtonText: '继续',
              cancelButtonText: '取消',
              type: 'warning'
            }
          );
        } catch {
          return; // 用户取消
        }
      }

      this.sam2Processing = true;

      try {
        // 将当前图像转换为Blob
        const response = await fetch(this.imageUrl);
        const imageBlob = await response.blob();

        // 调用SAM2 API
        const result = await sam2Segment({
          imageFile: imageBlob,
          imageType: 'L3',
          patientId: this.patient,
          sliceIndex: this.date
        });

        // 显示处理时间和置信度
        const timeMsg = result.cached ? '(缓存)' : `(${result.processing_time_ms}ms)`;
        this.$message.success(
          `AI分割完成 ${timeMsg} 置信度: ${(result.confidence_score * 100).toFixed(1)}%`
        );

        // 解码mask_data (base64 PNG)
        const maskImage = new Image();
        maskImage.onload = () => {
          // 分析mask图像，提取白色区域作为矩形
          this.extractRectsFromMask(maskImage);
        };
        maskImage.onerror = () => {
          throw new Error('Mask图像加载失败');
        };
        maskImage.src = `data:image/png;base64,${result.mask_data}`;

      } catch (error) {
        console.error('SAM2 分割失败:', error);
        this.$message.error(error.message || 'AI分割失败，请重试');
      } finally {
        this.sam2Processing = false;
      }
    },
    // 从mask图像提取矩形区域
    extractRectsFromMask(maskImage) {
      console.log('Extracting rects from mask, image size:', maskImage.width, 'x', maskImage.height);

      const canvas = document.createElement('canvas');
      canvas.width = maskImage.width;
      canvas.height = maskImage.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(maskImage, 0, 0);

      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imageData.data;

      // 找到mask的边界
      let minX = canvas.width, minY = canvas.height, maxX = 0, maxY = 0;
      let hasWhitePixel = false;
      let whiteCount = 0;

      for (let y = 0; y < canvas.height; y++) {
        for (let x = 0; x < canvas.width; x++) {
          const idx = (y * canvas.width + x) * 4;
          const r = data[idx];

          // 白色像素 (假设mask的前景是白色或亮色)
          if (r > 128) {
            hasWhitePixel = true;
            whiteCount++;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
          }
        }
      }

      console.log('Mask analysis:', {
        hasWhitePixel,
        whiteCount,
        totalPixels: canvas.width * canvas.height,
        bounds: hasWhitePixel ? { minX, minY, maxX, maxY } : null
      });

      if (hasWhitePixel) {
        const rect = {
          x1: minX,
          y1: minY,
          x2: maxX,
          y2: maxY
        };

        // 清除现有矩形并添加新的
        this.rects = [rect];

        console.log('Created rect:', {
          x1: rect.x1,
          y1: rect.y1,
          x2: rect.x2,
          y2: rect.y2,
          width: rect.x2 - rect.x1,
          height: rect.y2 - rect.y1
        });

        // 确保在下一个tick后重绘，让Vue完成响应式更新
        this.$nextTick(() => {
          console.log('Calling redraw after nextTick');
          this.redraw();
        });

        this.$message.success(`已提取分割区域: ${maxX - minX} x ${maxY - minY} 像素`);
      } else {
        console.warn('No white pixels found in mask');
        this.$message.warning('未检测到分割区域，请手动标注');
      }
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
.draw-canvas.click-mode {
  cursor: pointer;
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