<template>
  <div class="model-3d-viewer" style="border: 5px solid green; background: white; padding: 20px; min-height: 200px;">
    <h1 style="color: green; font-size: 24px; font-weight: bold;">✅ Model3DViewer 组件已加载！</h1>
    <p style="font-size: 16px;">Patient: {{ patient }}</p>
    <p style="font-size: 16px;">Date: {{ date }}</p>
    <p style="font-size: 16px;">MaskType: {{ selectedMaskType }}</p>
    <p style="color: red; font-size: 16px;">如果你能看到这段文字，说明组件渲染成功！</p>
  </div>
</template>

<script>
export default {
  name: 'Model3DViewer',
  props: {
    patient: {
      type: String,
      default: 'unknown'
    },
    date: {
      type: String,
      default: 'unknown'
    },
    selectedMaskType: {
      type: String,
      default: 'psoas'
    }
  },
  created() {
    console.log('[Model3DViewer] ✅ created 钩子调用');
  },
  beforeMount() {
    console.log('[Model3DViewer] ✅ beforeMount 钩子调用');
  },
  mounted() {
    console.log('[Model3DViewer] ✅✅✅ mounted 钩子调用！');
    console.log('[Model3DViewer] Props:', {
      patient: this.patient,
      date: this.date,
      selectedMaskType: this.selectedMaskType
    });
    console.log('[Model3DViewer] $el:', this.$el);
  },
  errorCaptured(err, vm, info) {
    console.error('[Model3DViewer] ❌ 捕获到错误:', err);
    console.error('[Model3DViewer] 错误信息:', info);
    return false;
  }
};
</script>

<style scoped>
.model-3d-viewer {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
}
</style>
