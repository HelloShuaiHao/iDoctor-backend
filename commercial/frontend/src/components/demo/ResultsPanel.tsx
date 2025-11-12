import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Clock, Box } from 'lucide-react';
import type { SegmentationResult } from '@/types/demo';

interface Props {
  result: SegmentationResult;
}

export const ResultsPanel: React.FC<Props> = ({ result }) => {
  const confidencePercent = (result.confidence_score * 100).toFixed(1);
  const timeDisplay =
    result.processing_time_ms > 1000
      ? `${(result.processing_time_ms / 1000).toFixed(1)}s`
      : `${result.processing_time_ms}ms`;

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <Card className="border-2 rounded-lg">
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2 text-gray-900 dark:text-gray-100">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          分割结果
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-700 dark:text-gray-300">置信度:</span>
            <span className={`font-semibold ${getConfidenceColor(result.confidence_score)}`}>
              {confidencePercent}%
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-700 dark:text-gray-300">处理时间:</span>
            <div className="flex items-center gap-1 text-gray-900 dark:text-gray-100">
              <Clock className="h-3 w-3" />
              <span className="font-medium">{timeDisplay}</span>
              {result.cached && (
                <Badge variant="outline" className="text-xs ml-1">
                  缓存
                </Badge>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-700 dark:text-gray-300">区域大小:</span>
            <div className="flex items-center gap-1 text-gray-900 dark:text-gray-100">
              <Box className="h-3 w-3" />
              <span className="font-medium">
                {result.bounding_box.width} × {result.bounding_box.height}
              </span>
            </div>
          </div>
        </div>

        {result.confidence_score < 0.5 && (
          <div className="pt-3 border-t">
            <p className="text-xs text-yellow-600">
              ⚠️ 置信度较低，建议添加更多标记点以提高准确性
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
