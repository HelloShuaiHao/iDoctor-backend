
import Vue from 'vue'
import App from './App'
import VueRouter from 'vue-router'
import axios from 'axios'
import Element from 'element-ui'
import echarts from "echarts"

import Content from './components/Content.vue'
import ResultsList from './components/ResultList.vue'
import ResultDetail from './components/ResultDetail.vue'
import Login from './components/Login.vue'

Vue.prototype.$echarts = echarts
import '../node_modules/element-ui/lib/theme-chalk/index.css'
import '../src/assets/style.css'
import './theme/index.css'

import { i18n } from './i18n'


Vue.use(Element)
Vue.config.productionTip = false
Vue.use(VueRouter)
Vue.prototype.$http = axios

const router = new VueRouter({
    routes: [
        { path: '/login', component: Login, meta: { title: '登录', requiresAuth: false } },
        { path: '/', component: Content, meta: { title: '上传与处理', requiresAuth: true } },
        { path: '/results', component: ResultsList, meta: { title: '结果列表', requiresAuth: true } },
        { path: '/results/:patient/:date', component: ResultDetail, meta: { title: '结果详情', requiresAuth: true } },
        { path: '*', redirect: '/' }
    ],
    // 为避免服务器未配 history 重写导致 404，建议开发用 hash 模式
    mode: 'hash'
})

// 路由守卫：检查登录状态
router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('access_token')
    const requiresAuth = to.meta.requiresAuth !== false  // 默认需要认证

    if (requiresAuth && !token) {
        // 需要登录但未登录，跳转到登录页
        next('/login')
    } else if (to.path === '/login' && token) {
        // 已登录但访问登录页，跳转到首页
        next('/')
    } else {
        next()
    }
})

// 全局注册（可选）
Vue.component('App', App)

new Vue({
    el: '#app',
    router,
    i18n,
    render: h => h(App)
})
