import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sparkles } from 'lucide-react';
import { ImageSegmentationDemo } from './ImageSegmentationDemo';
import { Dialog, DialogContent } from '@/components/ui/dialog';

export const DemoSegmentationCard: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <Card
        className="group cursor-pointer transition-all duration-300 hover:shadow-xl hover:scale-105 border-2 border-gray-200 rounded-xl overflow-hidden"
        onClick={() => setIsModalOpen(true)}
      >
        <CardHeader>
          <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-3">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <CardTitle className="text-xl">AI 图像分割演示</CardTitle>
          <CardDescription>
            体验 SAM2 交互式智能分割技术
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center text-sm text-primary font-medium group-hover:gap-3 transition-all">
            <span>立即体验</span>
            <span className="ml-2 group-hover:translate-x-1 transition-transform">→</span>
          </div>
        </CardContent>
      </Card>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-[95vw] max-h-[95vh] p-0 overflow-hidden">
          <ImageSegmentationDemo onClose={() => setIsModalOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
};
