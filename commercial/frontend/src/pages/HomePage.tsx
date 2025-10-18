import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ROUTES, IDOCTOR_APP_URL } from '@/utils/constants';
import { MainLayout } from '@/components/layout/MainLayout';
import { SparklesCore } from '@/components/ui/sparkles';
import {
  Activity,
  Shield,
  Zap,
  Brain,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  
  const handleFlaskAppRedirect = () => {
    try {
      // 在新窗口打开Flask应用
      const newWindow = window.open(IDOCTOR_APP_URL, '_blank');
      if (!newWindow) {
        // 如果弹窗被阻止，提示用户
        alert('请允许浏览器弹窗，然后再试一次');
      }
    } catch (error) {
      console.error('跳转到分析服务失败:', error);
      // 备用方案：直接跳转
      window.location.href = IDOCTOR_APP_URL;
    }
  };

  const features = [
    {
      icon: Brain,
      title: '智能分析',
      description: '基于深度学习的 L3 椎体检测与肌肉分割技术',
    },
    {
      icon: Zap,
      title: '高效处理',
      description: '自动化流程，快速生成精准的分析报告',
    },
    {
      icon: Shield,
      title: '安全可靠',
      description: '企业级数据加密，符合医疗行业安全标准',
    },
  ];

  const highlights = [
    '自动 L3 椎体检测',
    '精准肌肉区域分割',
    'HU 值统计分析',
    '可视化结果输出',
  ];

  return (
    <MainLayout>
      {/* Global Sparkles Background */}
      <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
        <SparklesCore
          id="global-sparkles"
          background="transparent"
          minSize={0.6}
          maxSize={2}
          particleDensity={60}
          className="w-full h-full"
          particleColor="#ffffff"
          speed={0.25}
        />
      </div>

      {/* Hero Section */}
      <div className="relative min-h-[600px] flex items-center justify-center overflow-hidden" style={{ zIndex: 2 }}>
        {/* Content */}
        <div className="relative container mx-auto px-4 py-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary border border-primary/20 mb-8">
            <Activity className="h-4 w-4" />
            <span className="text-sm font-medium">AI 医疗影像分析平台</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-primary via-secondary to-primary bg-clip-text text-transparent">
            iDoctor
          </h1>

          <p className="text-xl md:text-2xl text-muted-foreground mb-4 max-w-3xl mx-auto">
            专业的医疗影像 AI 分析服务
          </p>
          <p className="text-lg text-muted-foreground mb-10 max-w-2xl mx-auto">
            基于先进的深度学习模型，提供精准的 CT 扫描分析与肌肉组织评估
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            {isAuthenticated ? (
              <Button size="lg" className="text-lg px-8" onClick={() => navigate(ROUTES.DASHBOARD)}>
                进入控制台
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            ) : (
              <>
                <Button size="lg" className="text-lg px-8" onClick={() => navigate(ROUTES.REGISTER)}>
                  开始使用
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  className="text-lg px-8"
                  onClick={() => navigate(ROUTES.LOGIN)}
                >
                  登录账户
                </Button>
              </>
            )}
          </div>

          {/* Highlights */}
          <div className="flex flex-wrap justify-center gap-4 max-w-3xl mx-auto">
            {highlights.map((item, index) => (
              <div
                key={index}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border"
              >
                <CheckCircle2 className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="relative container mx-auto px-4 py-20" style={{ zIndex: 2 }}>
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">核心功能</h2>
        <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
          我们提供全流程自动化的医疗影像分析服务
        </p>

        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <Card
                key={index}
                className="border-2 hover:border-primary/50 transition-all duration-300 hover:shadow-lg group"
              >
                <CardHeader>
                  <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <CardTitle className="text-xl">{feature.title}</CardTitle>
                  <CardDescription className="text-base">
                    {feature.description}
                  </CardDescription>
                </CardHeader>
              </Card>
            );
          })}
        </div>
      </div>

      {/* CTA Section */}
      <div className="relative container mx-auto px-4 py-20" style={{ zIndex: 2 }}>
        <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5">
          <CardHeader className="text-center py-12">
            <CardTitle className="text-3xl md:text-4xl mb-4">
              准备好开始了吗？
            </CardTitle>
            <CardDescription className="text-lg mb-8">
              选择适合您的订阅计划，立即体验专业的医疗影像分析服务
            </CardDescription>
            <div className="flex gap-4 justify-center">
              <Button
                size="lg"
                className="text-lg px-8"
                onClick={handleFlaskAppRedirect}
              >
                立即体验分析服务
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </div>
          </CardHeader>
        </Card>
      </div>
    </MainLayout>
  );
};

export default HomePage;
