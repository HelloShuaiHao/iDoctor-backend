import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, X } from 'lucide-react';
import type { Label } from '@/types/demo';

interface Props {
  disabled: boolean;
  labels: Label[];
  onAddLabel: (text: string) => void;
  onRemoveLabel: (labelId: string) => void;
}

const MAX_LABEL_LENGTH = 50;

export const LabelInputPanel: React.FC<Props> = ({
  disabled,
  labels,
  onAddLabel,
  onRemoveLabel,
}) => {
  const [labelText, setLabelText] = useState('');

  const handleAdd = () => {
    if (labelText.trim()) {
      onAddLabel(labelText);
      setLabelText('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAdd();
    }
  };

  return (
    <Card className="border-2 rounded-lg">
      <CardHeader>
        <CardTitle className="text-sm text-gray-900 dark:text-gray-100">标签管理</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            placeholder="输入标签 (如: 肾脏)"
            value={labelText}
            onChange={(e) => setLabelText(e.target.value.slice(0, MAX_LABEL_LENGTH))}
            onKeyPress={handleKeyPress}
            disabled={disabled}
            className="text-sm text-gray-900 dark:text-gray-100"
          />
          <Button
            size="sm"
            onClick={handleAdd}
            disabled={disabled || !labelText.trim()}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <div className="text-xs text-right text-gray-600 dark:text-gray-400">
          {labelText.length}/{MAX_LABEL_LENGTH}
        </div>

        {labels.length > 0 && (
          <div className="pt-3 border-t space-y-2">
            <div className="text-xs font-medium text-gray-700 dark:text-gray-300">
              已添加的标签:
            </div>
            <div className="flex flex-wrap gap-2">
              {labels.map((label) => (
                <Badge
                  key={label.id}
                  variant="default"
                  className="text-xs py-1 px-2 pr-1 bg-blue-600 text-white hover:bg-blue-700"
                >
                  {label.text}
                  <button
                    onClick={() => onRemoveLabel(label.id)}
                    className="ml-1 hover:text-white/80"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
