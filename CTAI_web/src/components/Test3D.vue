<template>
  <div style="padding: 40px; background: #f0f0f0; min-height: 100vh;">
    <h1 style="color: blue; font-size: 32px; margin-bottom: 20px;">🧪 3D 组件测试页面</h1>

    <div style="background: yellow; padding: 20px; margin-bottom: 20px; border: 3px solid orange;">
      <h2>✅ 步骤1: 如果你能看到这个黄色框，说明测试页面加载成功</h2>
    </div>

    <div style="background: lightblue; padding: 20px; margin-bottom: 20px; border: 3px solid blue;">
      <h2>步骤2: 测试简单组件</h2>
      <simple-test-component />
    </div>

    <div style="background: lightgreen; padding: 20px; margin-bottom: 20px; border: 3px solid green;">
      <h2>步骤3A: 测试 Model3DViewer 组件 (kebab-case)</h2>
      <p>Patient: 1390714</p>
      <p>Date: 20251031</p>
      <p>MaskType: psoas</p>
      <model-3d-viewer
        patient="1390714"
        date="20251031"
        selected-mask-type="psoas"
      />
    </div>

    <div style="background: lightcoral; padding: 20px; margin-bottom: 20px; border: 3px solid darkred;">
      <h2>步骤3B: 测试 Model3DViewer 组件 (PascalCase)</h2>
      <Model3DViewer
        patient="1390714"
        date="20251031"
        :selected-mask-type="'psoas'"
      />
    </div>

    <div style="background: pink; padding: 20px; margin-bottom: 20px; border: 3px solid red;">
      <h2>步骤4: 测试全新的 Model3DViewerNew 组件</h2>
      <Model3DViewerNew />
    </div>
  </div>
</template>

<script>
import Model3DViewer from './Model3DViewer.vue';
import Model3DViewerNew from './Model3DViewerNew.vue';
import SimpleTestComponent from './SimpleTestComponent.vue';

export default {
  name: 'Test3D',
  components: {
    Model3DViewer,
    Model3DViewerNew,
    SimpleTestComponent
  },
  mounted() {
    console.log('✅✅✅ Test3D 页面已挂载！');
    console.log('所有已注册组件:', Object.keys(this.$options.components));
    console.log('Model3DViewer:', this.$options.components.Model3DViewer);
    console.log('SimpleTestComponent:', this.$options.components.SimpleTestComponent);

    // 检查组件是否有错误
    this.$nextTick(() => {
      const simpleTest = this.$el.querySelector('[style*="purple"]');
      const model3d = this.$el.querySelector('.model-3d-viewer');
      console.log('SimpleTestComponent DOM 元素:', simpleTest ? '✅ 找到' : '❌ 未找到');
      console.log('Model3DViewer DOM 元素:', model3d ? '✅ 找到' : '❌ 未找到');
    });
  }
};
</script>

<style scoped>
</style>
