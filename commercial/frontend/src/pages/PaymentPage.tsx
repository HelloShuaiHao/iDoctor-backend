import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

const PaymentPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-8">
      <div className="container mx-auto">
        <h1 className="text-3xl font-bold mb-8">支付</h1>
        <Card>
          <CardHeader>
            <CardTitle>支付功能</CardTitle>
            <CardDescription>支付功能开发中...</CardDescription>
          </CardHeader>
        </Card>
      </div>
    </div>
  );
};

export default PaymentPage;
