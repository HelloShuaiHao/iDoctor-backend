<template>
  <div style="padding: 40px; background: #f0f0f0; min-height: 100vh;">
    <h1 style="color: blue; font-size: 32px; margin-bottom: 20px;">🧪 3D 组件测试页面</h1>

    <div style="background: yellow; padding: 20px; margin-bottom: 20px; border: 3px solid orange;">
      <h2>✅ 步骤1: 如果你能看到这个黄色框，说明测试页面加载成功</h2>
    </div>

    <div style="background: lightblue; padding: 20px; margin-bottom: 20px; border: 3px solid blue;">
      <h2>步骤2: 测试简单组件</h2>
      <simple-test />
    </div>

    <div style="background: lightgreen; padding: 20px; margin-bottom: 20px; border: 3px solid green;">
      <h2>步骤3: 测试 Model3DViewer 组件</h2>
      <p>Patient: 1390714</p>
      <p>Date: 20251031</p>
      <p>MaskType: psoas</p>
      <model-3d-viewer
        patient="1390714"
        date="20251031"
        selected-mask-type="psoas"
      />
    </div>
  </div>
</template>

<script>
import Model3DViewer from './Model3DViewer.vue';

const SimpleTest = {
  template: '<div style="border: 3px solid purple; padding: 10px; background: pink;"><h3>✅ SimpleTest 内联组件渲染成功！</h3></div>'
};

export default {
  name: 'Test3D',
  components: {
    Model3DViewer,
    SimpleTest
  },
  mounted() {
    console.log('✅✅✅ Test3D 页面已挂载！');
    console.log('Model3DViewer 组件:', this.$options.components.Model3DViewer);
    console.log('SimpleTest 组件:', this.$options.components.SimpleTest);
  }
};
</script>

<style scoped>
</style>
