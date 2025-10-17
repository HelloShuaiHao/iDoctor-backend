import { paymentAPI } from './api';
import type {
  SubscriptionPlan,
  UserSubscription,
  CreatePlanRequest,
} from '@/types/subscription';

/**
 * 订阅服务
 */
export const subscriptionService = {
  /**
   * 获取所有订阅计划
   * @param activeOnly 是否只获取激活的计划
   */
  async getPlans(activeOnly = true): Promise<SubscriptionPlan[]> {
    const response = await paymentAPI.get<SubscriptionPlan[]>('/plans/', {
      params: { active_only: activeOnly },
    });
    return response.data;
  },

  /**
   * 获取订阅计划详情
   */
  async getPlanById(planId: string): Promise<SubscriptionPlan> {
    const response = await paymentAPI.get<SubscriptionPlan>(`/plans/${planId}`);
    return response.data;
  },

  /**
   * 创建订阅计划（管理员）
   */
  async createPlan(data: CreatePlanRequest): Promise<SubscriptionPlan> {
    const response = await paymentAPI.post<SubscriptionPlan>('/plans/', data);
    return response.data;
  },

  /**
   * 更新订阅计划（管理员）
   */
  async updatePlan(planId: string, data: Partial<CreatePlanRequest>): Promise<SubscriptionPlan> {
    const response = await paymentAPI.put<SubscriptionPlan>(`/plans/${planId}`, data);
    return response.data;
  },

  /**
   * 删除订阅计划（管理员）
   */
  async deletePlan(planId: string): Promise<void> {
    await paymentAPI.delete(`/plans/${planId}`);
  },

  /**
   * 获取用户订阅列表
   */
  async getUserSubscriptions(): Promise<UserSubscription[]> {
    const response = await paymentAPI.get<UserSubscription[]>('/subscriptions/');
    return response.data;
  },

  /**
   * 获取当前激活的订阅
   */
  async getActiveSubscription(): Promise<UserSubscription | null> {
    const subscriptions = await this.getUserSubscriptions();
    const active = subscriptions.find((sub) => sub.status === 'active');
    return active || null;
  },
};
