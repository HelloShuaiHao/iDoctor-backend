import { paymentAPI } from './api';
import type {
  PaymentTransaction,
  CreatePaymentRequest,
  RefundRequest,
  PaymentRecord,
} from '@/types/payment';

/**
 * 支付服务
 */
export const paymentService = {
  /**
   * 创建支付订单
   */
  async createPayment(data: CreatePaymentRequest): Promise<PaymentTransaction> {
    const response = await paymentAPI.post<PaymentTransaction>('/payments/', data);
    return response.data;
  },

  /**
   * 获取支付状态
   */
  async getPaymentStatus(paymentId: string): Promise<PaymentTransaction> {
    const response = await paymentAPI.get<PaymentTransaction>(`/payments/${paymentId}`);
    return response.data;
  },

  /**
   * 申请退款
   */
  async requestRefund(paymentId: string, data: RefundRequest): Promise<PaymentTransaction> {
    const response = await paymentAPI.post<PaymentTransaction>(
      `/payments/${paymentId}/refund`,
      data
    );
    return response.data;
  },

  /**
   * 获取支付历史
   */
  async getPaymentHistory(statusFilter?: string): Promise<PaymentRecord[]> {
    const params = statusFilter ? { status_filter: statusFilter } : {};
    const response = await paymentAPI.get<PaymentRecord[]>('/payments/', { params });
    return response.data;
  },

  /**
   * 轮询支付状态
   * @param paymentId 支付 ID
   * @param onStatusChange 状态变化回调
   * @param interval 轮询间隔（毫秒），默认 2000ms
   * @param maxAttempts 最大尝试次数，默认 60 次（2分钟）
   */
  async pollPaymentStatus(
    paymentId: string,
    onStatusChange: (payment: PaymentTransaction) => void,
    interval = 2000,
    maxAttempts = 60
  ): Promise<void> {
    let attempts = 0;

    const poll = async (): Promise<void> => {
      try {
        const payment = await this.getPaymentStatus(paymentId);
        onStatusChange(payment);

        // 如果支付完成或失败，停止轮询
        if (payment.status === 'completed' || payment.status === 'failed') {
          return;
        }

        // 继续轮询
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, interval);
        }
      } catch (error) {
        console.error('轮询支付状态失败:', error);
      }
    };

    await poll();
  },
};
