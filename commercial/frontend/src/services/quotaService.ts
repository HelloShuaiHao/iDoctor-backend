import { authAPI } from './api';
import type {
  QuotaSummary,
  QuotaUsage,
  UsageTrend,
  QuotaLimit,
} from '@/types/quota';

/**
 * 配额管理服务
 *
 * 注意：部分API端点可能尚未在后端实现，需要根据实际情况调整
 */
export const quotaService = {
  /**
   * 获取当前用户的配额使用摘要
   */
  async getQuotaSummary(): Promise<QuotaSummary[]> {
    try {
      const response = await authAPI.get<QuotaSummary[]>('/quota/summary');
      return response.data;
    } catch (error: any) {
      // 如果API未实现，返回模拟数据
      if (error.response?.status === 404) {
        return getMockQuotaSummary();
      }
      throw error;
    }
  },

  /**
   * 获取配额使用历史
   */
  async getQuotaUsageHistory(
    quotaTypeId?: string,
    startDate?: string,
    endDate?: string
  ): Promise<QuotaUsage[]> {
    try {
      const params = new URLSearchParams();
      if (quotaTypeId) params.append('quota_type_id', quotaTypeId);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const response = await authAPI.get<QuotaUsage[]>(
        `/quota/usage?${params.toString()}`
      );
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return [];
      }
      throw error;
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
      const response = await authAPI.get<UsageTrend>(
        `/quota/trend/${quotaTypeId}?days=${days}`
      );
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return getMockUsageTrend(quotaTypeId, days);
      }
      throw error;
    }
  },

  /**
   * 获取用户的配额限制
   */
  async getQuotaLimits(): Promise<QuotaLimit[]> {
    try {
      const response = await authAPI.get<QuotaLimit[]>('/quota/limits');
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return [];
      }
      throw error;
    }
  },
};

/**
 * 模拟数据 - 配额摘要
 * 用于后端API尚未实现时的演示
 */
function getMockQuotaSummary(): QuotaSummary[] {
  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);

  return [
    {
      quota_type: {
        id: '1',
        application_id: 'idoctor',
        name: 'API 调用',
        description: 'API 接口调用次数',
        unit: '次',
        time_window: 'month',
        created_at: new Date().toISOString(),
      },
      limit: 10000,
      used: 6543,
      remaining: 3457,
      percentage: 65.43,
      time_window: 'month',
      window_start: monthStart.toISOString(),
      window_end: monthEnd.toISOString(),
    },
    {
      quota_type: {
        id: '2',
        application_id: 'idoctor',
        name: '存储空间',
        description: '数据存储空间',
        unit: 'GB',
        time_window: 'lifetime',
        created_at: new Date().toISOString(),
      },
      limit: 100,
      used: 45.6,
      remaining: 54.4,
      percentage: 45.6,
      time_window: 'lifetime',
      window_start: new Date(2024, 0, 1).toISOString(),
      window_end: new Date(2099, 11, 31).toISOString(),
    },
    {
      quota_type: {
        id: '3',
        application_id: 'idoctor',
        name: 'AI 分析',
        description: 'AI 医学影像分析次数',
        unit: '次',
        time_window: 'day',
        created_at: new Date().toISOString(),
      },
      limit: 50,
      used: 23,
      remaining: 27,
      percentage: 46,
      time_window: 'day',
      window_start: new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString(),
      window_end: new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59).toISOString(),
    },
  ];
}

/**
 * 模拟数据 - 使用趋势
 */
function getMockUsageTrend(quotaTypeId: string, days: number): UsageTrend {
  const dataPoints = [];
  const now = new Date();

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    dataPoints.push({
      timestamp: date.toISOString(),
      value: Math.floor(Math.random() * 300) + 100,
      label: date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }),
    });
  }

  const totalUsage = dataPoints.reduce((sum, point) => sum + point.value, 0);

  return {
    quota_type: {
      id: quotaTypeId,
      application_id: 'idoctor',
      name: 'API 调用',
      unit: '次',
      time_window: 'day',
      created_at: new Date().toISOString(),
    },
    time_window: 'day',
    data_points: dataPoints,
    total_usage: totalUsage,
    average_usage: Math.floor(totalUsage / days),
    peak_usage: Math.max(...dataPoints.map(p => p.value)),
  };
}
