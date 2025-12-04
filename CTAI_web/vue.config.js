module.exports = {
  lintOnSave: undefined,
  // CTAI_web 独立运行在根路径，通过 Nginx /ctai 代理访问
  publicPath: './',
  outputDir: undefined,
  assetsDir: undefined,
  runtimeCompiler: undefined,
  productionSourceMap: undefined,
  parallel: false,
  css: undefined,
  devServer: {
    port: 7500,
    host: '0.0.0.0',
    disableHostCheck: true // 允许所有主机访问
  }
}