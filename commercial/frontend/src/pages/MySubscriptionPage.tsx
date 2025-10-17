import { type FC, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { subscriptionService } from '@/services/subscriptionService';
import type { UserSubscription, SubscriptionPlan } from '@/types/subscription';
import {
  CreditCard,
  Calendar,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  RefreshCw,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { ROUTES } from '@/utils/constants';

const MySubscriptionPage: FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [plan, setPlan] = useState<SubscriptionPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSubscription();
  }, []);

  const loadSubscription = async () => {
    try {
      setLoading(true);
      setError(null);

      // 获取当前激活的订阅
      const activeSub = await subscriptionService.getActiveSubscription();

      if (activeSub) {
        setSubscription(activeSub);
        // 获取订阅计划详情
        const planData = await subscriptionService.getPlanById(activeSub.plan_id);
        setPlan(planData);
      } else {
        setSubscription(null);
        setPlan(null);
      }
    } catch (err) {
      console.error('Failed to load subscription:', err);
      setError('加载订阅信息失败');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return (
          <Badge className="bg-green-500">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            激活中
          </Badge>
        );
      case 'expired':
        return (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            已过期
          </Badge>
        );
      case 'cancelled':
        return (
          <Badge variant="outline">
            <XCircle className="h-3 w-3 mr-1" />
            已取消
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary">
            <Clock className="h-3 w-3 mr-1" />
            {status}
          </Badge>
        );
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="container mx-auto px-4 py-12">
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-3 text-muted-foreground">加载中...</span>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (error) {
    return (
      <MainLayout>
        <div className="container mx-auto px-4 py-12">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">我的订阅</h1>
          <p className="text-muted-foreground">
            管理您的订阅计划和配额使用情况
          </p>
        </div>

        {/* Current Subscription */}
        {subscription && plan ? (
          <div className="space-y-6">
            {/* Subscription Card */}
            <Card className="border-2 border-primary/20">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                      <CreditCard className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <CardTitle className="text-2xl">{plan.name}</CardTitle>
                      <CardDescription className="mt-1">
                        {plan.description}
                      </CardDescription>
                    </div>
                  </div>
                  {getStatusBadge(subscription.status)}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">订阅时间</p>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-primary" />
                      <span className="font-medium">
                        {formatDate(subscription.start_date)}
                      </span>
                    </div>
                  </div>

                  {subscription.end_date && (
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">到期时间</p>
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-destructive" />
                        <span className="font-medium">
                          {formatDate(subscription.end_date)}
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">配额限制</p>
                    <p className="text-2xl font-bold text-primary">
                      {plan.quota_limit} 次
                    </p>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">价格</p>
                    <p className="text-2xl font-bold">
                      {plan.price === '0' ? '免费' : `¥${parseFloat(plan.price).toFixed(2)}`}
                      {plan.price !== '0' && (
                        <span className="text-sm text-muted-foreground font-normal ml-2">
                          / {plan.billing_cycle === 'monthly' ? '月' : plan.billing_cycle === 'yearly' ? '年' : '次'}
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                <div className="pt-4 border-t flex gap-3">
                  <Button
                    onClick={() => navigate(ROUTES.SUBSCRIPTION)}
                    variant="outline"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    更换订阅
                  </Button>

                  {subscription.status === 'active' && plan.price !== '0' && (
                    <Button onClick={() => navigate(ROUTES.PAYMENT, { state: { plan, subscription_id: subscription.id } })}>
                      <CreditCard className="h-4 w-4 mr-2" />
                      续费订阅
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Usage Stats */}
            <Card>
              <CardHeader>
                <CardTitle>使用统计</CardTitle>
                <CardDescription>
                  您的配额使用情况和历史记录
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>配额使用统计功能开发中...</p>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          /* No Subscription */
          <Card className="border-2 border-dashed">
            <CardContent className="pt-12 pb-12">
              <div className="text-center space-y-4">
                <div className="w-20 h-20 rounded-full bg-muted mx-auto flex items-center justify-center">
                  <CreditCard className="h-10 w-10 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">暂无订阅</h3>
                  <p className="text-muted-foreground mb-6">
                    您还没有订阅任何计划，选择一个适合您的计划开始使用
                  </p>
                </div>
                <Button
                  size="lg"
                  onClick={() => navigate(ROUTES.SUBSCRIPTION)}
                >
                  浏览订阅计划
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </MainLayout>
  );
};

export default MySubscriptionPage;
