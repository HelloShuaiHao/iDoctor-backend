import { type FC, useState, useEffect } from 'react';
import { PlanCard } from './PlanCard';
import { subscriptionService } from '@/services/subscriptionService';
import { type SubscriptionPlan } from '@/types/subscription';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2 } from 'lucide-react';

interface PlanListProps {
  onSelectPlan: (plan: SubscriptionPlan) => void;
  currentPlanId?: string;
  layout?: 'grid' | 'list';
}

export const PlanList: FC<PlanListProps> = ({
  onSelectPlan,
  currentPlanId,
  layout = 'grid'
}) => {
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

      // Sort plans by price (free first, then ascending)
      const sortedPlans = data.sort((a, b) => {
        if (a.price === 0) return -1;
        if (b.price === 0) return 1;
        return a.price - b.price;
      });

      setPlans(sortedPlans);
    } catch (err) {
      console.error('Failed to load plans:', err);
      setError('加载订阅计划失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  // Determine which plan is popular (usually the middle-priced one)
  const getPopularPlanId = () => {
    const activePlans = plans.filter(p => p.is_active && p.price > 0);
    if (activePlans.length === 0) return null;
    const middleIndex = Math.floor(activePlans.length / 2);
    return activePlans[middleIndex]?.id;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">加载订阅计划中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (plans.length === 0) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>暂无可用的订阅计划</AlertDescription>
      </Alert>
    );
  }

  const popularPlanId = getPopularPlanId();

  return (
    <div className={`
      ${layout === 'grid'
        ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
        : 'flex flex-col gap-4 max-w-2xl mx-auto'
      }
    `}>
      {plans.map((plan) => (
        <PlanCard
          key={plan.id}
          plan={plan}
          onSelect={onSelectPlan}
          isPopular={plan.id === popularPlanId}
          currentPlanId={currentPlanId}
        />
      ))}
    </div>
  );
};
