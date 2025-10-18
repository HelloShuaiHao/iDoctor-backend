// 用户相关类型
export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

// 注册请求
export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  verification_code: string;
}

// 登录请求
export interface LoginRequest {
  username_or_email: string;
  password: string;
}

// Token 响应
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// API Key
export interface APIKey {
  id: string;
  key_prefix: string;
  name: string;
  is_active: boolean;
  created_at: string;
  expires_at?: string;
  key?: string; // 仅在创建时返回
}

// 创建 API Key 请求
export interface CreateAPIKeyRequest {
  name: string;
  expires_at?: string;
}

// 更新用户请求
export interface UpdateUserRequest {
  email?: string;
  username?: string;
  password?: string;
}
