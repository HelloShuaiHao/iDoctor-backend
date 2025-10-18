import { authAPI } from './api';
import type {
  User,
  RegisterRequest,
  LoginRequest,
  TokenResponse,
  APIKey,
  CreateAPIKeyRequest,
  UpdateUserRequest,
} from '@/types/auth';

/**
 * 认证服务
 */
export const authService = {
  /**
   * 发送邮箱验证码
   */
  async sendVerificationCode(email: string): Promise<{ message: string; success: boolean }> {
    const response = await authAPI.post<{ message: string; success: boolean }>(
      '/auth/send-verification-code',
      { email }
    );
    return response.data;
  },

  /**
   * 验证邮箱验证码（可选，注册时也会验证）
   */
  async verifyEmail(email: string, code: string): Promise<{ message: string; success: boolean }> {
    const response = await authAPI.post<{ message: string; success: boolean }>(
      '/auth/verify-email',
      { email, code }
    );
    return response.data;
  },

  /**
   * 用户注册
   */
  async register(data: RegisterRequest): Promise<User> {
    const response = await authAPI.post<User>('/auth/register', data);
    return response.data;
  },

  /**
   * 用户登录
   */
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await authAPI.post<TokenResponse>('/auth/login', data);
    // 保存 Token 到 localStorage
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('refresh_token', response.data.refresh_token);
    return response.data;
  },

  /**
   * 刷新 Token
   */
  async refreshToken(): Promise<TokenResponse> {
    const response = await authAPI.post<TokenResponse>('/auth/refresh');
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('refresh_token', response.data.refresh_token);
    return response.data;
  },

  /**
   * 登出
   */
  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<User> {
    const response = await authAPI.get<User>('/users/me');
    return response.data;
  },

  /**
   * 更新当前用户信息
   */
  async updateCurrentUser(data: UpdateUserRequest): Promise<User> {
    const response = await authAPI.put<User>('/users/me', data);
    return response.data;
  },

  /**
   * 获取用户信息（通过 ID，管理员权限）
   */
  async getUserById(userId: string): Promise<User> {
    const response = await authAPI.get<User>(`/users/${userId}`);
    return response.data;
  },

  /**
   * 创建 API Key
   */
  async createAPIKey(data: CreateAPIKeyRequest): Promise<APIKey> {
    const response = await authAPI.post<APIKey>('/api-keys/', data);
    return response.data;
  },

  /**
   * 获取 API Key 列表
   */
  async getAPIKeys(): Promise<APIKey[]> {
    const response = await authAPI.get<APIKey[]>('/api-keys/');
    return response.data;
  },

  /**
   * 删除 API Key
   */
  async deleteAPIKey(keyId: string): Promise<void> {
    await authAPI.delete(`/api-keys/${keyId}`);
  },

  /**
   * 停用 API Key
   */
  async deactivateAPIKey(keyId: string): Promise<APIKey> {
    const response = await authAPI.patch<APIKey>(`/api-keys/${keyId}/deactivate`);
    return response.data;
  },

  /**
   * 检查是否已登录
   */
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  },
};
