import { type FC } from 'react';
import { Check } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { type SubscriptionPlan } from '@/types/subscription';

interface PlanCardProps {
  plan: SubscriptionPlan;
  onSelect: (plan: SubscriptionPlan) => void;
  isPopular?: boolean;
  currentPlanId?: string;
}

export const PlanCard: FC<PlanCardProps> = ({ plan, onSelect, isPopular = false, currentPlanId }) => {
  const isCurrentPlan = currentPlanId === plan.id;

  // Parse features from object to array
  const features = plan.features ? Object.entries(plan.features).map(([key, value]) => {
    if (typeof value === 'boolean' && value) {
      // 转换特性名称为友好显示
      const featureNames: Record<string, string> = {
        'api_access': 'API 访问',
        'priority_support': '优先支持',
        'advanced_features': '高级功能',
      };
      return featureNames[key] || key;
    }
    return null;
  }).filter(Boolean) as string[] : [];

  // Format price display
  const priceNum = parseFloat(plan.price);
  const priceDisplay = priceNum === 0 ? '免费' : `¥${priceNum.toFixed(0)}`;

  // Calculate period display from billing_cycle
  const periodDisplay = plan.billing_cycle === 'monthly' ? '/月' :
                        plan.billing_cycle === 'yearly' ? '/年' :
                        plan.billing_cycle === 'one_time' ? '' : '';

  return (
    <Card className={`relative flex flex-col ${isPopular ? 'border-primary border-2 shadow-lg' : ''}`}>
      {isPopular && (
        <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary">
          最受欢迎
        </Badge>
      )}

      <CardHeader className="text-center pb-4">
        <CardTitle className="text-2xl">{plan.name}</CardTitle>
        <CardDescription className="text-sm mt-2">{plan.description}</CardDescription>
      </CardHeader>

      <CardContent className="flex-1">
        <div className="text-center mb-6">
          <div className="flex items-baseline justify-center gap-1">
            <span className="text-4xl font-bold">{priceDisplay}</span>
            {plan.price > 0 && <span className="text-muted-foreground">{periodDisplay}</span>}
          </div>
        </div>

        <div className="space-y-3">
          {features.length > 0 ? (
            features.map((feature, index) => (
              <div key={index} className="flex items-start gap-2">
                <Check className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                <span className="text-sm">{feature}</span>
              </div>
            ))
          ) : (
            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="flex items-start gap-2">
                <Check className="h-5 w-5 text-primary shrink-0" />
                <span>配额: {plan.quota_limit} 次</span>
              </div>
              <div className="flex items-start gap-2">
                <Check className="h-5 w-5 text-primary shrink-0" />
                <span>周期: {plan.billing_cycle === 'monthly' ? '按月' : plan.billing_cycle === 'yearly' ? '按年' : '一次性'}</span>
              </div>
              {plan.is_active && (
                <div className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-primary shrink-0" />
                  <span>当前可用</span>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter>
        <Button
          className="w-full"
          variant={isCurrentPlan ? 'outline' : isPopular ? 'default' : 'secondary'}
          onClick={() => onSelect(plan)}
          disabled={isCurrentPlan || !plan.is_active}
        >
          {isCurrentPlan ? '当前计划' : !plan.is_active ? '暂不可用' : '选择计划'}
        </Button>
      </CardFooter>
    </Card>
  );
};
