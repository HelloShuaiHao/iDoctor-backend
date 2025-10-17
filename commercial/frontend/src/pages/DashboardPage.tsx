import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ROUTES } from '@/utils/constants';
import { MainLayout } from '@/components/layout/MainLayout';
import {
  BarChart3,
  Key,
  CreditCard,
  Receipt,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate(ROUTES.LOGIN);
    }
  }, [isAuthenticated, navigate]);

  if (!user) {
    return null;
  }

  const dashboardCards = [
    {
      icon: BarChart3,
      title: '使用统计',
      description: '查看您的 API 使用情况和配额',
      action: () => navigate(ROUTES.USAGE_STATS),
      actionLabel: '查看详情',
      gradient: 'from-blue-500 to-cyan-500',
    },
    {
      icon: Key,
      title: 'API 密钥',
      description: '管理您的 API 访问密钥',
      action: () => navigate(ROUTES.API_KEYS),
      actionLabel: '管理密钥',
      gradient: 'from-purple-500 to-pink-500',
    },
    {
      icon: CreditCard,
      title: '订阅管理',
      description: '查看和管理您的订阅计划',
      action: () => navigate(ROUTES.MY_SUBSCRIPTION),
      actionLabel: '我的订阅',
      gradient: 'from-orange-500 to-red-500',
    },
    {
      icon: Receipt,
      title: '支付记录',
      description: '查看您的支付历史和账单',
      action: () => {},
      actionLabel: '查看记录',
      status: '开发中',
      gradient: 'from-green-500 to-emerald-500',
    },
  ];

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-12">
        {/* Welcome Section */}
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white text-2xl font-bold">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-3xl md:text-4xl font-bold">
                欢迎回来，{user.username}！
              </h1>
              <p className="text-muted-foreground mt-1">{user.email}</p>
            </div>
          </div>

          <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-secondary/5">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-primary" />
                    快速统计
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    您的账户状态和使用概览
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Dashboard Cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {dashboardCards.map((card, index) => {
            const Icon = card.icon;
            return (
              <Card
                key={index}
                className="group hover:shadow-xl transition-all duration-300 border-2 hover:border-primary/30"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div
                      className={`w-12 h-12 rounded-lg bg-gradient-to-br ${card.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}
                    >
                      <Icon className="h-6 w-6 text-white" />
                    </div>
                    {card.status && (
                      <span className="text-xs px-2 py-1 rounded-full bg-muted text-muted-foreground">
                        {card.status}
                      </span>
                    )}
                  </div>
                  <CardTitle className="text-xl">{card.title}</CardTitle>
                  <CardDescription className="text-base">
                    {card.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button
                    onClick={card.action}
                    variant={card.status ? 'outline' : 'default'}
                    className="w-full group-hover:bg-primary group-hover:text-primary-foreground transition-colors"
                    disabled={!!card.status}
                  >
                    {card.actionLabel}
                    {!card.status && <ArrowRight className="ml-2 h-4 w-4" />}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Quick Actions */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold mb-6">快速操作</h2>
          <div className="grid md:grid-cols-3 gap-4">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader>
                <CardTitle className="text-lg">查看文档</CardTitle>
                <CardDescription>
                  了解如何使用 iDoctor API
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader>
                <CardTitle className="text-lg">联系支持</CardTitle>
                <CardDescription>
                  获取技术支持和帮助
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader>
                <CardTitle className="text-lg">升级计划</CardTitle>
                <CardDescription>
                  探索更高级的订阅选项
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default DashboardPage;
