/**
 * Type definitions for the Commercial SAM2 Interactive Demo feature
 */

/**
 * Represents a click point on the canvas for SAM2 segmentation
 * @property x - X coordinate in original image dimensions
 * @property y - Y coordinate in original image dimensions
 * @property label - 1 for foreground (green), 0 for background (red)
 */
export interface ClickPoint {
  x: number;
  y: number;
  label: 0 | 1;
}

/**
 * Bounding box coordinates and dimensions
 */
export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Result from SAM2 segmentation API
 */
export interface SegmentationResult {
  /** Base64-encoded PNG mask data */
  mask_data: string;
  /** Confidence score between 0.0 and 1.0 */
  confidence_score: number;
  /** Processing time in milliseconds */
  processing_time_ms: number;
  /** Bounding box of the segmented region */
  bounding_box: BoundingBox;
  /** Whether this result was served from cache */
  cached: boolean;
}

/**
 * 2D point coordinates
 */
export interface Point {
  x: number;
  y: number;
}

/**
 * Label annotation for a segmented region
 */
export interface Label {
  /** Unique identifier */
  id: string;
  /** Label text content */
  text: string;
  /** Position of the label text box */
  position: Point;
  /** Center point of the associated segment (for leader line) */
  segmentCenter: Point;
}

/**
 * Image metadata
 */
export interface ImageMetadata {
  width: number;
  height: number;
  format: string;
}

/**
 * Supported LLM providers
 */
export type LLMProvider = "openai" | "anthropic" | "none" | "mock";

/**
 * Main state for the demo component
 */
export interface DemoState {
  /** Data URL of the uploaded image */
  uploadedImage: string | null;
  /** Metadata of the uploaded image */
  imageMetadata: ImageMetadata | null;
  /** Array of click points for segmentation */
  clickPoints: ClickPoint[];
  /** Current segmentation mask (base64 PNG) */
  segmentationMask: string | null;
  /** Full segmentation result from API */
  segmentationResult: SegmentationResult | null;
  /** Array of labels added to the image */
  labels: Label[];
  /** Whether segmentation is in progress */
  isSegmenting: boolean;
  /** Whether LLM suggestions are being fetched */
  isFetchingSuggestions: boolean;
  /** Current error message, if any */
  error: string | null;
}

/**
 * Environment configuration for the demo
 */
export interface DemoConfig {
  llmProvider: LLMProvider;
  llmApiKey: string;
  llmModel: string;
  llmDebug: boolean;
}

/**
 * LLM suggestion request parameters
 */
export interface LLMSuggestionParams {
  /** Base64-encoded image of the segmented region */
  imageBase64: string;
  /** Base64-encoded mask */
  maskBase64: string;
  /** Bounding box of the segmented region */
  boundingBox: BoundingBox;
  /** Optional context hint for the LLM */
  contextHint?: string;
}
