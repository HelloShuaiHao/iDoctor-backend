/**
 * 应用常量
 */

export const APP_NAME = import.meta.env.VITE_APP_NAME || 'iDoctor 商业化平台';
export const APP_VERSION = import.meta.env.VITE_APP_VERSION || '1.0.0';

// API 端点（统一通过 Nginx 代理）
export const NGINX_BASE_URL = import.meta.env.VITE_NGINX_BASE_URL || 'http://localhost:3000';
export const IDOCTOR_APP_URL = import.meta.env.VITE_IDOCTOR_APP_URL || '/ctai';

// 路由路径
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  SUBSCRIPTION: '/subscription',
  MY_SUBSCRIPTION: '/my-subscription',
  PAYMENT: '/payment',
  PAYMENT_HISTORY: '/payment-history',
  API_KEYS: '/api-keys',
  USAGE_STATS: '/usage-stats',
} as const;

// 支付方式配置
export const PAYMENT_METHODS = {
  alipay: {
    name: '支付宝',
    icon: '💳',
    color: '#1677ff',
  },
  wechat: {
    name: '微信支付',
    icon: '💚',
    color: '#07c160',
  },
} as const;

// 支付状态配置
export const PAYMENT_STATUS = {
  pending: {
    text: '待支付',
    color: 'warning',
  },
  completed: {
    text: '已完成',
    color: 'success',
  },
  failed: {
    text: '失败',
    color: 'error',
  },
  refunded: {
    text: '已退款',
    color: 'default',
  },
} as const;

// 订阅周期配置
export const BILLING_CYCLES = {
  monthly: '月付',
  yearly: '年付',
  one_time: '一次性',
} as const;
