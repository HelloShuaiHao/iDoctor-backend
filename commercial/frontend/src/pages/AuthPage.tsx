import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Mail, Lock, User, AlertCircle, CheckCircle2 } from 'lucide-react';
import { ROUTES } from '@/utils/constants';
import { MainLayout } from '@/components/layout/MainLayout';

interface AuthPageProps {
  mode?: 'login' | 'register';
}

interface LoginForm {
  email: string;
  password: string;
}

interface RegisterForm {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

interface FormErrors {
  username?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

const AuthPage: React.FC<AuthPageProps> = ({ mode = 'login' }) => {
  const navigate = useNavigate();
  const { login, register } = useAuth();

  const [activeTab, setActiveTab] = useState<'login' | 'register'>(mode);
  const [loginForm, setLoginForm] = useState<LoginForm>({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState<RegisterForm>({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const [loginErrors, setLoginErrors] = useState<FormErrors>({});
  const [registerErrors, setRegisterErrors] = useState<FormErrors>({});
  const [submitStatus, setSubmitStatus] = useState<{
    type: 'success' | 'error' | null;
    message: string;
  }>({ type: null, message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validateLoginForm = (): boolean => {
    const errors: FormErrors = {};

    if (!loginForm.email) {
      errors.email = '请输入邮箱或用户名';
    }

    if (!loginForm.password) {
      errors.password = '请输入密码';
    } else if (loginForm.password.length < 6) {
      errors.password = '密码至少需要6个字符';
    }

    setLoginErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const validateRegisterForm = (): boolean => {
    const errors: FormErrors = {};

    if (!registerForm.username) {
      errors.username = '请输入用户名';
    } else if (registerForm.username.length < 3) {
      errors.username = '用户名至少需要3个字符';
    }

    if (!registerForm.email) {
      errors.email = '请输入邮箱';
    } else if (!validateEmail(registerForm.email)) {
      errors.email = '请输入有效的邮箱地址';
    }

    if (!registerForm.password) {
      errors.password = '请输入密码';
    } else if (registerForm.password.length < 6) {
      errors.password = '密码至少需要6个字符';
    }

    if (!registerForm.confirmPassword) {
      errors.confirmPassword = '请确认密码';
    } else if (registerForm.password !== registerForm.confirmPassword) {
      errors.confirmPassword = '两次输入的密码不一致';
    }

    setRegisterErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitStatus({ type: null, message: '' });

    if (!validateLoginForm()) return;

    setIsSubmitting(true);
    try {
      await login({
        username_or_email: loginForm.email,
        password: loginForm.password,
      });

      setSubmitStatus({
        type: 'success',
        message: '登录成功！正在跳转...',
      });

      setTimeout(() => {
        navigate(ROUTES.DASHBOARD);
      }, 1000);
    } catch (error: any) {
      console.error('Login error:', error);

      // 处理不同类型的错误响应
      let errorMessage = '登录失败，请检查用户名和密码';

      if (error.response?.data) {
        const data = error.response.data;

        // FastAPI 验证错误格式
        if (Array.isArray(data.detail)) {
          errorMessage = data.detail.map((err: any) => err.msg).join(', ');
        }
        // 字符串类型的 detail
        else if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        }
        // 对象类型的 detail
        else if (data.detail && typeof data.detail === 'object') {
          errorMessage = JSON.stringify(data.detail);
        }
      }

      setSubmitStatus({
        type: 'error',
        message: errorMessage,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitStatus({ type: null, message: '' });

    if (!validateRegisterForm()) return;

    setIsSubmitting(true);
    try {
      await register({
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password,
      });

      setSubmitStatus({
        type: 'success',
        message: '注册成功！正在跳转...',
      });

      setTimeout(() => {
        navigate(ROUTES.DASHBOARD);
      }, 1000);
    } catch (error: any) {
      console.error('Registration error:', error);

      // 处理不同类型的错误响应
      let errorMessage = '注册失败，请稍后重试';

      if (error.response?.data) {
        const data = error.response.data;

        // FastAPI 验证错误格式
        if (Array.isArray(data.detail)) {
          errorMessage = data.detail.map((err: any) => err.msg).join(', ');
        }
        // 字符串类型的 detail
        else if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        }
        // 对象类型的 detail
        else if (data.detail && typeof data.detail === 'object') {
          errorMessage = JSON.stringify(data.detail);
        }
      }

      setSubmitStatus({
        type: 'error',
        message: errorMessage,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <MainLayout>
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-lg backdrop-blur-sm bg-white/95 dark:bg-slate-900/95">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            iDoctor 商业化平台
          </CardTitle>
          <CardDescription className="text-center">
            登录或注册以继续使用
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            onValueChange={(value) => {
              setActiveTab(value as 'login' | 'register');
              setSubmitStatus({ type: null, message: '' });
              setLoginErrors({});
              setRegisterErrors({});
            }}
            className="w-full"
          >
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="login">登录</TabsTrigger>
              <TabsTrigger value="register">注册</TabsTrigger>
            </TabsList>

            {/* 登录表单 */}
            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="login-email">邮箱/用户名</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="login-email"
                      type="text"
                      placeholder="请输入邮箱或用户名"
                      className={`pl-10 ${loginErrors.email ? 'border-destructive' : ''}`}
                      value={loginForm.email}
                      onChange={(e) => {
                        setLoginForm({ ...loginForm, email: e.target.value });
                        setLoginErrors({ ...loginErrors, email: undefined });
                      }}
                      disabled={isSubmitting}
                    />
                  </div>
                  {loginErrors.email && (
                    <p className="text-sm text-destructive flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {loginErrors.email}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="login-password">密码</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="login-password"
                      type="password"
                      placeholder="请输入密码"
                      className={`pl-10 ${loginErrors.password ? 'border-destructive' : ''}`}
                      value={loginForm.password}
                      onChange={(e) => {
                        setLoginForm({ ...loginForm, password: e.target.value });
                        setLoginErrors({ ...loginErrors, password: undefined });
                      }}
                      disabled={isSubmitting}
                    />
                  </div>
                  {loginErrors.password && (
                    <p className="text-sm text-destructive flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {loginErrors.password}
                    </p>
                  )}
                </div>

                {submitStatus.type && activeTab === 'login' && (
                  <Alert variant={submitStatus.type === 'error' ? 'destructive' : 'default'}>
                    {submitStatus.type === 'success' ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <AlertCircle className="h-4 w-4" />
                    )}
                    <AlertDescription>{submitStatus.message}</AlertDescription>
                  </Alert>
                )}

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? '登录中...' : '登录'}
                </Button>
              </form>
            </TabsContent>

            {/* 注册表单 */}
            <TabsContent value="register">
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="register-username">用户名</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="register-username"
                      type="text"
                      placeholder="请输入用户名"
                      className={`pl-10 ${registerErrors.username ? 'border-destructive' : ''}`}
                      value={registerForm.username}
                      onChange={(e) => {
                        setRegisterForm({ ...registerForm, username: e.target.value });
                        setRegisterErrors({ ...registerErrors, username: undefined });
                      }}
                      disabled={isSubmitting}
                    />
                  </div>
                  {registerErrors.username && (
                    <p className="text-sm text-destructive flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {registerErrors.username}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="register-email">邮箱</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="register-email"
                      type="email"
                      placeholder="请输入邮箱"
                      className={`pl-10 ${registerErrors.email ? 'border-destructive' : ''}`}
                      value={registerForm.email}
                      onChange={(e) => {
                        setRegisterForm({ ...registerForm, email: e.target.value });
                        setRegisterErrors({ ...registerErrors, email: undefined });
                      }}
                      disabled={isSubmitting}
                    />
                  </div>
                  {registerErrors.email && (
                    <p className="text-sm text-destructive flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {registerErrors.email}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="register-password">密码</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="register-password"
                      type="password"
                      placeholder="请输入密码"
                      className={`pl-10 ${registerErrors.password ? 'border-destructive' : ''}`}
                      value={registerForm.password}
                      onChange={(e) => {
                        setRegisterForm({ ...registerForm, password: e.target.value });
                        setRegisterErrors({ ...registerErrors, password: undefined });
                      }}
                      disabled={isSubmitting}
                    />
                  </div>
                  {registerErrors.password && (
                    <p className="text-sm text-destructive flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {registerErrors.password}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="register-confirm-password">确认密码</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="register-confirm-password"
                      type="password"
                      placeholder="请再次输入密码"
                      className={`pl-10 ${registerErrors.confirmPassword ? 'border-destructive' : ''}`}
                      value={registerForm.confirmPassword}
                      onChange={(e) => {
                        setRegisterForm({
                          ...registerForm,
                          confirmPassword: e.target.value,
                        });
                        setRegisterErrors({
                          ...registerErrors,
                          confirmPassword: undefined,
                        });
                      }}
                      disabled={isSubmitting}
                    />
                  </div>
                  {registerErrors.confirmPassword && (
                    <p className="text-sm text-destructive flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {registerErrors.confirmPassword}
                    </p>
                  )}
                </div>

                {submitStatus.type && activeTab === 'register' && (
                  <Alert variant={submitStatus.type === 'error' ? 'destructive' : 'default'}>
                    {submitStatus.type === 'success' ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <AlertCircle className="h-4 w-4" />
                    )}
                    <AlertDescription>{submitStatus.message}</AlertDescription>
                  </Alert>
                )}

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? '注册中...' : '注册'}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      </div>
    </MainLayout>
  );
};

export default AuthPage;
