import React, { useCallback, useState } from 'react';
import { Upload, Image as ImageIcon } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface Props {
  onImageLoaded: (imageUrl: string, width: number, height: number) => void;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_DIMENSION = 2048;
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg'];

export const ImageUploadZone: React.FC<Props> = ({ onImageLoaded }) => {
  const { toast } = useToast();
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      // Validate file type
      if (!ALLOWED_TYPES.includes(file.type)) {
        toast({
          title: '不支持的格式',
          description: '请上传 PNG 或 JPG 格式的图片',
          variant: 'destructive',
        });
        return;
      }

      // Validate file size
      if (file.size > MAX_FILE_SIZE) {
        toast({
          title: '文件过大',
          description: `文件大小不能超过 ${MAX_FILE_SIZE / 1024 / 1024}MB`,
          variant: 'destructive',
        });
        return;
      }

      // Load image
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          let { width, height } = img;

          // Resize if needed
          if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
            const scale = Math.min(MAX_DIMENSION / width, MAX_DIMENSION / height);
            width = Math.floor(width * scale);
            height = Math.floor(height * scale);

            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d')!;
            ctx.drawImage(img, 0, 0, width, height);

            const resizedUrl = canvas.toDataURL('image/png');
            onImageLoaded(resizedUrl, width, height);

            toast({
              title: '图片已调整',
              description: `图片已调整至 ${width} × ${height} 像素以优化处理`,
            });
          } else {
            onImageLoaded(e.target!.result as string, width, height);
          }
        };
        img.src = e.target!.result as string;
      };
      reader.readAsDataURL(file);
    },
    [onImageLoaded, toast]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleClick = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = ALLOWED_TYPES.join(',');
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleFile(file);
      }
    };
    input.click();
  }, [handleFile]);

  return (
    <div className="flex items-center justify-center h-full min-h-[500px]">
      <div
        className={`
          w-full max-w-2xl p-12 border-2 border-dashed rounded-xl
          transition-all cursor-pointer
          ${
            isDragging
              ? 'border-primary bg-primary/5 scale-105'
              : 'border-gray-300 hover:border-primary hover:bg-gray-50'
          }
        `}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
      >
        <div className="flex flex-col items-center text-center space-y-4">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-100 to-pink-100 flex items-center justify-center">
            {isDragging ? (
              <Upload className="h-10 w-10 text-primary animate-bounce" />
            ) : (
              <ImageIcon className="h-10 w-10 text-primary" />
            )}
          </div>

          <div>
            <h3 className="text-xl font-semibold mb-2">
              {isDragging ? '释放以上传' : '拖放图片到这里'}
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              或点击选择文件
            </p>
          </div>

          <div className="text-xs text-muted-foreground space-y-1">
            <p>支持格式: PNG, JPG, JPEG</p>
            <p>最大大小: 10MB</p>
            <p>最大尺寸: 2048 × 2048 像素</p>
          </div>
        </div>
      </div>
    </div>
  );
};
