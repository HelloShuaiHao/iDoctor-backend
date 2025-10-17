import { useState } from 'react';
import { paymentService } from '@services/paymentService';
import type {
  PaymentTransaction,
  CreatePaymentRequest,
  RefundRequest,
} from '@/types/payment';

interface UsePaymentReturn {
  payment: PaymentTransaction | null;
  loading: boolean;
  error: string | null;
  createPayment: (data: CreatePaymentRequest) => Promise<PaymentTransaction | null>;
  checkPaymentStatus: (paymentId: string) => Promise<PaymentTransaction | null>;
  requestRefund: (paymentId: string, data: RefundRequest) => Promise<void>;
  startPolling: (paymentId: string, onComplete?: (payment: PaymentTransaction) => void) => void;
  reset: () => void;
}

export const usePayment = (): UsePaymentReturn => {
  const [payment, setPayment] = useState<PaymentTransaction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createPayment = async (data: CreatePaymentRequest): Promise<PaymentTransaction | null> => {
    setLoading(true);
    setError(null);

    try {
      const result = await paymentService.createPayment(data);
      setPayment(result);
      return result;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || '创建支付订单失败';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const checkPaymentStatus = async (paymentId: string): Promise<PaymentTransaction | null> => {
    setLoading(true);
    setError(null);

    try {
      const result = await paymentService.getPaymentStatus(paymentId);
      setPayment(result);
      return result;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || '获取支付状态失败';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const requestRefund = async (paymentId: string, data: RefundRequest): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const result = await paymentService.requestRefund(paymentId, data);
      setPayment(result);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || '申请退款失败';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const startPolling = (
    paymentId: string,
    onComplete?: (payment: PaymentTransaction) => void
  ): void => {
    paymentService.pollPaymentStatus(paymentId, (updatedPayment) => {
      setPayment(updatedPayment);

      if (
        updatedPayment.status === 'completed' ||
        updatedPayment.status === 'failed'
      ) {
        onComplete?.(updatedPayment);
      }
    });
  };

  const reset = () => {
    setPayment(null);
    setError(null);
    setLoading(false);
  };

  return {
    payment,
    loading,
    error,
    createPayment,
    checkPaymentStatus,
    requestRefund,
    startPolling,
    reset,
  };
};
