// 时间窗口类型
export type TimeWindow = 'minute' | 'hour' | 'day' | 'month' | 'year' | 'lifetime';

// 配额类型
export interface QuotaType {
  id: string;
  application_id: string;
  name: string;
  description?: string;
  unit: string; // 'requests', 'GB', etc.
  time_window: TimeWindow;
  created_at: string;
}

// 配额限制
export interface QuotaLimit {
  id: string;
  user_id: string;
  quota_type_id: string;
  limit_value: number;
  created_at: string;
  updated_at?: string;
  quota_type?: QuotaType;
}

// 配额使用记录
export interface QuotaUsage {
  id: string;
  user_id: string;
  quota_type_id: string;
  usage_value: number;
  window_start: string;
  window_end: string;
  created_at: string;
  quota_type?: QuotaType;
}

// 配额使用统计摘要
export interface QuotaSummary {
  quota_type: QuotaType;
  limit: number;
  used: number;
  remaining: number;
  percentage: number; // 使用百分比
  time_window: TimeWindow;
  window_start: string;
  window_end: string;
}

// 使用历史数据点（用于图表）
export interface UsageDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

// 配额使用趋势
export interface UsageTrend {
  quota_type: QuotaType;
  time_window: TimeWindow;
  data_points: UsageDataPoint[];
  total_usage: number;
  average_usage: number;
  peak_usage: number;
}
