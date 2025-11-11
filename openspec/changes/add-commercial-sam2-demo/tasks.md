# Implementation Tasks

This document outlines the ordered, verifiable tasks required to implement the Commercial SAM2 Interactive Demo feature.

## Task Status Legend
- ⏸️ Pending: Not yet started
- 🏗️ In Progress: Currently being worked on
- ✅ Done: Completed and verified
- 🧪 Testing: Implementation complete, under test

---

## Phase 1: Foundation & Setup (1-2 days)

### Task 1.1: Project Structure Setup
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking)
**Estimated Time**: 1 hour

**Description**: Create necessary directories and configuration files for the demo feature.

**Steps**:
1. Create directory: `commercial/frontend/src/components/demo/`
2. Create directory: `commercial/frontend/src/services/demo/`
3. Create TypeScript types file: `commercial/frontend/src/types/demo.ts`
4. Add environment variables to `.env.example`:
   ```
   VITE_LLM_PROVIDER=openai # or anthropic, none, mock
   VITE_LLM_API_KEY=your_api_key_here
   VITE_LLM_MODEL=gpt-4o-mini
   VITE_LLM_DEBUG=false
   ```
5. Update `.gitignore` to exclude `.env.local`

**Verification**:
- [ ] Directories exist and are accessible
- [ ] Types file compiles without errors
- [ ] `.env.example` contains all required variables
- [ ] `.env.local` is not tracked by git

**Dependencies**: None

---

### Task 1.2: TypeScript Type Definitions
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking)
**Estimated Time**: 1 hour

**Description**: Define all TypeScript interfaces and types for the demo feature.

**Steps**:
1. Create `src/types/demo.ts` with interfaces:
   - `ClickPoint { x: number, y: number, label: 0 | 1 }`
   - `SegmentationResult { mask_data: string, confidence_score: number, processing_time_ms: number, bounding_box: BoundingBox, cached: boolean }`
   - `BoundingBox { x: number, y: number, width: number, height: number }`
   - `Label { id: string, text: string, position: Point, segmentCenter: Point }`
   - `Point { x: number, y: number }`
   - `LLMProvider = "openai" | "anthropic" | "none" | "mock"`
   - `DemoState { uploadedImage, imageMetadata, clickPoints, segmentationMask, labels, isSegmenting, isFetchingSuggestions, error }`

**Verification**:
- [ ] All types are exported
- [ ] No TypeScript compilation errors
- [ ] Types are documented with JSDoc comments

**Dependencies**: Task 1.1

---

### Task 1.3: Environment Configuration Service
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 1 hour

**Description**: Create a service to read and validate environment variables.

**Steps**:
1. Create `src/utils/envConfig.ts`
2. Implement `getEnvConfig()` function that reads VITE_* variables
3. Add validation for LLM_PROVIDER (must be valid enum value)
4. Add warning logs for missing API keys
5. Export config object with typed properties

**Verification**:
- [ ] Function returns valid config object
- [ ] Invalid provider defaults to "none" with warning
- [ ] Missing API key logs warning but doesn't crash
- [ ] Config is readonly (TypeScript)

**Dependencies**: Task 1.2

---

## Phase 2: Core UI Components (2-3 days)

### Task 2.1: Dashboard Card Component
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking)
**Estimated Time**: 2 hours

**Description**: Create the dashboard entry point card for the demo feature.

**Steps**:
1. Create `src/components/demo/DemoSegmentationCard.tsx`
2. Implement card with:
   - Magic wand icon (from lucide-react)
   - Title: "AI Image Segmentation Demo"
   - Subtitle: "Try SAM2 interactive segmentation"
   - Modern border and shadow styling
   - Hover animations (scale + shadow)
3. Add click handler to open modal
4. Integrate into `DashboardPage.tsx` in the quick actions grid

**Verification**:
- [ ] Card renders in dashboard
- [ ] Styling matches shadcn/ui design system
- [ ] Hover effects work smoothly
- [ ] Click opens modal (placeholder OK for now)
- [ ] Responsive on mobile/tablet/desktop

**Dependencies**: Task 1.2

---

### Task 2.2: Modal Container Component
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking)
**Estimated Time**: 2 hours

**Description**: Create modal wrapper for the demo interface.

**Steps**:
1. Create `src/components/demo/DemoModal.tsx` using shadcn/ui Dialog
2. Configure modal:
   - Full-screen on mobile
   - Large size on desktop (80% width, 90% height)
   - Close button in top-right
   - Prevent close on outside click
   - ESC key to close
3. Add state management in DashboardPage for `isModalOpen`
4. Pass `onClose` callback to modal

**Verification**:
- [ ] Modal opens when card is clicked
- [ ] Modal closes on ESC or close button
- [ ] Modal doesn't close on backdrop click
- [ ] Focus traps correctly
- [ ] Accessible (ARIA labels present)

**Dependencies**: Task 2.1

---

### Task 2.3: Image Upload Component
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking)
**Estimated Time**: 3 hours

**Description**: Create drag-and-drop image upload interface.

**Steps**:
1. Create `src/components/demo/ImageUploadZone.tsx`
2. Implement drag-and-drop handlers:
   - `onDragEnter`, `onDragOver`, `onDragLeave`, `onDrop`
3. Implement file input click handler
4. Add validation:
   - Check MIME type (image/png, image/jpeg)
   - Check file size (< 10MB)
   - Check dimensions (resize if > 2048x2048)
5. Add preview after successful upload
6. Emit `onImageLoaded(imageUrl, metadata)` event

**Verification**:
- [ ] Drag-and-drop works
- [ ] File browser works
- [ ] Invalid formats show error toast
- [ ] Large files show error toast
- [ ] Oversized images are resized client-side
- [ ] Preview displays correctly

**Dependencies**: Task 2.2

---

### Task 2.4: Canvas Component (Base)
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking)
**Estimated Time**: 4 hours

**Description**: Create the interactive canvas for displaying images and handling clicks.

**Steps**:
1. Create `src/components/demo/SAM2Canvas.tsx`
2. Set up canvas refs and context
3. Implement image rendering:
   - Load image onto canvas
   - Calculate scale to fit modal
   - Maintain aspect ratio
4. Implement click handling:
   - Left-click: add foreground point
   - Right-click: add background point
   - Transform canvas coords to image coords
5. Implement point rendering:
   - Green circles for foreground (label=1)
   - Red circles for background (label=0)
6. Add hover effects on points

**Verification**:
- [ ] Image renders correctly
- [ ] Clicking adds points at correct positions
- [ ] Right-click prevents context menu
- [ ] Point colors are correct
- [ ] Coordinate transformation is accurate
- [ ] Canvas resizes with modal

**Dependencies**: Task 2.3

---

### Task 2.5: Control Panel Component
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 2 hours

**Description**: Create UI controls for segmentation actions.

**Steps**:
1. Create `src/components/demo/ControlPanel.tsx`
2. Add buttons:
   - "Run Segmentation" (primary, disabled if no click points)
   - "Clear Points" (secondary, disabled if no points)
   - "Start Over" (outline, always enabled)
3. Add click point counter display
4. Add instruction text (changes based on state)
5. Wire up button click handlers

**Verification**:
- [ ] Buttons render with correct styling
- [ ] Disabled states work correctly
- [ ] Click handlers fire events to parent
- [ ] Counter updates accurately
- [ ] Instructions change contextually

**Dependencies**: Task 2.4

---

### Task 2.6: Label Input Panel Component
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 3 hours

**Description**: Create interface for adding labels to segmented regions.

**Steps**:
1. Create `src/components/demo/LabelInputPanel.tsx`
2. Add text input with character counter (max 50)
3. Add "Add Label" button
4. Add "Get AI Suggestions" button (only if LLM configured)
5. Add suggestion chips display
6. Implement label addition logic
7. Implement suggestion chip click handler

**Verification**:
- [ ] Input validates max length
- [ ] Character counter updates
- [ ] "Add Label" adds label to list
- [ ] Input clears after adding
- [ ] Suggestion chips render when available
- [ ] Clicking chip populates input

**Dependencies**: Task 2.5

---

### Task 2.7: Results Panel Component
**Status**: ⏸️ Pending
**Priority**: P2
**Estimated Time**: 2 hours

**Description**: Display segmentation results and statistics.

**Steps**:
1. Create `src/components/demo/ResultsPanel.tsx`
2. Display confidence score with color coding
3. Display processing time
4. Display cached indicator if applicable
5. Display bounding box dimensions
6. Add "Export Result" button
7. Style panel consistently with design system

**Verification**:
- [ ] All metrics display correctly
- [ ] Confidence score color changes with value
- [ ] Cached badge appears when appropriate
- [ ] Export button is functional (placeholder OK)

**Dependencies**: Task 2.5

---

## Phase 3: SAM2 Integration (1 day)

### Task 3.1: SAM2 Service Implementation
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking)
**Estimated Time**: 3 hours

**Description**: Create service for communicating with SAM2 API.

**Steps**:
1. Create `src/services/demo/demoSAM2Service.ts`
2. Import `idoctorAPI` instance from `src/services/api.ts`
3. Implement `segmentWithClicks(imageFile, clickPoints)`:
   - Build FormData payload
   - Send POST to `/api/ctai/api/segmentation/sam2`
   - Handle response
   - Return SegmentationResult
4. Implement `checkServiceHealth()`:
   - Ping SAM2 health endpoint
   - Return boolean
5. Add error handling for all HTTP status codes

**Verification**:
- [ ] Service successfully calls SAM2 API
- [ ] FormData is correctly structured
- [ ] Response is properly typed
- [ ] Errors are caught and formatted
- [ ] Health check works

**Dependencies**: Task 1.2, Task 1.3

---

### Task 3.2: Mask Rendering Logic
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking)
**Estimated Time**: 3 hours

**Description**: Implement mask decoding and overlay rendering.

**Steps**:
1. Add `renderMask()` method to SAM2Canvas component
2. Decode base64 mask data to Image object
3. Draw mask as semi-transparent overlay (40% opacity)
4. Apply green tint (#22c55e)
5. Draw bounding box with dashed outline
6. Handle mask scaling for canvas display size

**Verification**:
- [ ] Mask displays correctly aligned with image
- [ ] Mask has correct opacity
- [ ] Bounding box is visible
- [ ] Mask scales with canvas resize
- [ ] No performance issues on large images

**Dependencies**: Task 2.4, Task 3.1

---

### Task 3.3: Segmentation Workflow Integration
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking)
**Estimated Time**: 2 hours

**Description**: Connect UI components to SAM2 service.

**Steps**:
1. Add state management in main demo component for:
   - `isSegmenting: boolean`
   - `segmentationMask: string | null`
   - `segmentationResult: SegmentationResult | null`
2. Implement `handleRunSegmentation()` function:
   - Call SAM2 service
   - Update state on success/error
   - Show loading overlay
3. Wire "Run Segmentation" button to handler
4. Update canvas to display mask when available
5. Update results panel with metadata

**Verification**:
- [ ] Clicking "Run Segmentation" calls API
- [ ] Loading state shows during request
- [ ] Mask renders on success
- [ ] Error toast shows on failure
- [ ] Results panel updates with data

**Dependencies**: Task 3.1, Task 3.2

---

### Task 3.4: Error Handling and Retry Logic
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 2 hours

**Description**: Implement comprehensive error handling for SAM2 API.

**Steps**:
1. Handle 402 (quota exhausted) with upgrade modal
2. Handle 503 (service unavailable) with retry button
3. Handle timeout (30s) with error message
4. Handle network errors with retry option
5. Add retry functionality with exponential backoff (optional)

**Verification**:
- [ ] All error types show appropriate messages
- [ ] Retry button appears when relevant
- [ ] Quota modal redirects to subscription page
- [ ] Errors don't crash the app

**Dependencies**: Task 3.3

---

## Phase 4: LLM Integration (1-2 days)

### Task 4.1: LLM Service Foundation
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 2 hours

**Description**: Create base service for LLM API communication.

**Steps**:
1. Create `src/services/demo/llmService.ts`
2. Implement provider selection based on env config
3. Create abstract `LLMProvider` interface with `getSuggestions()` method
4. Implement factory function to return correct provider

**Verification**:
- [ ] Service correctly selects provider based on config
- [ ] Returns "none" provider when LLM disabled
- [ ] No errors when API key missing (graceful degradation)

**Dependencies**: Task 1.3

---

### Task 4.2: OpenAI Provider Implementation
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 3 hours

**Description**: Implement OpenAI-specific LLM integration.

**Steps**:
1. Create `src/services/demo/providers/openaiProvider.ts`
2. Implement `getSuggestions()` method:
   - Extract and resize segmented region (max 512x512)
   - Convert to base64
   - Build request payload with vision API format
   - Send to `https://api.openai.com/v1/chat/completions`
   - Parse response as JSON array
   - Return string[] of suggestions
3. Add error handling for API errors
4. Add timeout (15 seconds)

**Verification**:
- [ ] Successfully calls OpenAI API
- [ ] Request payload is correctly formatted
- [ ] Response is correctly parsed
- [ ] Returns valid array of strings
- [ ] Handles errors gracefully

**Dependencies**: Task 4.1

---

### Task 4.3: Anthropic Provider Implementation
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 3 hours

**Description**: Implement Anthropic-specific LLM integration.

**Steps**:
1. Create `src/services/demo/providers/anthropicProvider.ts`
2. Implement `getSuggestions()` method:
   - Extract and resize segmented region (max 512x512)
   - Convert to base64 (without data URI prefix for Anthropic)
   - Build request payload with Messages API format
   - Send to `https://api.anthropic.com/v1/messages`
   - Parse response from `content[0].text`
   - Return string[] of suggestions
3. Add error handling
4. Add timeout (15 seconds)

**Verification**:
- [ ] Successfully calls Anthropic API
- [ ] Request payload matches Anthropic format
- [ ] Response is correctly parsed
- [ ] Returns valid array of strings
- [ ] Handles errors gracefully

**Dependencies**: Task 4.1

---

### Task 4.4: Mock Provider for Testing
**Status**: ⏸️ Pending
**Priority**: P2
**Estimated Time**: 1 hour

**Description**: Create mock LLM provider for development/testing.

**Steps**:
1. Create `src/services/demo/providers/mockProvider.ts`
2. Return hardcoded suggestions: `["region_1", "segment_area", "highlighted_section"]`
3. Add simulated 2-second delay
4. Randomly fail 10% of requests for error testing

**Verification**:
- [ ] Mock provider returns consistent results
- [ ] Delay is noticeable but not blocking
- [ ] Random failures work as expected
- [ ] Useful for testing without API keys

**Dependencies**: Task 4.1

---

### Task 4.5: LLM UI Integration
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 2 hours

**Description**: Connect LLM service to UI components.

**Steps**:
1. Add "Get AI Suggestions" button to LabelInputPanel
2. Implement click handler:
   - Show loading state
   - Call LLM service
   - Display suggestions as chips
   - Handle errors
3. Add first-time consent modal (optional, can defer)
4. Add caching logic (sessionStorage)

**Verification**:
- [ ] Button triggers LLM request
- [ ] Loading state displays during request
- [ ] Suggestions appear as clickable chips
- [ ] Clicking chip populates input
- [ ] Errors show toast messages
- [ ] Cached suggestions load instantly

**Dependencies**: Task 4.2 OR Task 4.3, Task 2.6

---

### Task 4.6: LLM Caching and Rate Limiting
**Status**: ⏸️ Pending
**Priority**: P2
**Estimated Time**: 2 hours

**Description**: Implement client-side optimizations for LLM usage.

**Steps**:
1. Add caching logic:
   - Hash mask bounding box as cache key
   - Store in sessionStorage with timestamp
   - Check cache before API call (TTL: 30 minutes)
2. Add request debouncing (3 seconds)
3. Add request counter (warn at 10 requests/session)

**Verification**:
- [ ] Cache hits return instantly
- [ ] Cache expires after 30 minutes
- [ ] Rapid clicks don't trigger multiple requests
- [ ] Warning appears after 10 requests
- [ ] Cache clears on session end

**Dependencies**: Task 4.5

---

## Phase 5: Leader Lines & Labels (1 day)

### Task 5.1: Leader Line Rendering
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 3 hours

**Description**: Implement SVG leader lines connecting labels to segments.

**Steps**:
1. Create `src/components/demo/LeaderLines.tsx` component
2. Calculate line path from segment center to label position
3. Render SVG line element with:
   - Dashed style (`stroke-dasharray: 4 4`)
   - 2px width
   - Gray color (#6b7280)
4. Render anchor circle at label end
5. Position SVG overlay absolute on canvas

**Verification**:
- [ ] Lines draw correctly from segment to label
- [ ] Lines are dashed
- [ ] Anchor circles appear
- [ ] Lines update when label is dragged
- [ ] No performance issues with multiple labels

**Dependencies**: Task 2.6

---

### Task 5.2: Draggable Label Implementation
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 2 hours

**Description**: Make labels draggable to reposition them.

**Steps**:
1. Add mouse event handlers to label elements:
   - `onMouseDown`: start drag
   - `onMouseMove`: update position
   - `onMouseUp`: end drag
2. Update label position in state
3. Trigger leader line redraw on position change
4. Add hover state (change background, show move cursor)

**Verification**:
- [ ] Labels can be dragged
- [ ] Leader lines update during drag
- [ ] Position persists after drag
- [ ] Hover cursor changes to "move"
- [ ] Dragging feels smooth (no lag)

**Dependencies**: Task 5.1

---

### Task 5.3: Label Collision Avoidance (Optional)
**Status**: ⏸️ Pending
**Priority**: P3 (Nice-to-have)
**Estimated Time**: 3 hours

**Description**: Automatically position labels to avoid overlaps.

**Steps**:
1. Implement simple collision detection
2. When adding new label, check for overlaps with existing labels
3. Adjust position slightly if collision detected
4. Use basic offset algorithm (try positions around segment in circular pattern)

**Verification**:
- [ ] Multiple labels don't overlap (mostly)
- [ ] Automatic positioning looks reasonable
- [ ] User can still manually drag if needed
- [ ] Performance is acceptable

**Dependencies**: Task 5.2

**Note**: This task can be deferred if time-constrained.

---

## Phase 6: Export & Polish (1 day)

### Task 6.1: Export Functionality
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 3 hours

**Description**: Implement export of annotated image.

**Steps**:
1. Create `src/utils/exportCanvas.ts` utility
2. Implement composite rendering:
   - Create offscreen canvas with original image dimensions
   - Draw base image
   - Draw mask overlay
   - Draw all labels (positioned correctly)
   - Draw leader lines
3. Convert canvas to PNG blob
4. Trigger browser download with filename: `segmentation_result_<timestamp>.png`
5. Wire "Export Result" button to export function

**Verification**:
- [ ] Export includes all visual elements
- [ ] Resolution matches original image
- [ ] Labels are readable
- [ ] Download triggers correctly
- [ ] Filename is unique (timestamp)

**Dependencies**: Task 5.1, Task 3.2

---

### Task 6.2: Responsive Layout Implementation
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 2 hours

**Description**: Make demo interface responsive across screen sizes.

**Steps**:
1. Add Tailwind breakpoint classes to main layout:
   - Desktop (≥1024px): 3-column grid
   - Tablet (768-1023px): 2-column grid
   - Mobile (<768px): stacked layout
2. Adjust modal size for mobile (full-screen)
3. Adjust canvas max height for mobile (400px)
4. Test on different screen sizes

**Verification**:
- [ ] Desktop layout uses 3 columns
- [ ] Tablet layout uses 2 columns
- [ ] Mobile layout stacks vertically
- [ ] All controls remain accessible
- [ ] No horizontal scrolling

**Dependencies**: Task 2.2

---

### Task 6.3: Loading States and Skeletons
**Status**: ⏸️ Pending
**Priority**: P2
**Estimated Time**: 2 hours

**Description**: Add polished loading states throughout UI.

**Steps**:
1. Create skeleton loader for initial modal load
2. Add spinner overlay for canvas during segmentation
3. Add spinner icon to "Get AI Suggestions" button when loading
4. Add fade-in transitions for mask and suggestions
5. Add progress text: "AI is analyzing..." with estimated time

**Verification**:
- [ ] Skeleton displays on modal open
- [ ] Segmentation shows loading overlay
- [ ] LLM button shows loading state
- [ ] Transitions are smooth
- [ ] User knows what's happening at all times

**Dependencies**: Multiple (Task 3.3, Task 4.5)

---

### Task 6.4: Accessibility Audit and Fixes
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 2 hours

**Description**: Ensure WCAG 2.1 AA compliance.

**Steps**:
1. Add ARIA labels to all interactive elements
2. Add `role="img"` and `aria-label` to canvas
3. Ensure focus indicators are visible
4. Test keyboard navigation (Tab order)
5. Test with screen reader (VoiceOver on Mac)
6. Fix any contrast ratio issues
7. Add live regions for dynamic content (`aria-live`)

**Verification**:
- [ ] All elements have proper ARIA attributes
- [ ] Keyboard navigation works
- [ ] Focus indicators are visible
- [ ] Screen reader announces content correctly
- [ ] Color contrast meets WCAG AA
- [ ] Lighthouse accessibility score ≥ 95

**Dependencies**: All UI tasks

---

### Task 6.5: Error Boundary and Fallback UI
**Status**: ⏸️ Pending
**Priority**: P2
**Estimated Time**: 1 hour

**Description**: Add error boundary to gracefully handle crashes.

**Steps**:
1. Create `src/components/demo/DemoErrorBoundary.tsx`
2. Wrap main demo component with error boundary
3. Display user-friendly error message on crash
4. Add "Reload" button to reset state
5. Log errors to console for debugging

**Verification**:
- [ ] Simulated error is caught
- [ ] Fallback UI displays
- [ ] Reload button works
- [ ] Error is logged
- [ ] Rest of app continues working

**Dependencies**: Task 2.2

---

## Phase 7: Testing & Documentation (1 day)

### Task 7.1: Unit Tests for Services
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 3 hours

**Description**: Write unit tests for core services.

**Steps**:
1. Test `demoSAM2Service.ts`:
   - Mock axios responses
   - Test successful segmentation
   - Test error scenarios (timeout, 402, 503, network error)
2. Test `llmService.ts`:
   - Mock provider responses
   - Test OpenAI provider
   - Test Anthropic provider
   - Test caching logic
3. Run tests: `npm test`

**Verification**:
- [ ] All service tests pass
- [ ] Coverage ≥ 80% for services
- [ ] Edge cases are covered

**Dependencies**: Task 3.1, Task 4.1

---

### Task 7.2: Integration Tests
**Status**: ⏸️ Pending
**Priority**: P2
**Estimated Time**: 2 hours

**Description**: Test end-to-end workflows.

**Steps**:
1. Write Cypress or Playwright test:
   - Open dashboard
   - Click demo card
   - Upload image
   - Click to add points
   - Run segmentation (mocked API)
   - Add label
   - Export result
2. Run test: `npm run test:e2e`

**Verification**:
- [ ] E2E test passes
- [ ] Workflow completes without errors
- [ ] All interactions work as expected

**Dependencies**: All implementation tasks

---

### Task 7.3: Manual Testing Checklist
**Status**: ⏸️ Pending
**Priority**: P1
**Estimated Time**: 2 hours

**Description**: Perform comprehensive manual testing.

**Steps**:
1. Test on browsers: Chrome, Firefox, Safari
2. Test on devices: Desktop, tablet, mobile
3. Test scenarios:
   - Upload various image formats (PNG, JPG, invalid)
   - Add many click points (test limit)
   - Run segmentation with 0, 1, 5, 50 points
   - Trigger LLM suggestions (with real API key if available)
   - Drag labels around
   - Export result
   - Start over and repeat
4. Document any bugs found

**Verification**:
- [ ] All scenarios tested
- [ ] No critical bugs found
- [ ] UX feels smooth
- [ ] Performance is acceptable

**Dependencies**: Task 6.5

---

### Task 7.4: Documentation Updates
**Status**: ⏸️ Pending
**Priority**: P2
**Estimated Time**: 2 hours

**Description**: Update project documentation.

**Steps**:
1. Update `commercial/frontend/DEVELOPMENT_GUIDE.md`:
   - Add demo feature section
   - Document LLM configuration
   - Add screenshots (optional)
2. Create `commercial/docs/DEMO_FEATURE_GUIDE.md`:
   - User guide for the demo
   - Configuration guide for LLM
   - Troubleshooting section
3. Update README with demo feature mention

**Verification**:
- [ ] Documentation is clear and accurate
- [ ] Configuration steps are complete
- [ ] Troubleshooting covers common issues

**Dependencies**: Task 7.3

---

## Phase 8: Deployment & Validation (0.5 days)

### Task 8.1: Build and Deploy to Dev
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking for release)
**Estimated Time**: 1 hour

**Description**: Build and deploy to development environment.

**Steps**:
1. Run build: `npm run build`
2. Fix any build errors
3. Deploy to dev Nginx: `bash commercial/scripts/deploy-frontend.sh dev`
4. Verify deployment: access via http://localhost:3000

**Verification**:
- [ ] Build completes without errors
- [ ] Deployment script succeeds
- [ ] Feature is accessible on dev environment
- [ ] No console errors in browser

**Dependencies**: Task 7.3

---

### Task 8.2: Production Environment Variable Setup
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking for release)
**Estimated Time**: 30 minutes

**Description**: Configure production environment variables.

**Steps**:
1. Add LLM config to `commercial/docker/.env.prod`:
   ```
   VITE_LLM_PROVIDER=openai
   VITE_LLM_API_KEY=<redacted>
   VITE_LLM_MODEL=gpt-4o-mini
   ```
2. Ensure API key is secured (not in git)
3. Document key rotation procedure

**Verification**:
- [ ] Env vars are set in production config
- [ ] API key is not in version control
- [ ] Build uses production env vars

**Dependencies**: Task 1.1

---

### Task 8.3: Smoke Testing in Production
**Status**: ⏸️ Pending
**Priority**: P0 (Blocking for release)
**Estimated Time**: 1 hour

**Description**: Perform smoke tests on production deployment.

**Steps**:
1. Access production URL
2. Test complete workflow:
   - Login
   - Open demo from dashboard
   - Upload image
   - Run segmentation
   - Get LLM suggestions (if enabled)
   - Add label
   - Export
3. Monitor for errors in browser console
4. Check Nginx and backend logs for errors

**Verification**:
- [ ] All core features work in production
- [ ] No critical errors
- [ ] Performance is acceptable
- [ ] LLM integration works (if enabled)

**Dependencies**: Task 8.1, Task 8.2

---

## Task Dependencies Graph

```
Phase 1 (Setup)
  1.1 → 1.2 → 1.3

Phase 2 (UI)
  1.2 → 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6, 2.7

Phase 3 (SAM2)
  1.2, 1.3 → 3.1
  2.4, 3.1 → 3.2
  3.1, 3.2 → 3.3 → 3.4

Phase 4 (LLM)
  1.3 → 4.1 → 4.2, 4.3, 4.4
  4.2/4.3, 2.6 → 4.5 → 4.6

Phase 5 (Labels)
  2.6 → 5.1 → 5.2 → 5.3 (optional)

Phase 6 (Polish)
  5.1, 3.2 → 6.1
  2.2 → 6.2
  3.3, 4.5 → 6.3
  All UI → 6.4
  2.2 → 6.5

Phase 7 (Testing)
  3.1, 4.1 → 7.1
  All → 7.2, 7.3 → 7.4

Phase 8 (Deploy)
  7.3 → 8.1
  1.1 → 8.2
  8.1, 8.2 → 8.3
```

---

## Critical Path (Minimum Viable Product)

For the fastest path to a working demo, prioritize these tasks:

1. ✅ **Foundation**: 1.1, 1.2, 1.3
2. ✅ **Basic UI**: 2.1, 2.2, 2.3, 2.4, 2.5
3. ✅ **SAM2 Core**: 3.1, 3.2, 3.3
4. ✅ **Labels**: 2.6, 5.1, 5.2
5. ✅ **Export**: 6.1
6. ✅ **Testing**: 7.3
7. ✅ **Deploy**: 8.1, 8.3

**Estimated Time for MVP**: 5-6 days

**Deferred for v2**:
- Task 3.4 (Retry logic - can use basic error handling)
- All Phase 4 tasks (LLM integration - manual labels work fine)
- Task 5.3 (Collision avoidance)
- Task 6.2 (Responsive - desktop-first is OK)
- Task 6.3 (Loading polish)
- Task 6.4 (Accessibility audit)
- Task 7.1, 7.2 (Automated tests)
- Task 7.4 (Documentation)

---

## Progress Tracking

| Phase | Total Tasks | Completed | In Progress | Pending |
|-------|-------------|-----------|-------------|---------|
| 1: Setup | 3 | 0 | 0 | 3 |
| 2: UI | 7 | 0 | 0 | 7 |
| 3: SAM2 | 4 | 0 | 0 | 4 |
| 4: LLM | 6 | 0 | 0 | 6 |
| 5: Labels | 3 | 0 | 0 | 3 |
| 6: Polish | 5 | 0 | 0 | 5 |
| 7: Testing | 4 | 0 | 0 | 4 |
| 8: Deploy | 3 | 0 | 0 | 3 |
| **TOTAL** | **35** | **0** | **0** | **35** |

---

## Risk Mitigation

| Risk | Task(s) Affected | Mitigation |
|------|------------------|------------|
| SAM2 service latency | 3.3 | Add loading indicators, set 30s timeout, cache results |
| LLM API costs | 4.2, 4.3, 4.6 | Implement caching, rate limiting, use cheap models |
| Cross-origin issues | 3.1 | Verify Nginx CORS config, test early |
| Canvas performance | 2.4, 3.2, 5.1 | Optimize redraw logic, throttle events, test with large images |
| Time constraints | All | Focus on critical path first, defer optional features |

---

## Daily Milestones (Aggressive Timeline)

**Day 1**: Phase 1 + Phase 2 (Tasks 1.1-2.5) - "UI Foundation"
**Day 2**: Phase 2 + Phase 3 (Tasks 2.6-3.3) - "SAM2 Integration"
**Day 3**: Phase 3 + Phase 5 (Tasks 3.4-5.2) - "Labels & Lines"
**Day 4**: Phase 4 (Tasks 4.1-4.6) - "LLM Integration"
**Day 5**: Phase 6 (Tasks 6.1-6.5) - "Polish & UX"
**Day 6**: Phase 7 (Tasks 7.1-7.4) - "Testing & Docs"
**Day 7**: Phase 8 (Tasks 8.1-8.3) - "Deploy & Validate"

---

## Success Criteria

✅ **MVP Success** (End of Day 5):
- [ ] Demo accessible from dashboard
- [ ] Can upload image, click points, run segmentation
- [ ] Mask displays correctly
- [ ] Can add labels manually
- [ ] Can export annotated image
- [ ] No critical bugs

✅ **Full Feature Success** (End of Day 7):
- [ ] All MVP criteria met
- [ ] LLM suggestions work (OpenAI OR Anthropic)
- [ ] Labels have leader lines
- [ ] Labels are draggable
- [ ] Responsive layout works
- [ ] Accessibility audit passed
- [ ] Deployed to production

---

**Last Updated**: 2025-01-11
**Total Estimated Time**: 80-100 hours (10-12.5 working days for 1 developer)
**Realistic Timeline**: 2 weeks with buffer
