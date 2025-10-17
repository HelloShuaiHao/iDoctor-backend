// 计费周期
export type BillingCycle = 'monthly' | 'yearly' | 'one_time';

// 配额类型
export type QuotaType = 'processing_count' | 'storage_gb' | 'api_calls';

// 订阅计划 (匹配后端 API 返回格式)
export interface SubscriptionPlan {
  id: string;
  name: string;
  description: string;
  price: string; // 字符串格式，如 "99.00"
  currency: string;
  billing_cycle: BillingCycle;
  quota_type: QuotaType;
  quota_limit: number;
  features: Record<string, any>; // 对象格式，如 {"api_access": true}
  is_active: boolean;
  created_at: string;
  updated_at?: string;

  // 前端扩展字段（可选）
  duration_days?: number; // 从 billing_cycle 计算得出
}

// 用户订阅
export interface UserSubscription {
  id: string;
  user_id: string;
  plan_id: string;
  status: 'active' | 'cancelled' | 'expired';
  start_date: string;
  end_date?: string;
  auto_renew: boolean;
  created_at: string;
  updated_at?: string;
  plan?: SubscriptionPlan;
}

// 创建订阅计划请求（管理员）
export interface CreatePlanRequest {
  name: string;
  description: string;
  price: number;
  currency: string;
  billing_cycle: BillingCycle;
  quota_type: QuotaType;
  quota_limit: number;
  features?: Record<string, any>;
}
