# Design Document: Commercial SAM2 Interactive Demo

## Overview

This document outlines the architectural decisions, component design, and implementation strategies for adding an interactive SAM2 segmentation demo to the commercial frontend.

## Architecture Decisions

### Decision 1: Dashboard Module vs. Standalone Page

**Context**: The feature needs to be easily accessible for quick demonstrations.

**Options**:
1. Dashboard card module (expandable/modal)
2. Separate route/page (`/demo` or `/image-demo`)
3. Homepage hero section

**Decision**: **Dashboard card module with modal expansion**

**Rationale**:
- Faster access (2 clicks from login)
- Maintains user context (no navigation away)
- Can be expanded to full-screen modal for better UX
- Aligns with existing dashboard patterns

**Trade-offs**:
- Limited initial screen space (mitigated by modal expansion)
- Requires state management for modal

### Decision 2: LLM Integration Approach

**Context**: Need intelligent label suggestions based on segmented regions.

**Options**:
1. Backend API endpoint (FastAPI service)
2. Client-side direct API calls (OpenAI/Anthropic)
3. Hybrid (backend for image processing, client for LLM)

**Decision**: **Client-side direct API calls**

**Rationale**:
- Faster MVP development (no backend changes)
- Reduced latency (direct API access)
- Easier iteration on prompts
- Cost transparency (user's API keys optional)

**Trade-offs**:
- API keys exposed in browser (mitigated by env vars + optional user keys)
- No centralized rate limiting (acceptable for demo MVP)
- Can migrate to backend later if needed

### Decision 3: Image Format Support

**Context**: Balance between medical accuracy and demo accessibility.

**Options**:
1. DICOM only (medical-grade)
2. PNG/JPG only (general-purpose)
3. Both formats

**Decision**: **PNG/JPG only for MVP**

**Rationale**:
- Lower barrier to entry for demos
- No DICOM parsing complexity
- Faster loading and processing
- Users can provide screenshots or test images easily

**Trade-offs**:
- Not medically accurate (acceptable for demo/marketing)
- DICOM support can be added in future iteration

### Decision 4: SAM2 API Communication

**Context**: Commercial frontend needs to communicate with existing SAM2 service.

**Options**:
1. Direct HTTP calls to SAM2 Docker service
2. Proxy through commercial backend
3. Use existing CTAI backend endpoints

**Decision**: **Use existing CTAI backend SAM2 endpoint via Nginx**

**Rationale**:
- Leverages existing `/api/ctai/api/segmentation/sam2` endpoint
- CORS already configured in Nginx
- Consistent with L3MaskEditor implementation
- Caching and error handling already in place

**Trade-offs**:
- Depends on CTAI backend being available
- Coupled to existing API contract

## Component Design

### Component Hierarchy

```
DashboardPage
  └─ DemoSegmentationCard
       └─ [onClick] → Modal/Expanded View
            └─ ImageSegmentationDemo
                 ├─ ImageUploadZone
                 ├─ SAM2InteractiveCanvas
                 │    ├─ CanvasOverlay (click points)
                 │    ├─ MaskRenderer (segmentation result)
                 │    └─ LeaderLineLabels (text annotations)
                 ├─ LabelInputPanel
                 │    ├─ LabelTextField
                 │    └─ LLMSuggestionButton
                 └─ ResultsPanel
                      ├─ SegmentationStats
                      ├─ ExportButton
                      └─ ClearButton
```

### Component Specifications

#### 1. DemoSegmentationCard

**Purpose**: Entry point on dashboard

**Props**: None (uses navigation context)

**State**:
- `isModalOpen: boolean`

**Key Features**:
- Eye-catching card design with icon
- Call-to-action: "Try AI Segmentation Demo"
- Opens modal on click

**Styling**:
- Border: `border-2 border-gray-200`
- Border radius: `rounded-xl` (12px)
- Hover effect: Scale + shadow
- Icon: Magic wand or AI chip icon

---

#### 2. ImageSegmentationDemo

**Purpose**: Main demo interface container

**Props**:
- `onClose: () => void` (for modal)

**State**:
```typescript
{
  uploadedImage: string | null,
  imageMetadata: { width: number, height: number },
  clickPoints: { x: number, y: number, label: 0 | 1 }[],
  segmentationMask: string | null, // base64 PNG
  labels: { id: string, text: string, position: Point }[],
  isSegmenting: boolean,
  isFetchingSuggestions: boolean,
  error: string | null
}
```

**Key Features**:
- Workflow stages: Upload → Click → Segment → Label → Export
- Progress indicator showing current stage
- Error boundary for graceful failures

**Layout**:
- Full-width modal or card expansion
- 3-column grid: Image (60%) | Controls (20%) | Results (20%)
- Mobile: stacked layout

---

#### 3. SAM2InteractiveCanvas

**Purpose**: Handle image display, click interactions, and mask rendering

**Props**:
```typescript
{
  imageUrl: string,
  clickPoints: ClickPoint[],
  maskData: string | null, // base64 PNG
  labels: Label[],
  onClickPoint: (point: ClickPoint) => void,
  onLabelPositionChange: (labelId: string, position: Point) => void,
  disabled: boolean
}
```

**State**:
- `canvasRef: React.RefObject<HTMLCanvasElement>`
- `scale: number` (for zoom)
- `hoveredLabel: string | null`

**Interactions**:
- Left-click: Add foreground point (green)
- Right-click: Add background point (red)
- Drag label: Reposition label text
- Scroll: Zoom in/out (optional)

**Rendering Layers**:
1. Base image layer
2. Mask overlay (semi-transparent)
3. Click points (circles with border)
4. Leader lines (SVG paths from label to region)
5. Label text (outside image bounds, white background)

**Styling**:
- Container: `border-2 border-gray-300 rounded-lg overflow-hidden`
- Canvas: `bg-black` (medical image convention)
- Points: Green (#22c55e) for foreground, Red (#ef4444) for background
- Leader lines: Dashed, thin, subtle color

---

#### 4. LabelInputPanel

**Purpose**: Input and manage labels for segmented regions

**Props**:
```typescript
{
  currentLabel: string,
  onLabelChange: (text: string) => void,
  onAddLabel: () => void,
  onRequestSuggestions: () => void,
  suggestions: string[],
  isLoadingSuggestions: boolean,
  disabled: boolean
}
```

**UI Elements**:
- Text input field (rounded, bordered)
- "Add Label" button (primary)
- "Get AI Suggestions" button (secondary, with sparkle icon)
- Suggestions dropdown (chips, clickable)

**Validation**:
- Max 50 characters per label
- Prevent empty labels
- Debounce input for suggestion triggers

---

#### 5. LLMSuggestionService

**Purpose**: Fetch intelligent label suggestions from LLM

**API**:
```typescript
interface LLMSuggestionService {
  getSuggestions(params: {
    imageBase64: string,
    maskBase64: string,
    boundingBox: { x: number, y: number, width: number, height: number },
    contextHint?: string
  }): Promise<string[]>
}
```

**Implementation**:
- Support both OpenAI and Anthropic APIs
- Provider configured via env var: `VITE_LLM_PROVIDER=openai|anthropic`
- API key from env: `VITE_LLM_API_KEY`
- Fallback to manual input if API unavailable

**Prompt Engineering**:
```
You are an image analysis assistant. Analyze the provided image and the highlighted segmentation mask.

The mask represents a distinct region within the image. Based on the shape, texture, color, and context, suggest 3-5 concise labels that best describe what this segmented region represents.

Return ONLY a JSON array of label strings, e.g. ["kidney", "liver tissue", "bone structure"]

Guidelines:
- Be specific and descriptive
- Use medical/anatomical terms when applicable
- Keep labels 1-3 words
- Focus on what the region IS, not what it looks like
```

**Error Handling**:
- Timeout after 10 seconds
- Retry once on failure
- Show fallback message: "AI suggestions unavailable. Please enter labels manually."

## Data Flow

### 1. Image Upload Flow

```
User selects file
  → Validate format (PNG/JPG)
  → Read as Data URL
  → Load image to get dimensions
  → Render on canvas
  → Enable click mode
```

### 2. Segmentation Flow

```
User clicks image
  → Add click point to state (with label 0/1)
  → Render point on canvas
  ↓ (User clicks "Segment")
  → Call SAM2 API with image + click points
  → Show loading spinner
  → Receive mask (base64 PNG)
  → Decode and render mask overlay
  → Extract bounding box from mask
  → Enable label input
```

### 3. Label Suggestion Flow

```
User clicks "Get AI Suggestions"
  → Extract segmented region as separate image
  → Send to LLM with prompt
  → Parse JSON response
  → Display as clickable chips
  → User selects suggestion or types custom
  → Add label with leader line
```

### 4. Export Flow

```
User clicks "Export"
  → Create composite image (original + mask + labels)
  → Render to new canvas
  → Convert to PNG blob
  → Trigger download
```

## API Contracts

### SAM2 Segmentation Endpoint

**Endpoint**: `POST /api/ctai/api/segmentation/sam2`

**Request**:
```typescript
{
  imageFile: Blob, // PNG/JPG file
  imageType: "general", // new type for non-medical
  patientId: "demo-user", // placeholder
  sliceIndex: "0",
  clickPoints: { x: number, y: number, label: 0 | 1 }[]
}
```

**Response**:
```typescript
{
  mask_data: string, // base64 PNG
  confidence_score: number,
  processing_time_ms: number,
  bounding_box: { x: number, y: number, width: number, height: number },
  cached: boolean
}
```

### LLM API (OpenAI Example)

**Endpoint**: `POST https://api.openai.com/v1/chat/completions`

**Request**:
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "<prompt>" },
        { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }
      ]
    }
  ],
  "max_tokens": 100
}
```

**Response**:
```json
{
  "choices": [
    {
      "message": {
        "content": "[\"label1\", \"label2\", \"label3\"]"
      }
    }
  ]
}
```

## UI/UX Design Specifications

### Visual Design System

**Colors**:
- Primary: `#3b82f6` (blue-500)
- Secondary: `#8b5cf6` (purple-500)
- Success: `#22c55e` (green-500)
- Error: `#ef4444` (red-500)
- Background: `#ffffff`
- Border: `#e5e7eb` (gray-200)
- Text: `#1f2937` (gray-800)

**Typography**:
- Headings: `font-semibold text-xl`
- Body: `text-base text-gray-700`
- Labels: `text-sm font-medium text-gray-600`

**Spacing**:
- Container padding: `p-6`
- Section gaps: `gap-4`
- Element margins: `mb-3`

**Borders & Shadows**:
- Card border: `border-2 border-gray-200`
- Radius: `rounded-xl` (12px) for containers, `rounded-lg` (8px) for inputs
- Shadow: `shadow-lg hover:shadow-xl` for cards
- Subtle shadow: `shadow-sm` for inputs

### Leader Line Design

**Specification**:
- Line style: Dashed (`stroke-dasharray="4 4"`)
- Line width: `2px`
- Line color: `#6b7280` (gray-500)
- Connection point: Center of segmentation bounding box
- Label end: Small circle/dot anchor
- Label background: White with border and shadow
- Label padding: `px-3 py-2`

**Example SVG**:
```svg
<svg className="absolute inset-0 pointer-events-none">
  <line
    x1={segmentCenter.x}
    y1={segmentCenter.y}
    x2={labelPosition.x}
    y2={labelPosition.y}
    stroke="#6b7280"
    strokeWidth="2"
    strokeDasharray="4 4"
  />
  <circle cx={labelPosition.x} cy={labelPosition.y} r="4" fill="#3b82f6" />
</svg>
```

### Responsive Breakpoints

- Desktop (≥ 1024px): 3-column layout
- Tablet (768-1023px): 2-column (image + stacked controls/results)
- Mobile (< 768px): Single column, stacked

### Accessibility

- All interactive elements have `aria-label`
- Canvas has `role="img"` with descriptive text
- Keyboard navigation for label input
- Focus indicators on all buttons
- Color contrast ratio ≥ 4.5:1

## Performance Considerations

### Image Size Limits

- Max upload size: 10MB
- Max dimensions: 2048x2048
- Auto-resize if exceeds limits (client-side canvas)

### Canvas Optimization

- Use `requestAnimationFrame` for smooth rendering
- Throttle mouse move events (100ms)
- Lazy render labels (only when in viewport)
- Cache rendered mask overlay

### LLM Request Optimization

- Resize image before sending (max 512x512 for LLM)
- Cache suggestions by mask hash
- Debounce suggestion requests (2 seconds)
- Use cheaper models (gpt-4o-mini, claude-haiku)

## Security Considerations

### API Key Management

- Store in `.env.local` (not committed)
- Provide clear setup instructions in docs
- Optional: Allow users to input their own keys (stored in sessionStorage)

### Input Validation

- Validate file types client-side (MIME type + extension)
- Sanitize label input (XSS prevention)
- Limit label count (max 10 per image)

### CORS & CSP

- Ensure Nginx allows commercial frontend origin
- Configure CSP to allow LLM API domains
- Handle CORS preflight for SAM2 API

## Testing Strategy

### Unit Tests

- LabelSuggestionService API mocking
- Canvas coordinate transformations
- Leader line calculations
- Label validation logic

### Integration Tests

- End-to-end segmentation workflow
- LLM suggestion fetching
- Image upload and processing
- Export functionality

### Visual Regression Tests

- Screenshot comparisons for:
  - Dashboard card
  - Modal layout
  - Canvas rendering
  - Label positioning

### Manual Testing Checklist

- [ ] Upload various image formats (PNG, JPG, invalid)
- [ ] Click foreground and background points
- [ ] Trigger segmentation with different point counts
- [ ] Request LLM suggestions (with/without API key)
- [ ] Add, edit, and position labels
- [ ] Export final result
- [ ] Test on different screen sizes
- [ ] Test on different browsers (Chrome, Firefox, Safari)

## Migration & Rollout Plan

### Phase 1: MVP (Week 1-2)
- Dashboard card + modal
- Basic upload and SAM2 integration
- Manual label input
- Simple export

### Phase 2: LLM Integration (Week 3)
- LLM suggestion service
- OpenAI/Anthropic support
- Suggestion UI

### Phase 3: Polish (Week 4)
- Leader line labels
- Advanced styling
- Responsive design
- Performance optimization

### Phase 4: Future Enhancements
- DICOM support
- Multi-region segmentation
- Save/load sessions
- Share demo link

## Open Questions

1. **LLM Model Selection**: Which model provides best balance of cost/quality?
   - Recommendation: Start with `gpt-4o-mini` (fast, cheap, good vision)

2. **User API Keys**: Should we support user-provided API keys?
   - Recommendation: Optional feature for power users

3. **Result Storage**: Should demo results be saved to database?
   - Recommendation: No for MVP; add later if users request

4. **Analytics**: Should we track demo usage metrics?
   - Recommendation: Yes - track: images uploaded, segmentations completed, LLM requests

5. **Commercial Integration**: Should successful demos prompt subscription upgrade?
   - Recommendation: Yes - add "Upgrade for unlimited use" CTA after 3 demos

## Conclusion

This design provides a comprehensive blueprint for implementing the Commercial SAM2 Interactive Demo. The architecture balances:

- **Simplicity**: Minimal backend changes, reuse existing services
- **User Experience**: Modern UI, intelligent suggestions, smooth workflow
- **Scalability**: Can evolve to support more features
- **Maintainability**: Clear component boundaries, testable code

Next steps: Create detailed spec deltas for each capability and implementation task breakdown.
