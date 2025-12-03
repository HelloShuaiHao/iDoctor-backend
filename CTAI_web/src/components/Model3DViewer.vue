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
      required: true
    },
    date: {
      type: String,
      required: true
    },
    selectedMaskType: {
      type: String,
      default: 'psoas'
    }
  },
  mounted() {
    console.log('[3D组件-简化版] ✅ 组件已挂载！');
    console.log('[3D组件-简化版] Props:', {
      patient: this.patient,
      date: this.date,
      selectedMaskType: this.selectedMaskType
    });
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
