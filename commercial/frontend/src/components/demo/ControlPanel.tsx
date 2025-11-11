import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Eraser, RotateCcw } from 'lucide-react';

interface Props {
  clickPointsCount: number;
  hasImage: boolean;
  isSegmenting: boolean;
  onClearPoints: () => void;
  onStartOver: () => void;
}

export const ControlPanel: React.FC<Props> = ({
  clickPointsCount,
  hasImage,
  isSegmenting,
  onClearPoints,
  onStartOver,
}) => {
  return (
    <Card className="border-2 rounded-lg">
      <CardHeader>
        <CardTitle className="text-sm">控制面板</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-xs text-muted-foreground space-y-1">
          <p>📍 <strong>左键:</strong> 前景点 (绿色)</p>
          <p>📍 <strong>右键:</strong> 背景点 (红色)</p>
        </div>

        <div className="pt-3 border-t">
          <div className="text-sm font-medium mb-2">
            标记点: <span className="text-primary">{clickPointsCount}</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="w-full"
            disabled={clickPointsCount === 0 || isSegmenting}
            onClick={onClearPoints}
          >
            <Eraser className="h-4 w-4 mr-2" />
            清除标记点
          </Button>
        </div>

        <div className="pt-3 border-t">
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            disabled={!hasImage || isSegmenting}
            onClick={onStartOver}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            重新开始
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
