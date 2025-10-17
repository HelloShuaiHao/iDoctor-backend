import { type FC, useState, useEffect } from 'react';
import { Check, X, Loader2 } from 'lucide-react';
import { subscriptionService } from '@/services/subscriptionService';
import { type SubscriptionPlan } from '@/types/subscription';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface PlanComparisonProps {
  onSelectPlan: (plan: SubscriptionPlan) => void;
  currentPlanId?: string;
}

interface ComparisonFeature {
  label: string;
  key: keyof SubscriptionPlan | 'custom';
  formatter?: (plan: SubscriptionPlan) => string | boolean;
}

const COMPARISON_FEATURES: ComparisonFeature[] = [
  {
    label: '价格',
    key: 'price',
    formatter: (plan) => {
      const priceNum = parseFloat(plan.price);
      return priceNum === 0 ? '免费' : `¥${priceNum.toFixed(0)}`;
    }
  },
  {
    label: '计费周期',
    key: 'billing_cycle',
    formatter: (plan) => {
      const cycleMap: Record<string, string> = {
        'monthly': '按月',
        'yearly': '按年',
        'one_time': '一次性'
      };
      return cycleMap[plan.billing_cycle] || plan.billing_cycle;
    }
  },
  {
    label: '配额限制',
    key: 'quota_limit',
    formatter: (plan) => `${plan.quota_limit} 次`
  },
  {
    label: '当前可用',
    key: 'is_active',
    formatter: (plan) => plan.is_active
  }
];

export const PlanComparison: FC<PlanComparisonProps> = ({ onSelectPlan, currentPlanId }) => {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await subscriptionService.getPlans();

      // Sort plans by price
      const sortedPlans = data.sort((a, b) => {
        if (a.price === 0) return -1;
        if (b.price === 0) return 1;
        return a.price - b.price;
      });

      setPlans(sortedPlans);
    } catch (err) {
      console.error('Failed to load plans:', err);
      setError('加载订阅计划失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (plans.length === 0) {
    return (
      <Alert>
        <AlertDescription>暂无可用的订阅计划</AlertDescription>
      </Alert>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-4 text-left font-semibold min-w-[150px]">功能特性</th>
              {plans.map((plan) => (
                <th key={plan.id} className="p-4 text-center font-semibold min-w-[150px]">
                  <div className="flex flex-col gap-2">
                    <span className="text-lg">{plan.name}</span>
                    {currentPlanId === plan.id && (
                      <span className="text-xs font-normal text-primary">当前计划</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {COMPARISON_FEATURES.map((feature, index) => (
              <tr key={index} className="border-b hover:bg-muted/20 transition-colors">
                <td className="p-4 font-medium text-sm">{feature.label}</td>
                {plans.map((plan) => {
                  const value = feature.formatter ? feature.formatter(plan) : plan[feature.key];
                  const isBool = typeof value === 'boolean';

                  return (
                    <td key={plan.id} className="p-4 text-center">
                      {isBool ? (
                        value ? (
                          <Check className="h-5 w-5 text-green-600 mx-auto" />
                        ) : (
                          <X className="h-5 w-5 text-muted-foreground mx-auto" />
                        )
                      ) : (
                        <span className="text-sm">{value as string}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}

            {/* Action row */}
            <tr className="bg-muted/30">
              <td className="p-4 font-medium">操作</td>
              {plans.map((plan) => (
                <td key={plan.id} className="p-4">
                  <Button
                    className="w-full"
                    variant={currentPlanId === plan.id ? 'outline' : 'default'}
                    onClick={() => onSelectPlan(plan)}
                    disabled={currentPlanId === plan.id || !plan.is_active}
                  >
                    {currentPlanId === plan.id ? '当前使用' : !plan.is_active ? '暂不可用' : '选择'}
                  </Button>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  );
};
