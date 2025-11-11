<template>
  <footer id="Footer">
    <p>{{ $t("footer.copyright", { year: currentYear }) }}</p>
  </footer>
</template>

<script>
export default {
  name: "Footer",
  data() {
    return {
      msg: "Copyright 2025 © 肌少症诊断系统 版权所有",
      currentYear: new Date().getFullYear(),
    };
  },
};
</script>
<style scoped>
#Footer {
  /*background:#F2F6FC;*/
  padding: 6px;
  border-radius: 5px;
  width: 80%;
  height: 80px;
  margin: 20px auto;
  margin-top: 140px;
}

p {
  color: #123737;
  text-align: center;
  margin: 30px auto;
  font-size: 1.1em;
}
</style>


