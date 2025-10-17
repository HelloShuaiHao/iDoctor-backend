import { type FC, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LayoutGrid, List } from 'lucide-react';
import { PlanList } from '@/components/subscription/PlanList';
import { PlanComparison } from '@/components/subscription/PlanComparison';
import { Button } from '@/components/ui/button';
import { type SubscriptionPlan } from '@/types/subscription';
import { useAuth } from '@/hooks/useAuth';

const SubscriptionPage: FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [viewMode, setViewMode] = useState<'grid' | 'comparison'>('grid');

  // TODO: 获取用户当前订阅
  const currentPlanId = undefined; // 暂时为空，待实现用户订阅查询

  const handleSelectPlan = (plan: SubscriptionPlan) => {
    console.log('Selected plan:', plan);

    // 如果未登录，先跳转到登录页面
    if (!user) {
      navigate('/auth', { state: { from: '/subscription', selectedPlan: plan } });
      return;
    }

    // 跳转到支付页面，传递订阅计划信息
    navigate('/payment', { state: { plan } });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header Section */}
      <div className="border-b bg-muted/30">
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold mb-2">订阅计划</h1>
              <p className="text-muted-foreground">
                选择适合您的订阅计划，享受更多功能和服务
              </p>
            </div>

            {/* View Toggle */}
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('grid')}
              >
                <LayoutGrid className="h-4 w-4 mr-2" />
                卡片视图
              </Button>
              <Button
                variant={viewMode === 'comparison' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('comparison')}
              >
                <List className="h-4 w-4 mr-2" />
                对比视图
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Plans Section */}
      <div className="container mx-auto px-4 py-12">
        {viewMode === 'grid' ? (
          <PlanList
            onSelectPlan={handleSelectPlan}
            currentPlanId={currentPlanId}
            layout="grid"
          />
        ) : (
          <PlanComparison
            onSelectPlan={handleSelectPlan}
            currentPlanId={currentPlanId}
          />
        )}
      </div>

      {/* FAQ or Additional Info */}
      <div className="border-t bg-muted/20 py-12">
        <div className="container mx-auto px-4">
          <h2 className="text-2xl font-bold mb-6 text-center">常见问题</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <div className="space-y-2">
              <h3 className="font-semibold">如何升级订阅？</h3>
              <p className="text-sm text-muted-foreground">
                您可以随时升级到更高级别的订阅计划，差额部分会按比例计算。
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">支持哪些支付方式？</h3>
              <p className="text-sm text-muted-foreground">
                我们支持支付宝和微信支付，安全便捷。
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">可以退款吗？</h3>
              <p className="text-sm text-muted-foreground">
                支持按比例退款，具体请查看退款政策或联系客服。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionPage;
