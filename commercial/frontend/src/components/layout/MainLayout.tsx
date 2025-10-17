import { type FC, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import {
  Home,
  LayoutDashboard,
  CreditCard,
  User,
  LogOut,
  Menu,
  X,
  Sun,
  Moon
} from 'lucide-react';
import { useState } from 'react';
import { ROUTES } from '@/utils/constants';
import { useTheme } from '@/hooks/useTheme';

interface MainLayoutProps {
  children: ReactNode;
  showNavbar?: boolean;
}

export const MainLayout: FC<MainLayoutProps> = ({ children, showNavbar = true }) => {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate(ROUTES.HOME);
  };

  const navLinks = [
    { label: '首页', path: ROUTES.HOME, icon: Home },
    { label: '控制台', path: ROUTES.DASHBOARD, icon: LayoutDashboard, requireAuth: true },
    { label: '订阅计划', path: ROUTES.SUBSCRIPTION, icon: CreditCard },
  ];

  return (
    <div className="min-h-screen relative">
      {/* Background Gradient - positioned behind everything */}
      <div className="fixed inset-0 -z-10 bg-gradient-to-br from-blue-50 via-teal-50 to-cyan-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950" />

      {/* Navbar */}
      {showNavbar && (
        <nav className="sticky top-0 z-50 border-b bg-white/80 dark:bg-slate-950/80 backdrop-blur-md">
          <div className="container mx-auto px-4">
            <div className="flex h-16 items-center justify-between">
              {/* Logo */}
              <div
                className="flex items-center gap-2 cursor-pointer group"
                onClick={() => navigate(ROUTES.HOME)}
              >
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-bold text-xl">
                  i
                </div>
                <span className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                  iDoctor
                </span>
              </div>

              {/* Desktop Navigation */}
              <div className="hidden md:flex items-center gap-1">
                {navLinks.map((link) => {
                  if (link.requireAuth && !isAuthenticated) return null;
                  const Icon = link.icon;
                  return (
                    <Button
                      key={link.path}
                      variant="ghost"
                      onClick={() => navigate(link.path)}
                      className="gap-2"
                    >
                      <Icon className="h-4 w-4" />
                      {link.label}
                    </Button>
                  );
                })}
              </div>

              {/* User Menu */}
              <div className="hidden md:flex items-center gap-2">
                {/* Theme Toggle */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleTheme}
                  className="w-9 px-0"
                >
                  {theme === 'light' ? (
                    <Moon className="h-4 w-4" />
                  ) : (
                    <Sun className="h-4 w-4" />
                  )}
                </Button>

                {isAuthenticated && user ? (
                  <>
                    <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-accent">
                      <User className="h-4 w-4 text-accent-foreground" />
                      <span className="text-sm font-medium text-accent-foreground">
                        {user.username}
                      </span>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleLogout}>
                      <LogOut className="h-4 w-4 mr-2" />
                      退出
                    </Button>
                  </>
                ) : (
                  <>
                    <Button variant="outline" onClick={() => navigate(ROUTES.LOGIN)}>
                      登录
                    </Button>
                    <Button onClick={() => navigate(ROUTES.REGISTER)}>
                      注册
                    </Button>
                  </>
                )}
              </div>

              {/* Mobile Menu Button */}
              <Button
                variant="ghost"
                size="sm"
                className="md:hidden"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X /> : <Menu />}
              </Button>
            </div>

            {/* Mobile Menu */}
            {mobileMenuOpen && (
              <div className="md:hidden py-4 border-t">
                <div className="flex flex-col gap-2">
                  {navLinks.map((link) => {
                    if (link.requireAuth && !isAuthenticated) return null;
                    const Icon = link.icon;
                    return (
                      <Button
                        key={link.path}
                        variant="ghost"
                        onClick={() => {
                          navigate(link.path);
                          setMobileMenuOpen(false);
                        }}
                        className="justify-start gap-2"
                      >
                        <Icon className="h-4 w-4" />
                        {link.label}
                      </Button>
                    );
                  })}

                  {/* Mobile Theme Toggle */}
                  <Button
                    variant="ghost"
                    onClick={toggleTheme}
                    className="justify-start gap-2"
                  >
                    {theme === 'light' ? (
                      <>
                        <Moon className="h-4 w-4" />
                        深色模式
                      </>
                    ) : (
                      <>
                        <Sun className="h-4 w-4" />
                        浅色模式
                      </>
                    )}
                  </Button>

                  {isAuthenticated && user ? (
                    <>
                      <div className="px-3 py-2 mt-2 border-t">
                        <p className="text-sm text-muted-foreground mb-2">当前用户</p>
                        <p className="text-sm font-medium">{user.username}</p>
                      </div>
                      <Button
                        variant="outline"
                        onClick={() => {
                          handleLogout();
                          setMobileMenuOpen(false);
                        }}
                        className="justify-start gap-2"
                      >
                        <LogOut className="h-4 w-4" />
                        退出登录
                      </Button>
                    </>
                  ) : (
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        className="flex-1"
                        onClick={() => {
                          navigate(ROUTES.LOGIN);
                          setMobileMenuOpen(false);
                        }}
                      >
                        登录
                      </Button>
                      <Button
                        className="flex-1"
                        onClick={() => {
                          navigate(ROUTES.REGISTER);
                          setMobileMenuOpen(false);
                        }}
                      >
                        注册
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </nav>
      )}

      {/* Main Content */}
      <main>{children}</main>

      {/* Footer */}
      {showNavbar && (
        <footer className="border-t bg-white/50 dark:bg-slate-950/50 backdrop-blur-sm mt-16">
          <div className="container mx-auto px-4 py-8">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4">
              <div className="text-center md:text-left">
                <p className="text-sm text-muted-foreground">
                  © 2024 iDoctor. 专业医疗影像AI分析平台
                </p>
              </div>
              <div className="flex gap-6 text-sm text-muted-foreground">
                <a href="#" className="hover:text-primary transition-colors">关于我们</a>
                <a href="#" className="hover:text-primary transition-colors">服务条款</a>
                <a href="#" className="hover:text-primary transition-colors">隐私政策</a>
                <a href="#" className="hover:text-primary transition-colors">联系我们</a>
              </div>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
};
