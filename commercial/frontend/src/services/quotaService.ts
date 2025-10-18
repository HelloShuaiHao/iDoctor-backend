import { idoctorAPI } from './api';
import type {
  QuotaSummary,
  QuotaUsage,
  UsageTrend,
  QuotaLimit,
} from '@/types/quota';

/**
 * 配额管理服务
 *
 * 使用 iDoctor 主应用的配额管理 API（/admin/quotas）
 */
export const quotaService = {
  /**
   * 获取当前用户的配额使用摘要
   */
  async getQuotaSummary(): Promise<QuotaSummary[]> {
    try {
      const response = await idoctorAPI.get('/admin/quotas/users/me');

      // 后端返回的是 UserQuotaSummary 格式
      // 需要转换为前端需要的 QuotaSummary[] 格式
      const data = response.data;

      if (data.quotas && Array.isArray(data.quotas)) {
        return data.quotas.map((quota: any) => ({
          quota_type: {
            id: quota.type_id || quota.type_key,
            application_id: 'idoctor',
            name: quota.name || quota.type_key,
            description: quota.description || '',
            unit: quota.unit || '次',
            time_window: quota.time_window || 'month',
            created_at: new Date().toISOString(),
          },
          limit: quota.limit,
          used: quota.used,
          remaining: quota.limit - quota.used,
          percentage: quota.usage_percent || (quota.used / quota.limit) * 100,
          time_window: quota.time_window || 'month',
          window_start: new Date().toISOString(),
          window_end: new Date().toISOString(),
        }));
      }

      return [];
    } catch (error: any) {
      console.error('Failed to load quota summary:', error);
      throw error;
    }
  },

  /**
   * 获取配额使用历史
   */
  async getQuotaUsageHistory(
    quotaTypeId?: string,
    startDate?: string,
    endDate?: string,
    limit?: number
  ): Promise<QuotaUsage[]> {
    try {
      const params = new URLSearchParams();
      if (quotaTypeId) params.append('quota_type', quotaTypeId);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (limit) params.append('limit', limit.toString());

      const response = await idoctorAPI.get(
        `/admin/quotas/usage-logs?${params.toString()}`
      );

      // 转换后端数据格式到前端格式
      const logs = response.data;
      if (Array.isArray(logs)) {
        return logs.map((log: any) => ({
          id: log.id,
          user_id: log.user_id,
          quota_type_id: log.quota_type,
          amount: log.amount,
          timestamp: log.created_at,
          metadata: log.metadata || {},
        }));
      }

      return [];
    } catch (error: any) {
      console.error('Failed to load usage history:', error);
      return [];
    }
  },

  /**
   * 获取配额使用趋势
   */
  async getUsageTrend(
    quotaTypeId: string,
    days: number = 30
  ): Promise<UsageTrend> {
    try {
      const response = await idoctorAPI.get(
        `/admin/quotas/statistics/${quotaTypeId}?days=${days}`
      );

      const data = response.data;

      // 如果后端返回了数据，转换格式
      if (data) {
        return {
          quota_type: {
            id: quotaTypeId,
            application_id: 'idoctor',
            name: data.quota_type_name || quotaTypeId,
            unit: data.unit || '次',
            time_window: 'day',
            created_at: new Date().toISOString(),
          },
          time_window: 'day',
          data_points: data.data_points || [],
          total_usage: data.total || 0,
          average_usage: data.average || 0,
          peak_usage: data.peak || 0,
        };
      }

      // 如果没有数据，返回空趋势
      return {
        quota_type: {
          id: quotaTypeId,
          application_id: 'idoctor',
          name: quotaTypeId,
          unit: '次',
          time_window: 'day',
          created_at: new Date().toISOString(),
        },
        time_window: 'day',
        data_points: [],
        total_usage: 0,
        average_usage: 0,
        peak_usage: 0,
      };
    } catch (error: any) {
      console.error('Failed to load usage trend:', error);
      // 返回空数据而不是抛出错误
      return {
        quota_type: {
          id: quotaTypeId,
          application_id: 'idoctor',
          name: quotaTypeId,
          unit: '次',
          time_window: 'day',
          created_at: new Date().toISOString(),
        },
        time_window: 'day',
        data_points: [],
        total_usage: 0,
        average_usage: 0,
        peak_usage: 0,
      };
    }
  },

  /**
   * 获取用户的配额限制
   */
  async getQuotaLimits(): Promise<QuotaLimit[]> {
    try {
      const response = await idoctorAPI.get('/admin/quotas/users/me');
      const data = response.data;

      if (data.quotas && Array.isArray(data.quotas)) {
        return data.quotas.map((quota: any) => ({
          quota_type_id: quota.type_id || quota.type_key,
          limit: quota.limit,
          time_window: quota.time_window || 'month',
        }));
      }

      return [];
    } catch (error: any) {
      console.error('Failed to load quota limits:', error);
      return [];
    }
  },
};
