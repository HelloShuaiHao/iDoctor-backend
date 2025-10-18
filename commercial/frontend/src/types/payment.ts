// 支付方式
export type PaymentMethod = 'alipay' | 'wechat';

// 支付状态
export type PaymentStatus = 'pending' | 'completed' | 'failed' | 'refunded';

// 支付交易
export interface PaymentTransaction {
  id: string;
  user_id?: string;
  subscription_id?: string;
  amount: string;
  currency: string;
  payment_method: PaymentMethod;
  status: PaymentStatus;
  payment_url?: string;
  qr_code?: string;
  created_at: string;
  updated_at?: string;
}

// 创建支付请求
export interface CreatePaymentRequest {
  amount: number;
  currency: string;
  payment_method: PaymentMethod;
  subscription_id?: string;
}

// 退款请求
export interface RefundRequest {
  refund_amount: number;
  reason: string;
}

// 支付历史记录项
export interface PaymentRecord {
  id: string;
  order_id: string;
  amount: number;
  currency: string;
  payment_method: string;
  status: string;
  created_at: string;
  updated_at: string;
  plan_name?: string;
  description?: string;
  invoice_url?: string;
}
