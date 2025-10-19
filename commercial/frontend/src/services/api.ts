import axios, { type AxiosInstance } from 'axios';

// 创建认证 API 实例
export const authAPI: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_AUTH_API_URL || 'http://localhost:9001',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 创建支付 API 实例
export const paymentAPI: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_PAYMENT_API_URL || 'http://localhost:9002',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 创建 iDoctor 主应用 API 实例（用于配额、处理等功能）
export const idoctorAPI: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_IDOCTOR_API_URL || 'http://localhost:4200',
  timeout: 30000, // 处理请求可能需要更长时间
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：添加 Token
authAPI.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

paymentAPI.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理 Token 过期
authAPI.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Token 过期，尝试刷新
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${import.meta.env.VITE_AUTH_API_URL}/refresh`,
            {},
            {
              headers: {
                Authorization: `Bearer ${refreshToken}`,
              },
            }
          );

          const { access_token, refresh_token } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);

          // 重试原请求
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return authAPI(originalRequest);
        } catch (refreshError) {
          // 刷新失败，清除 Token 并跳转登录
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        // 没有 refresh token，直接跳转登录
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// 支付 API 也添加类似的响应拦截器
paymentAPI.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${import.meta.env.VITE_AUTH_API_URL}/refresh`,
            {},
            {
              headers: {
                Authorization: `Bearer ${refreshToken}`,
              },
            }
          );

          const { access_token, refresh_token } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);

          // 重试原请求
          error.config.headers.Authorization = `Bearer ${access_token}`;
          return paymentAPI(error.config);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }

    return Promise.reject(error);
  }
);

// iDoctor API 拦截器
idoctorAPI.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

idoctorAPI.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${import.meta.env.VITE_AUTH_API_URL}/refresh`,
            {},
            {
              headers: {
                Authorization: `Bearer ${refreshToken}`,
              },
            }
          );

          const { access_token, refresh_token } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);

          // 重试原请求
          error.config.headers.Authorization = `Bearer ${access_token}`;
          return idoctorAPI(error.config);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }

    return Promise.reject(error);
  }
);
