import { type FC, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { quotaService } from '@/services/quotaService';
import { useAuth } from '@/context/AuthContext';
import { ROUTES } from '@/utils/constants';
import type { QuotaSummary, UsageTrend } from '@/types/quota';
import {
  BarChart3,
  TrendingUp,
  Database,
  Zap,
  Calendar,
  AlertCircle,
  Loader2,
  RefreshCw,
  ArrowUpRight,
  Clock,
  Infinity,
} from 'lucide-react';

const UsageStatsPage: FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [quotaSummaries, setQuotaSummaries] = useState<QuotaSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate(ROUTES.LOGIN);
      return;
    }
    loadQuotaData();
  }, [isAuthenticated, navigate]);

  const loadQuotaData = async () => {
    try {
      setLoading(true);
      setError(null);
      const summaries = await quotaService.getQuotaSummary();
      setQuotaSummaries(summaries);
    } catch (err: any) {
      console.error('Failed to load quota data:', err);
      setError('加载配额数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadQuotaData();
    setRefreshing(false);
  };

  const getQuotaIcon = (name: string) => {
    if (name.includes('API') || name.includes('调用')) return BarChart3;
    if (name.includes('存储') || name.includes('空间')) return Database;
    if (name.includes('AI') || name.includes('分析')) return Zap;
    return BarChart3;
  };

  const getTimeWindowLabel = (window: string) => {
    const labels: Record<string, string> = {
      minute: '每分钟',
      hour: '每小时',
      day: '每天',
      month: '每月',
      year: '每年',
      lifetime: '终身',
    };
    return labels[window] || window;
  };

  const getTimeWindowIcon = (window: string) => {
    if (window === 'lifetime') return Infinity;
    return Clock;
  };

  const getStatusColor = (percentage: number) => {
    if (percentage >= 90) return 'text-destructive';
    if (percentage >= 70) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getProgressColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-destructive';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-primary';
  };

  const formatValue = (value: number, unit: string) => {
    if (unit === 'GB') {
      return `${value.toFixed(2)} ${unit}`;
    }
    return `${Math.floor(value).toLocaleString()} ${unit}`;
  };

  const calculateTotalUsagePercentage = () => {
    if (quotaSummaries.length === 0) return 0;
    const total = quotaSummaries.reduce((sum, q) => sum + q.percentage, 0);
    return Math.round(total / quotaSummaries.length);
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="container mx-auto px-4 py-12">
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-3 text-muted-foreground">加载中...</span>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-12 max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">使用统计</h1>
            <p className="text-muted-foreground">
              查看您的配额使用情况和历史记录
            </p>
          </div>
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                刷新中...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                刷新数据
              </>
            )}
          </Button>
        </div>

        {/* Error Display */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Overview Card */}
        <Card className="mb-6 border-2 border-primary/20 bg-gradient-to-r from-primary/5 to-secondary/5">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl">总体使用情况</CardTitle>
                <CardDescription className="mt-1">
                  所有配额的平均使用率
                </CardDescription>
              </div>
              <div className="text-right">
                <div className={`text-4xl font-bold ${getStatusColor(calculateTotalUsagePercentage())}`}>
                  {calculateTotalUsagePercentage()}%
                </div>
                <p className="text-sm text-muted-foreground mt-1">平均使用率</p>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Quota Cards Grid */}
        {quotaSummaries.length === 0 ? (
          <Card className="border-2 border-dashed">
            <CardContent className="py-12">
              <div className="text-center space-y-4">
                <div className="w-20 h-20 rounded-full bg-muted mx-auto flex items-center justify-center">
                  <BarChart3 className="h-10 w-10 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">暂无使用数据</h3>
                  <p className="text-muted-foreground mb-6">
                    开始使用 API 后，您的使用统计将显示在这里
                  </p>
                </div>
                <Button onClick={() => navigate(ROUTES.SUBSCRIPTION)}>
                  查看订阅计划
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {quotaSummaries.map((quota) => {
              const Icon = getQuotaIcon(quota.quota_type.name);
              const TimeIcon = getTimeWindowIcon(quota.time_window);
              const isWarning = quota.percentage >= 70;
              const isCritical = quota.percentage >= 90;

              return (
                <Card
                  key={quota.quota_type.id}
                  className={`transition-all hover:shadow-lg ${
                    isCritical
                      ? 'border-destructive/50 bg-destructive/5'
                      : isWarning
                      ? 'border-yellow-500/50 bg-yellow-50/50 dark:bg-yellow-950/20'
                      : ''
                  }`}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                          <Icon className="h-6 w-6 text-white" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">
                            {quota.quota_type.name}
                          </CardTitle>
                          <CardDescription className="mt-1">
                            {quota.quota_type.description}
                          </CardDescription>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Usage Progress */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">使用进度</span>
                        <span className={`font-semibold ${getStatusColor(quota.percentage)}`}>
                          {quota.percentage.toFixed(1)}%
                        </span>
                      </div>
                      <Progress
                        value={quota.percentage}
                        className="h-2"
                      />
                    </div>

                    {/* Usage Details */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground mb-1">已使用</p>
                        <p className="font-semibold">
                          {formatValue(quota.used, quota.quota_type.unit)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground mb-1">剩余</p>
                        <p className="font-semibold">
                          {formatValue(quota.remaining, quota.quota_type.unit)}
                        </p>
                      </div>
                    </div>

                    {/* Total Limit */}
                    <div className="border-t pt-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">总配额</span>
                        <span className="font-semibold">
                          {formatValue(quota.limit, quota.quota_type.unit)}
                        </span>
                      </div>
                    </div>

                    {/* Time Window */}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <TimeIcon className="h-3 w-3" />
                      <span>{getTimeWindowLabel(quota.time_window)}</span>
                    </div>

                    {/* Warning Messages */}
                    {isCritical && (
                      <Alert variant="destructive" className="py-2">
                        <AlertCircle className="h-3 w-3" />
                        <AlertDescription className="text-xs">
                          配额即将用尽，请考虑升级订阅
                        </AlertDescription>
                      </Alert>
                    )}
                    {isWarning && !isCritical && (
                      <Alert className="py-2 border-yellow-500 bg-yellow-50 dark:bg-yellow-950/30">
                        <AlertCircle className="h-3 w-3 text-yellow-600" />
                        <AlertDescription className="text-xs text-yellow-600 dark:text-yellow-500">
                          配额使用较高，请注意
                        </AlertDescription>
                      </Alert>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Usage Trend Section (Placeholder for future implementation) */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-6">使用趋势</h2>
          <Card>
            <CardContent className="py-12">
              <div className="text-center text-muted-foreground">
                <TrendingUp className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>使用趋势图表功能开发中...</p>
                <p className="text-sm mt-2">
                  即将支持：日、周、月使用趋势图表，峰值分析等功能
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="mt-8 grid md:grid-cols-2 gap-4">
          <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => navigate(ROUTES.MY_SUBSCRIPTION)}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold mb-1">升级订阅</h3>
                  <p className="text-sm text-muted-foreground">
                    获取更多配额和功能
                  </p>
                </div>
                <ArrowUpRight className="h-5 w-5 text-primary" />
              </div>
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => navigate(ROUTES.API_KEYS)}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold mb-1">API 密钥管理</h3>
                  <p className="text-sm text-muted-foreground">
                    管理您的 API 访问密钥
                  </p>
                </div>
                <ArrowUpRight className="h-5 w-5 text-primary" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Info Notice */}
        <Alert className="mt-8">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            配额数据每小时更新一次。如需实时查看最新使用情况，请点击"刷新数据"按钮。
          </AlertDescription>
        </Alert>
      </div>
    </MainLayout>
  );
};

export default UsageStatsPage;
