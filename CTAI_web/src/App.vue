<template>
  <div id="app">
    <div class="hero-bg"></div>
    <app-header />
    <!-- 用路由承载页面：/、/results、/results/:patient/:date -->
    <router-view />
    <app-footer />
  </div>
</template>

<script>
import Header from "./components/Header";
import Footer from "./components/Footer";
// ...existing code...
export default {
  name: "肌少症诊断系统",
  components: {
    "app-header": Header,
    "app-footer": Footer,
  },
};
</script>

// ...existing code...
<style>
body {
  background: #f6fafd;
  margin: 0;
  padding: 0;
  min-height: 100vh;
}
#app {
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

/* Apple 风简约柔和背景 (替换原大图) */
.hero-bg {
  position: fixed;
  inset: 0;
  overflow: hidden;
  z-index: 0;
  pointer-events: none;
  /* 主基底渐变：淡蓝 -> 偏白 */
  background: linear-gradient(
    145deg,
    #f5faff 0%,
    #edf6ff 30%,
    #eaf5ff 55%,
    #e8f2fb 100%
  );
}

/* 彩色柔光斑 */
.hero-bg::before,
.hero-bg::after {
  content: "";
  position: absolute;
  width: 1200px;
  height: 1200px;
  top: -400px;
  left: -300px;
  background: radial-gradient(
      circle at 35% 35%,
      rgba(10, 132, 255, 0.42),
      rgba(10, 132, 255, 0) 60%
    ),
    radial-gradient(
      circle at 70% 60%,
      rgba(52, 199, 89, 0.35),
      rgba(52, 199, 89, 0) 65%
    );
  filter: blur(120px) saturate(140%);
  opacity: 0.85;
  animation: floatA 26s ease-in-out infinite;
}

.hero-bg::after {
  top: auto;
  bottom: -480px;
  left: auto;
  right: -360px;
  width: 1100px;
  height: 1100px;
  background: radial-gradient(
      circle at 40% 40%,
      rgba(94, 92, 230, 0.4),
      rgba(94, 92, 230, 0) 62%
    ),
    radial-gradient(
      circle at 70% 70%,
      rgba(255, 159, 10, 0.35),
      rgba(255, 159, 10, 0) 70%
    );
  animation: floatB 30s ease-in-out infinite;
  mix-blend-mode: plus-lighter;
}

/* 轻微噪点提升质感 */
.hero-bg::marker, /* 占位避免选择器警告 */
.hero-bg > i {
  display: none;
}
.hero-bg::before,
.hero-bg::after,
.hero-bg > .noise {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.hero-bg .noise-layer {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    rgba(255, 255, 255, 0.02) 0 2px,
    rgba(0, 0, 0, 0.02) 2px 4px
  );
  mix-blend-mode: overlay;
  opacity: 0.25;
}

/* 浮动动画 */
@keyframes floatA {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(60px, 40px, 0) scale(1.05);
  }
}
@keyframes floatB {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(-70px, -50px, 0) scale(1.07);
  }
}

/* 深色模式调色 */
@media (prefers-color-scheme: dark) {
  .hero-bg {
    background: linear-gradient(140deg, #0f1720 0%, #121d27 45%, #0e161e 100%);
  }
  .hero-bg::before {
    background: radial-gradient(
        circle at 35% 35%,
        rgba(10, 132, 255, 0.55),
        rgba(10, 132, 255, 0) 60%
      ),
      radial-gradient(
        circle at 70% 60%,
        rgba(52, 199, 89, 0.45),
        rgba(52, 199, 89, 0) 65%
      );
    filter: blur(140px) saturate(160%);
  }
  .hero-bg::after {
    background: radial-gradient(
        circle at 40% 40%,
        rgba(94, 92, 230, 0.55),
        rgba(94, 92, 230, 0) 62%
      ),
      radial-gradient(
        circle at 70% 70%,
        rgba(255, 159, 10, 0.45),
        rgba(255, 159, 10, 0) 70%
      );
  }
}

#app > *:not(.hero-bg) {
  position: relative;
  z-index: 1;
}

.header,
.top-title {
  color: #222;
  text-shadow: 0 2px 6px #fff8;
}
@media (prefers-color-scheme: dark) {
  .header,
  .top-title {
    color: #f5f9ff;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.6);
  }
}
</style>