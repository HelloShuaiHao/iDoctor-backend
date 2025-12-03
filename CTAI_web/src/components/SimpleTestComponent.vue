<template>
  <div style="border: 3px solid purple; padding: 10px; background: pink;">
    <h3>✅ SimpleTestComponent 渲染成功！</h3>
    <p>如果你能看到这段文字，说明 .vue 文件组件可以正常工作</p>
  </div>
</template>

<script>
export default {
  name: 'SimpleTestComponent',
  mounted() {
    console.log('✅ SimpleTestComponent 已挂载！');
  }
};
</script>
