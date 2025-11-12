import React, { useState, useCallback } from 'react';
import type { DemoState } from '@/types/demo';
import { ImageUploadZone } from './ImageUploadZone';
import { SAM2Canvas } from './SAM2Canvas';
import { ControlPanel } from './ControlPanel';
import { LabelInputPanel } from './LabelInputPanel';
import { ResultsPanel } from './ResultsPanel';

interface Props {
  onClose?: () => void;
}

export const ImageSegmentationDemo: React.FC<Props> = ({ onClose }) => {
  const [state, setState] = useState<DemoState>({
    uploadedImage: null,
    imageMetadata: null,
    clickPoints: [],
    segmentationMask: null,
    segmentationResult: null,
    labels: [],
    isSegmenting: false,
    isFetchingSuggestions: false,
    error: null,
  });

  const handleImageLoaded = useCallback((imageUrl: string, width: number, height: number) => {
    setState((prev) => ({
      ...prev,
      uploadedImage: imageUrl,
      imageMetadata: { width, height, format: 'image/png' },
      clickPoints: [],
      segmentationMask: null,
      segmentationResult: null,
      labels: [],
      error: null,
    }));
  }, []);

  const handleAddClickPoint = useCallback((x: number, y: number, label: 0 | 1) => {
    setState((prev) => ({
      ...prev,
      clickPoints: [...prev.clickPoints, { x, y, label }],
    }));
  }, []);

  const handleClearPoints = useCallback(() => {
    setState((prev) => ({
      ...prev,
      clickPoints: [],
    }));
  }, []);

  const handleStartOver = useCallback(() => {
    if (confirm('清除所有进度并重新开始?')) {
      setState({
        uploadedImage: null,
        imageMetadata: null,
        clickPoints: [],
        segmentationMask: null,
        segmentationResult: null,
        labels: [],
        isSegmenting: false,
        isFetchingSuggestions: false,
        error: null,
      });
    }
  }, []);

  const handleSegmentationComplete = useCallback((result: any) => {
    setState((prev) => ({
      ...prev,
      segmentationResult: result,
      segmentationMask: result.mask_data,
      clickPoints: [], // 清空标记点，允许用户重新标记
      isSegmenting: false,
      error: null,
    }));
  }, []);

  const handleSegmentationError = useCallback((error: string) => {
    setState((prev) => ({
      ...prev,
      isSegmenting: false,
      error,
    }));
  }, []);

  const handleAddLabel = useCallback((text: string) => {
    if (!text.trim() || !state.segmentationResult) return;

    const bbox = state.segmentationResult.bounding_box;
    const segmentCenter = {
      x: bbox.x + bbox.width / 2,
      y: bbox.y + bbox.height / 2,
    };

    const newLabel = {
      id: Date.now().toString(),
      text: text.trim(),
      position: {
        x: segmentCenter.x + bbox.width * 0.6,
        y: segmentCenter.y - bbox.height * 0.3,
      },
      segmentCenter,
    };

    setState((prev) => ({
      ...prev,
      labels: [...prev.labels, newLabel],
    }));
  }, [state.segmentationResult]);

  const handleRemoveLabel = useCallback((labelId: string) => {
    setState((prev) => ({
      ...prev,
      labels: prev.labels.filter((l) => l.id !== labelId),
    }));
  }, []);

  const handleUpdateLabelPosition = useCallback((labelId: string, x: number, y: number) => {
    setState((prev) => ({
      ...prev,
      labels: prev.labels.map((l) =>
        l.id === labelId ? { ...l, position: { x, y } } : l
      ),
    }));
  }, []);

  return (
    <div className="w-full h-full bg-white flex flex-col">
      {/* Header */}
      <div className="p-6 border-b">
        <h2 className="text-2xl font-bold !text-gray-900 dark:!text-gray-100">AI 图像分割演示</h2>
        <p className="text-sm !text-gray-600 dark:!text-gray-400 mt-1">
          上传图片，点击添加标记点，运行 SAM2 智能分割
        </p>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-6">
        {!state.uploadedImage ? (
          <ImageUploadZone onImageLoaded={handleImageLoaded} />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full">
            {/* Left: Controls */}
            <div className="lg:col-span-2 space-y-4">
              <ControlPanel
                clickPointsCount={state.clickPoints.length}
                hasImage={!!state.uploadedImage}
                isSegmenting={state.isSegmenting}
                onClearPoints={handleClearPoints}
                onStartOver={handleStartOver}
              />
            </div>

            {/* Center: Canvas */}
            <div className="lg:col-span-7">
              <SAM2Canvas
                imageUrl={state.uploadedImage}
                imageMetadata={state.imageMetadata!}
                clickPoints={state.clickPoints}
                maskData={state.segmentationMask}
                labels={state.labels}
                isSegmenting={state.isSegmenting}
                onAddClickPoint={handleAddClickPoint}
                onSegmentationComplete={handleSegmentationComplete}
                onSegmentationError={handleSegmentationError}
                onUpdateLabelPosition={handleUpdateLabelPosition}
                setState={setState}
              />
            </div>

            {/* Right: Labels & Results */}
            <div className="lg:col-span-3 space-y-4">
              {state.segmentationResult && (
                <>
                  <ResultsPanel result={state.segmentationResult} />
                  <LabelInputPanel
                    disabled={!state.segmentationResult}
                    labels={state.labels}
                    onAddLabel={handleAddLabel}
                    onRemoveLabel={handleRemoveLabel}
                  />
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
