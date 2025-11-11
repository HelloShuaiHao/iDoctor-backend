import React, { useRef, useEffect, useCallback, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, Play } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { ClickPoint, ImageMetadata, Label, SegmentationResult } from '@/types/demo';
import { demoSAM2Service } from '@/services/demo/demoSAM2Service';

interface Props {
  imageUrl: string;
  imageMetadata: ImageMetadata;
  clickPoints: ClickPoint[];
  maskData: string | null;
  labels: Label[];
  isSegmenting: boolean;
  onAddClickPoint: (x: number, y: number, label: 0 | 1) => void;
  onSegmentationComplete: (result: SegmentationResult) => void;
  onSegmentationError: (error: string) => void;
  onUpdateLabelPosition?: (labelId: string, x: number, y: number) => void;
  setState: React.Dispatch<React.SetStateAction<any>>;
}

export const SAM2Canvas: React.FC<Props> = ({
  imageUrl,
  imageMetadata,
  clickPoints,
  maskData,
  labels,
  isSegmenting,
  onAddClickPoint,
  onSegmentationComplete,
  onSegmentationError,
  setState,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const maskImageRef = useRef<HTMLImageElement | null>(null);
  const [scale, setScale] = useState(1);
  const { toast } = useToast();

  // Load and render image
  useEffect(() => {
    if (!canvasRef.current || !imageUrl) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      imageRef.current = img;

      // Calculate scale to fit container
      const container = containerRef.current;
      if (container) {
        const maxWidth = container.clientWidth - 40;
        const maxHeight = 600;
        const scaleX = maxWidth / img.width;
        const scaleY = maxHeight / img.height;
        const newScale = Math.min(scaleX, scaleY, 1);
        setScale(newScale);

        canvas.width = img.width * newScale;
        canvas.height = img.height * newScale;
      }

      redraw();
    };
    img.src = imageUrl;
  }, [imageUrl]);

  // Load mask image when available
  useEffect(() => {
    if (!maskData) {
      maskImageRef.current = null;
      redraw();
      return;
    }

    const maskImg = new Image();
    maskImg.onload = () => {
      maskImageRef.current = maskImg;
      redraw();
    };
    maskImg.src = `data:image/png;base64,${maskData}`;
  }, [maskData]);

  // Redraw canvas when any state changes
  useEffect(() => {
    redraw();
  }, [clickPoints, labels, scale]);

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || !imageRef.current) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw image
    ctx.drawImage(imageRef.current, 0, 0, canvas.width, canvas.height);

    // Draw mask overlay
    if (maskImageRef.current) {
      ctx.save();
      ctx.globalAlpha = 0.4;
      ctx.drawImage(maskImageRef.current, 0, 0, canvas.width, canvas.height);
      ctx.restore();
    }

    // Draw click points
    clickPoints.forEach((point) => {
      const x = point.x * scale;
      const y = point.y * scale;
      const isForeground = point.label === 1;

      // Draw outer circle
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, 2 * Math.PI);
      ctx.fillStyle = isForeground ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)';
      ctx.fill();
      ctx.strokeStyle = isForeground ? '#15803d' : '#991b1b';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw inner dot
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, 2 * Math.PI);
      ctx.fillStyle = 'white';
      ctx.fill();
    });
  }, [clickPoints, scale]);

  const canvasToImageCoords = useCallback(
    (clientX: number, clientY: number): { x: number; y: number } => {
      const canvas = canvasRef.current;
      if (!canvas) return { x: 0, y: 0 };

      const rect = canvas.getBoundingClientRect();
      const xCanvas = clientX - rect.left;
      const yCanvas = clientY - rect.top;

      return {
        x: Math.round(Math.max(0, Math.min(imageMetadata.width - 1, xCanvas / scale))),
        y: Math.round(Math.max(0, Math.min(imageMetadata.height - 1, yCanvas / scale))),
      };
    },
    [scale, imageMetadata]
  );

  const handleCanvasClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (isSegmenting) return;

      const { x, y } = canvasToImageCoords(e.clientX, e.clientY);
      const label = e.button === 2 ? 0 : 1; // Right-click = background, left-click = foreground
      onAddClickPoint(x, y, label);
    },
    [isSegmenting, canvasToImageCoords, onAddClickPoint]
  );

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    return false;
  }, []);

  const handleRunSegmentation = async () => {
    if (clickPoints.length === 0) {
      toast({
        title: '请添加标记点',
        description: '至少需要一个标记点才能运行分割',
        variant: 'destructive',
      });
      return;
    }

    setState((prev: any) => ({ ...prev, isSegmenting: true, error: null }));

    try {
      // Convert image URL to Blob
      const response = await fetch(imageUrl);
      const imageBlob = await response.blob();

      // Call SAM2 service
      const result = await demoSAM2Service.segmentWithClicks(imageBlob, clickPoints);

      onSegmentationComplete(result);

      toast({
        title: '分割完成',
        description: `置信度: ${(result.confidence_score * 100).toFixed(1)}%`,
      });
    } catch (error: any) {
      console.error('Segmentation failed:', error);
      onSegmentationError(error.message);

      toast({
        title: '分割失败',
        description: error.message,
        variant: 'destructive',
      });
    }
  };

  return (
    <div ref={containerRef} className="space-y-4">
      <div className="relative border-2 border-gray-300 rounded-lg overflow-hidden bg-black">
        <canvas
          ref={canvasRef}
          className={`max-w-full ${isSegmenting ? 'cursor-wait' : 'cursor-crosshair'}`}
          onClick={handleCanvasClick}
          onContextMenu={handleContextMenu}
          onMouseDown={(e) => {
            if (e.button === 2) handleCanvasClick(e);
          }}
        />

        {/* Loading overlay */}
        {isSegmenting && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <div className="bg-white rounded-lg p-6 text-center space-y-3">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <div>
                <p className="font-medium">AI 正在分析图像...</p>
                <p className="text-sm text-muted-foreground">通常需要 3-5 秒</p>
              </div>
            </div>
          </div>
        )}

        {/* Labels with leader lines */}
        {labels.length > 0 && (
          <svg className="absolute inset-0 pointer-events-none" style={{ width: '100%', height: '100%' }}>
            {labels.map((label) => {
              const x1 = label.segmentCenter.x * scale;
              const y1 = label.segmentCenter.y * scale;
              const x2 = label.position.x * scale;
              const y2 = label.position.y * scale;

              return (
                <g key={label.id}>
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="#6b7280"
                    strokeWidth="2"
                    strokeDasharray="4 4"
                  />
                  <circle cx={x2} cy={y2} r="4" fill="#3b82f6" />
                </g>
              );
            })}
          </svg>
        )}

        {/* Label text boxes */}
        {labels.length > 0 && (
          <div className="absolute inset-0 pointer-events-none">
            {labels.map((label) => (
              <div
                key={label.id}
                className="absolute bg-white border border-gray-300 rounded-md px-3 py-2 text-sm font-medium shadow-sm pointer-events-auto cursor-move"
                style={{
                  left: `${label.position.x * scale}px`,
                  top: `${label.position.y * scale}px`,
                  transform: 'translate(-50%, -100%)',
                }}
              >
                {label.text}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Instructions and Segment Button */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {clickPoints.length === 0 ? (
            <span>👆 点击图像添加标记点 (左键: 前景 | 右键: 背景)</span>
          ) : (
            <span>已添加 {clickPoints.length} 个标记点</span>
          )}
        </div>

        <Button
          onClick={handleRunSegmentation}
          disabled={clickPoints.length === 0 || isSegmenting}
          size="lg"
        >
          {isSegmenting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              分割中...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              执行分割 ({clickPoints.length})
            </>
          )}
        </Button>
      </div>
    </div>
  );
};
