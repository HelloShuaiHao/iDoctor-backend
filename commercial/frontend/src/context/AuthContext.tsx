import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { authService } from '@services/authService';
import type { User, LoginRequest, RegisterRequest } from '@/types/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // 初始化：检查是否已登录
  useEffect(() => {
    const initAuth = async () => {
      // 1. 检查 URL 参数中的 token（从 CTAI_web 跳转过来）
      const searchParams = new URLSearchParams(window.location.search);
      const urlToken = searchParams.get('token');

      if (urlToken) {
        // 保存 token 到 localStorage
        localStorage.setItem('access_token', urlToken);
        // 清除 URL 参数，避免刷新时重复处理
        window.history.replaceState({}, '', window.location.pathname);
        console.log('从 URL 参数获取到 token，已保存到 localStorage');
      }

      // 2. 正常的认证检查
      if (authService.isAuthenticated()) {
        try {
          const userData = await authService.getCurrentUser();
          setUser(userData);
        } catch (error) {
          console.error('获取用户信息失败:', error);
          authService.logout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (credentials: LoginRequest) => {
    setLoading(true);
    try {
      await authService.login(credentials);
      const userData = await authService.getCurrentUser();
      setUser(userData);
    } finally {
      setLoading(false);
    }
  };

  const register = async (data: RegisterRequest) => {
    setLoading(true);
    try {
      await authService.register(data);
      // 注册成功后自动登录
      await login({
        username_or_email: data.email,
        password: data.password,
      });
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  const refreshUser = async () => {
    if (authService.isAuthenticated()) {
      try {
        const userData = await authService.getCurrentUser();
        setUser(userData);
      } catch (error) {
        console.error('刷新用户信息失败:', error);
      }
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    register,
    logout,
    refreshUser,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
