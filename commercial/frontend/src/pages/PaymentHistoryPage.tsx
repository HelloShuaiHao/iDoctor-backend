import { type FC, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { paymentService } from '@/services/paymentService';
import { useAuth } from '@/context/AuthContext';
import { ROUTES, PAYMENT_STATUS } from '@/utils/constants';
import type { PaymentRecord } from '@/types/payment';
import {
  Receipt,
  Download,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  CreditCard,
  Calendar,
  DollarSign,
  FileText,
} from 'lucide-react';

const PaymentHistoryPage: FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate(ROUTES.LOGIN);
      return;
    }
    loadPayments();
  }, [isAuthenticated, navigate]);

  const loadPayments = async () => {
    try {
      setLoading(true);
      setError(null);

      // 调用真实 API 获取支付历史
      const records = await paymentService.getPaymentHistory();
      setPayments(records);
    } catch (err: any) {
      console.error('Failed to load payment history:', err);
      setError(err.response?.data?.detail || '加载支付记录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadPayments();
    setRefreshing(false);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <Badge className="bg-green-500">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            已完成
          </Badge>
        );
      case 'pending':
        return (
          <Badge variant="secondary">
            <Clock className="h-3 w-3 mr-1" />
            待支付
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            失败
          </Badge>
        );
      case 'refunded':
        return (
          <Badge variant="outline">
            <RefreshCw className="h-3 w-3 mr-1" />
            已退款
          </Badge>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getPaymentMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      alipay: '支付宝',
      wechat: '微信支付',
      card: '银行卡',
    };
    return labels[method] || method;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (amount: number, currency: string) => {
    const symbols: Record<string, string> = {
      CNY: '¥',
      USD: '$',
      EUR: '€',
    };
    return `${symbols[currency] || currency} ${amount.toFixed(2)}`;
  };

  const calculateTotalSpent = () => {
    return payments
      .filter(p => p.status === 'completed')
      .reduce((sum, p) => sum + p.amount, 0);
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
      <div className="container mx-auto px-4 py-12 max-w-6xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">支付记录</h1>
            <p className="text-muted-foreground">
              查看您的所有支付历史和账单
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
                刷新
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

        {/* Summary Cards */}
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>总支出</CardDescription>
              <CardTitle className="text-3xl">
                ¥{calculateTotalSpent().toFixed(2)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center text-sm text-muted-foreground">
                <DollarSign className="h-4 w-4 mr-1" />
                所有已完成的支付
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardDescription>总交易数</CardDescription>
              <CardTitle className="text-3xl">{payments.length}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center text-sm text-muted-foreground">
                <Receipt className="h-4 w-4 mr-1" />
                包含所有状态
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardDescription>成功率</CardDescription>
              <CardTitle className="text-3xl">
                {payments.length > 0
                  ? Math.round((payments.filter(p => p.status === 'completed').length / payments.length) * 100)
                  : 0}%
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center text-sm text-muted-foreground">
                <CheckCircle2 className="h-4 w-4 mr-1" />
                支付成功率
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Payment List */}
        {payments.length === 0 ? (
          <Card className="border-2 border-dashed">
            <CardContent className="py-12">
              <div className="text-center space-y-4">
                <div className="w-20 h-20 rounded-full bg-muted mx-auto flex items-center justify-center">
                  <Receipt className="h-10 w-10 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">暂无支付记录</h3>
                  <p className="text-muted-foreground mb-6">
                    您还没有任何支付记录
                  </p>
                </div>
                <Button onClick={() => navigate(ROUTES.SUBSCRIPTION)}>
                  选择订阅计划
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {payments.map((payment) => (
              <Card key={payment.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    {/* Left: Payment Info */}
                    <div className="flex items-start gap-4 flex-1">
                      <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center">
                        <CreditCard className="h-6 w-6 text-primary" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-lg">
                            {payment.plan_name || payment.description || '订阅支付'}
                          </h3>
                          {getStatusBadge(payment.status)}
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <FileText className="h-3 w-3" />
                            订单号: {payment.order_id}
                          </div>
                          <div className="flex items-center gap-1">
                            <CreditCard className="h-3 w-3" />
                            {getPaymentMethodLabel(payment.payment_method)}
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(payment.created_at)}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Right: Amount & Actions */}
                    <div className="text-right space-y-2">
                      <div className="text-2xl font-bold">
                        {formatCurrency(payment.amount, payment.currency)}
                      </div>
                      {payment.invoice_url && (
                        <Button variant="outline" size="sm">
                          <Download className="h-4 w-4 mr-1" />
                          下载发票
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Info Note */}
        <Alert className="mt-8">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            支付记录保存180天。如需更早的记录，请联系客服。
          </AlertDescription>
        </Alert>
      </div>
    </MainLayout>
  );
};

export default PaymentHistoryPage;
