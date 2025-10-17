import { type FC, useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { usePayment } from '@/hooks/usePayment';
import { useAuth } from '@/context/AuthContext';
import { ROUTES, PAYMENT_METHODS } from '@/utils/constants';
import type { SubscriptionPlan } from '@/types/subscription';
import type { PaymentMethod } from '@/types/payment';
import {
  CreditCard,
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowLeft,
  AlertCircle,
  QrCode,
  Clock,
} from 'lucide-react';

interface LocationState {
  plan?: SubscriptionPlan;
  subscription_id?: string;
}

const PaymentPage: FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated } = useAuth();
  const { payment, loading, error, createPayment, startPolling, reset } = usePayment();

  const state = location.state as LocationState | null;
  const plan = state?.plan;
  const subscription_id = state?.subscription_id;

  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod>('alipay');
  const [paymentStep, setPaymentStep] = useState<'select' | 'processing' | 'polling' | 'success' | 'failed'>('select');

  useEffect(() => {
    // 检查登录状态
    if (!isAuthenticated) {
      navigate(ROUTES.LOGIN, { state: { from: ROUTES.PAYMENT } });
      return;
    }

    // 检查是否有订阅计划信息
    if (!plan) {
      navigate(ROUTES.SUBSCRIPTION);
    }
  }, [isAuthenticated, plan, navigate]);

  useEffect(() => {
    // 当支付创建成功后，开始轮询
    if (payment && paymentStep === 'processing') {
      setPaymentStep('polling');
      startPolling(payment.id, (updatedPayment) => {
        if (updatedPayment.status === 'completed') {
          setPaymentStep('success');
        } else if (updatedPayment.status === 'failed') {
          setPaymentStep('failed');
        }
      });
    }
  }, [payment, paymentStep, startPolling]);

  const handleCreatePayment = async () => {
    if (!plan) return;

    setPaymentStep('processing');

    const result = await createPayment({
      amount: parseFloat(plan.price),
      currency: 'CNY',
      payment_method: selectedMethod,
      subscription_id,
    });

    if (!result) {
      setPaymentStep('failed');
    }
  };

  const handleRetry = () => {
    reset();
    setPaymentStep('select');
  };

  const handleBackToPlans = () => {
    navigate(ROUTES.SUBSCRIPTION);
  };

  const handleViewSubscription = () => {
    navigate(ROUTES.MY_SUBSCRIPTION);
  };

  if (!user || !plan) {
    return null;
  }

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-12 max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBackToPlans}
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回订阅计划
          </Button>
          <h1 className="text-3xl font-bold mb-2">支付订单</h1>
          <p className="text-muted-foreground">
            完成支付以激活您的订阅计划
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Left - Order Summary */}
          <div className="md:col-span-1">
            <Card className="sticky top-4">
              <CardHeader>
                <CardTitle className="text-lg">订单摘要</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">订阅计划</p>
                  <p className="font-semibold">{plan.name}</p>
                </div>

                <div>
                  <p className="text-sm text-muted-foreground mb-1">计费周期</p>
                  <p className="font-medium">
                    {plan.billing_cycle === 'monthly' ? '月付' :
                     plan.billing_cycle === 'yearly' ? '年付' : '一次性'}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-muted-foreground mb-1">配额限制</p>
                  <p className="font-medium">{plan.quota_limit} 次</p>
                </div>

                <div className="border-t pt-4">
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm text-muted-foreground">应付金额</span>
                    <div className="text-right">
                      <span className="text-2xl font-bold text-primary">
                        ¥{parseFloat(plan.price).toFixed(2)}
                      </span>
                      {plan.billing_cycle !== 'one_time' && (
                        <span className="text-sm text-muted-foreground ml-1">
                          / {plan.billing_cycle === 'monthly' ? '月' : '年'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right - Payment Process */}
          <div className="md:col-span-2">
            {/* Payment Method Selection */}
            {paymentStep === 'select' && (
              <Card>
                <CardHeader>
                  <CardTitle>选择支付方式</CardTitle>
                  <CardDescription>
                    请选择您偏好的支付方式
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    {(Object.keys(PAYMENT_METHODS) as PaymentMethod[]).map((method) => {
                      const config = PAYMENT_METHODS[method];
                      return (
                        <button
                          key={method}
                          onClick={() => setSelectedMethod(method)}
                          className={`p-6 border-2 rounded-lg transition-all ${
                            selectedMethod === method
                              ? 'border-primary bg-primary/5'
                              : 'border-border hover:border-primary/50'
                          }`}
                        >
                          <div className="flex flex-col items-center gap-3">
                            <span className="text-4xl">{config.icon}</span>
                            <span className="font-semibold">{config.name}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <Button
                    onClick={handleCreatePayment}
                    className="w-full"
                    size="lg"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        创建订单中...
                      </>
                    ) : (
                      <>
                        <CreditCard className="h-4 w-4 mr-2" />
                        立即支付 ¥{parseFloat(plan.price).toFixed(2)}
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* QR Code Display - Polling */}
            {(paymentStep === 'polling' || paymentStep === 'processing') && payment && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>扫码支付</CardTitle>
                      <CardDescription>
                        请使用{PAYMENT_METHODS[payment.payment_method].name}扫描二维码完成支付
                      </CardDescription>
                    </div>
                    <Badge className="bg-yellow-500">
                      <Clock className="h-3 w-3 mr-1" />
                      等待支付
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {/* QR Code */}
                    <div className="flex justify-center">
                      {payment.qr_code ? (
                        <div className="bg-white p-6 rounded-lg border-2 border-primary shadow-lg">
                          <QRCodeSVG
                            value={payment.qr_code}
                            size={256}
                            level="H"
                            includeMargin={true}
                          />
                        </div>
                      ) : payment.payment_url ? (
                        <div className="bg-white p-6 rounded-lg border-2 border-primary shadow-lg">
                          <QRCodeSVG
                            value={payment.payment_url}
                            size={256}
                            level="H"
                            includeMargin={true}
                          />
                        </div>
                      ) : (
                        <div className="w-64 h-64 bg-muted rounded-lg flex items-center justify-center">
                          <div className="text-center">
                            <QrCode className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                            <p className="text-sm text-muted-foreground">二维码加载中...</p>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Payment Amount */}
                    <div className="text-center">
                      <p className="text-sm text-muted-foreground mb-1">支付金额</p>
                      <p className="text-3xl font-bold text-primary">
                        ¥{parseFloat(payment.amount).toFixed(2)}
                      </p>
                    </div>

                    {/* Polling Indicator */}
                    <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>正在等待支付完成...</span>
                    </div>

                    {/* Alternative Payment Link */}
                    {payment.payment_url && (
                      <div className="border-t pt-4">
                        <p className="text-sm text-muted-foreground text-center mb-3">
                          或使用支付链接
                        </p>
                        <Button
                          variant="outline"
                          className="w-full"
                          onClick={() => window.open(payment.payment_url, '_blank')}
                        >
                          打开支付页面
                        </Button>
                      </div>
                    )}

                    <Button
                      variant="ghost"
                      className="w-full"
                      onClick={handleRetry}
                    >
                      取消支付
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Success State */}
            {paymentStep === 'success' && (
              <Card className="border-2 border-green-500">
                <CardContent className="pt-12 pb-12">
                  <div className="text-center space-y-6">
                    <div className="w-20 h-20 rounded-full bg-green-100 dark:bg-green-900/30 mx-auto flex items-center justify-center">
                      <CheckCircle2 className="h-10 w-10 text-green-600 dark:text-green-400" />
                    </div>

                    <div>
                      <h3 className="text-2xl font-bold mb-2">支付成功！</h3>
                      <p className="text-muted-foreground">
                        您的订阅已成功激活
                      </p>
                    </div>

                    {payment && (
                      <div className="bg-muted/50 rounded-lg p-4 max-w-md mx-auto">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-muted-foreground mb-1">订单号</p>
                            <p className="font-mono font-medium">{payment.id.slice(0, 12)}...</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1">支付方式</p>
                            <p className="font-medium">
                              {PAYMENT_METHODS[payment.payment_method].name}
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1">支付金额</p>
                            <p className="font-medium text-green-600">
                              ¥{parseFloat(payment.amount).toFixed(2)}
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1">支付时间</p>
                            <p className="font-medium">
                              {new Date(payment.updated_at || payment.created_at).toLocaleString('zh-CN')}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="flex gap-3 justify-center">
                      <Button
                        onClick={handleViewSubscription}
                        size="lg"
                      >
                        查看我的订阅
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => navigate(ROUTES.DASHBOARD)}
                        size="lg"
                      >
                        返回首页
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Failed State */}
            {paymentStep === 'failed' && (
              <Card className="border-2 border-destructive">
                <CardContent className="pt-12 pb-12">
                  <div className="text-center space-y-6">
                    <div className="w-20 h-20 rounded-full bg-destructive/10 mx-auto flex items-center justify-center">
                      <XCircle className="h-10 w-10 text-destructive" />
                    </div>

                    <div>
                      <h3 className="text-2xl font-bold mb-2">支付失败</h3>
                      <p className="text-muted-foreground">
                        {error || '支付过程中出现问题，请重试'}
                      </p>
                    </div>

                    <div className="flex gap-3 justify-center">
                      <Button onClick={handleRetry} size="lg">
                        重新支付
                      </Button>
                      <Button
                        variant="outline"
                        onClick={handleBackToPlans}
                        size="lg"
                      >
                        返回订阅计划
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* Security Notice */}
        <div className="mt-8">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              支付过程安全加密，我们不会存储您的支付密码或敏感信息。如遇到问题，请联系客服。
            </AlertDescription>
          </Alert>
        </div>
      </div>
    </MainLayout>
  );
};

export default PaymentPage;
