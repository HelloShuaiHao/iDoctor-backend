# demo-sam2-integration Specification Delta

## Purpose

Defines requirements for integrating SAM2 (Segment Anything Model 2) segmentation capabilities into the Commercial Demo feature, adapted for general-purpose images (PNG/JPG) rather than medical DICOM data.

## ADDED Requirements

### Requirement: Commercial SAM2 Client Service

The commercial frontend SHALL implement a dedicated service for communicating with the SAM2 API for demo purposes.

#### Scenario: Service initialization
- **WHEN** ImageSegmentationDemo component mounts
- **THEN** a `DemoSAM2Service` instance SHALL be created
- **AND** the service SHALL use the `idoctorAPI` axios instance (configured for `http://localhost:4200`)
- **AND** the service SHALL include authentication headers from localStorage (`access_token`)
- **AND** the service SHALL have a default timeout of 30 seconds for segmentation requests

#### Scenario: Service API structure
- **WHEN** DemoSAM2Service is implemented
- **THEN** it SHALL expose the following methods:
  - `async segmentWithClicks(imageFile: File, clickPoints: ClickPoint[]): Promise<SegmentationResult>`
  - `async checkServiceHealth(): Promise<boolean>`
  - `clearCache(): void`

#### Scenario: Service health check
- **WHEN** demo modal opens
- **THEN** the service SHALL call `checkServiceHealth()` to verify SAM2 service availability
- **AND** if health check fails, display warning banner: "AI Segmentation service unavailable. Please try again later."
- **AND** disable the canvas click interactions
- **AND** show a "Contact Support" link in the warning banner

---

### Requirement: SAM2 Segmentation Request for General Images

The system SHALL send properly formatted segmentation requests to the SAM2 API adapted for non-medical images.

#### Scenario: Build segmentation request payload
- **WHEN** user clicks "Run Segmentation" button with ≥1 click points
- **THEN** the system SHALL create a FormData payload with:
  - `imageFile`: Original uploaded image (File/Blob object)
  - `imageType`: String literal `"demo"` (new type for commercial demo)
  - `patientId`: String literal `"demo-user"` (placeholder)
  - `sliceIndex`: String literal `"0"` (placeholder)
  - `clickPoints`: JSON string array of `{x: number, y: number, label: 0|1}` objects

#### Scenario: Image coordinate normalization
- **WHEN** preparing click points for API request
- **THEN** click point coordinates SHALL be in the original image dimensions (not canvas display dimensions)
- **AND** coordinates SHALL be integers (rounded if necessary)
- **AND** coordinates SHALL be validated to be within image bounds: `0 <= x < width, 0 <= y < height`
- **AND** invalid click points SHALL be filtered out before sending

#### Scenario: Send segmentation request
- **WHEN** FormData payload is prepared
- **THEN** send POST request to `/api/ctai/api/segmentation/sam2`
- **AND** set `Content-Type: multipart/form-data` header automatically via FormData
- **AND** set timeout to 30000ms
- **AND** display loading overlay on canvas with progress indicator

#### Scenario: Successful segmentation response
- **WHEN** SAM2 API returns HTTP 200 with valid response
- **THEN** the response SHALL be validated to contain:
  - `mask_data`: Non-empty base64-encoded PNG string
  - `confidence_score`: Number between 0.0 and 1.0
  - `processing_time_ms`: Positive number
  - `bounding_box`: Object with `{x, y, width, height}` (all non-negative numbers)
  - `cached`: Boolean
- **AND** if validation passes, return the response as `SegmentationResult` type
- **AND** if validation fails, throw error: "Invalid response format from SAM2 service"

---

### Requirement: Mask Rendering and Visualization

The system SHALL decode and render SAM2-generated masks on the canvas with proper alignment.

#### Scenario: Decode base64 mask
- **WHEN** segmentation response contains `mask_data`
- **THEN** the system SHALL create an Image object with `src = data:image/png;base64,${mask_data}`
- **AND** wait for image load event before proceeding
- **AND** if image fails to load within 5 seconds, throw error: "Failed to decode segmentation mask"

#### Scenario: Render mask overlay
- **WHEN** mask image is successfully loaded
- **THEN** the system SHALL draw the mask on a separate canvas layer above the original image
- **AND** the mask SHALL be scaled to match the displayed canvas dimensions (same scale as original image)
- **AND** the mask SHALL use green color tint: `ctx.globalCompositeOperation = 'source-over'` with opacity 0.4
- **AND** the mask SHALL align pixel-perfectly with the original image (same top-left origin)

#### Scenario: Mask with bounding box highlight
- **WHEN** mask is rendered
- **THEN** the bounding box from the response SHALL be drawn as a thin rectangle outline
- **AND** the rectangle SHALL use color `#22c55e` (green-500) with 2px stroke width
- **AND** the rectangle SHALL have dashed style: `ctx.setLineDash([6, 4])`
- **AND** the rectangle coordinates SHALL be scaled proportionally to canvas display size

#### Scenario: Multiple segmentation attempts
- **WHEN** user runs segmentation multiple times on the same image
- **THEN** each new mask SHALL replace the previous mask (not overlay)
- **AND** the canvas SHALL be cleared before drawing new mask
- **AND** click points from previous attempt SHALL remain visible unless explicitly cleared
- **AND** labels from previous attempt SHALL be removed automatically

---

### Requirement: SAM2 Error Handling

The system SHALL gracefully handle various SAM2 API failure scenarios.

#### Scenario: Insufficient click points
- **WHEN** user attempts segmentation with 0 click points
- **THEN** the "Run Segmentation" button SHALL be disabled
- **AND** a tooltip SHALL display on hover: "Add at least one click point to begin"
- **WHEN** button is clicked while disabled (via keyboard)
- **THEN** an error toast SHALL display: "Please add click points to the image first"

#### Scenario: Request timeout
- **WHEN** SAM2 API does not respond within 30 seconds
- **THEN** the request SHALL be aborted
- **AND** the loading overlay SHALL be hidden
- **AND** an error toast SHALL display: "Segmentation timed out. This may happen with very large images. Please try a smaller image or contact support."
- **AND** click points SHALL remain on canvas for retry
- **AND** a "Retry Segmentation" button SHALL appear

#### Scenario: API returns 402 (quota exhausted)
- **WHEN** SAM2 API returns HTTP 402 Payment Required
- **THEN** parse the error response body for quota information
- **AND** display a modal dialog:
  - Title: "Quota Limit Reached"
  - Message: "You've used all your free segmentation credits. Upgrade your plan to continue using AI features."
  - Quota info: `${remaining}/${limit}` or from error body
  - Buttons: "Upgrade Plan" | "Close"
- **WHEN** user clicks "Upgrade Plan"
- **THEN** redirect to `/subscription` page
- **WHEN** user clicks "Close"
- **THEN** close modal and return to demo (manual annotation still available)

#### Scenario: API returns 503 (service unavailable)
- **WHEN** SAM2 API returns HTTP 503 or SAM2 Docker container is not running
- **THEN** parse error message from response body
- **AND** display error toast: "AI Segmentation service is temporarily unavailable. Please try again in a few minutes."
- **AND** log full error to console for debugging
- **AND** disable the "Run Segmentation" button for 60 seconds (show countdown)

#### Scenario: Invalid image format for SAM2
- **WHEN** SAM2 API returns HTTP 400 with message about image format
- **THEN** display error toast: "Image format not supported by AI service. Please try a different image."
- **AND** allow user to upload a new image
- **AND** log the specific error message to console

#### Scenario: Network error
- **WHEN** network request fails entirely (no response, DNS error, connection refused)
- **THEN** catch the network exception
- **AND** display error toast: "Unable to connect to AI service. Please check your internet connection and try again."
- **AND** provide a "Retry" button in the error toast
- **AND** clicking "Retry" SHALL re-send the exact same request

---

### Requirement: Segmentation Result Display

The system SHALL display segmentation metadata to provide feedback on AI performance.

#### Scenario: Display confidence score
- **WHEN** segmentation completes successfully
- **THEN** the confidence score SHALL be displayed in the results panel as a percentage
- **AND** format: `Confidence: ${(score * 100).toFixed(1)}%`
- **AND** color-code the score:
  - Green (#22c55e) if score ≥ 0.8
  - Yellow (#eab308) if 0.5 ≤ score < 0.8
  - Red (#ef4444) if score < 0.5
- **AND** if score < 0.5, show warning: "Low confidence. Try adding more click points for better accuracy."

#### Scenario: Display processing time
- **WHEN** segmentation completes successfully
- **THEN** the processing time SHALL be displayed in the results panel
- **AND** format: `Processed in ${time}ms` or `Processed in ${(time/1000).toFixed(1)}s` if > 1000ms
- **AND** if `cached: true`, append text: `(cached result)`
- **AND** cached results SHALL have a small cache icon next to the time

#### Scenario: Display bounding box dimensions
- **WHEN** segmentation mask is rendered
- **THEN** the results panel SHALL display the segmented region dimensions
- **AND** format: `Region: ${width} × ${height} pixels`
- **AND** calculate region area: `Area: ${width * height} px²`
- **AND** display as a separate line in the results panel

#### Scenario: Cache indicator
- **WHEN** segmentation result is served from cache (`cached: true`)
- **THEN** a subtle badge SHALL display near the processing time: "Cached"
- **AND** badge styling: `bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded`
- **AND** a tooltip SHALL explain: "This result was retrieved from cache for faster response"

---

### Requirement: Click Point Management

The system SHALL allow users to add, visualize, and clear click points for interactive segmentation.

#### Scenario: Add foreground click point
- **WHEN** user left-clicks on the canvas (mouse button 0)
- **THEN** a click point SHALL be added to state with `label: 1` (foreground)
- **AND** coordinates SHALL be captured relative to the original image dimensions
- **AND** a green circle marker SHALL be drawn at the click position
  - Outer circle: radius 8px, stroke `#15803d` (green-700), fill `#22c55e` (green-500), opacity 0.8
  - Inner dot: radius 2px, fill white
- **AND** the click point counter SHALL update: "Click points: X"

#### Scenario: Add background click point
- **WHEN** user right-clicks on the canvas (mouse button 2)
- **THEN** a click point SHALL be added to state with `label: 0` (background)
- **AND** coordinates SHALL be captured relative to original image dimensions
- **AND** a red circle marker SHALL be drawn at the click position
  - Outer circle: radius 8px, stroke `#991b1b` (red-800), fill `#ef4444` (red-500), opacity 0.8
  - Inner dot: radius 2px, fill white
- **AND** the default browser context menu SHALL be prevented (`e.preventDefault()`)

#### Scenario: Click point visualization
- **WHEN** canvas is redrawn (on any state change)
- **THEN** all existing click points SHALL be re-rendered on top of the image and mask
- **AND** points SHALL be drawn in order added (oldest to newest, so newest appears on top if overlapping)
- **AND** each point SHALL be clearly distinguishable (sufficient contrast against any background)

#### Scenario: Clear individual click point
- **WHEN** user hovers over a click point marker
- **THEN** the cursor SHALL change to "pointer"
- **AND** the marker SHALL scale slightly (1.2x) to indicate interactivity
- **WHEN** user Shift+clicks on an existing point
- **THEN** that specific point SHALL be removed from the state
- **AND** the canvas SHALL be redrawn without that point
- **AND** the click point counter SHALL decrement

#### Scenario: Clear all click points
- **WHEN** user clicks the "Clear Points" button
- **THEN** all click points SHALL be removed from state
- **AND** all click point markers SHALL be removed from canvas
- **AND** the counter SHALL reset to: "Click points: 0"
- **AND** any existing segmentation mask SHALL remain visible (not cleared)

#### Scenario: Click point limit
- **WHEN** user has added 50 click points (maximum)
- **THEN** further click attempts SHALL be ignored
- **AND** a warning toast SHALL display: "Maximum 50 click points reached. Clear some points or run segmentation."
- **AND** the "Clear Points" button SHALL be highlighted (pulsing animation)

---

### Requirement: Demo-Specific SAM2 Adaptations

The system SHALL adapt SAM2 functionality for demo use cases distinct from medical DICOM workflows.

#### Scenario: Support general image formats
- **WHEN** user uploads a PNG or JPG file
- **THEN** the image SHALL be processed without DICOM-specific metadata parsing
- **AND** no Hounsfield unit calculations or windowing SHALL be applied
- **AND** the image SHALL be displayed in its original color space (RGB for color images, grayscale for grayscale)

#### Scenario: No patient data association
- **WHEN** segmentation request is sent
- **THEN** the placeholder `patientId: "demo-user"` SHALL be used
- **AND** no results SHALL be stored in patient records database
- **AND** no DICOM metadata SHALL be required or generated

#### Scenario: Simplified result handling
- **WHEN** segmentation completes
- **THEN** results SHALL only be stored in component state (React state, not database)
- **AND** results SHALL be cleared when modal closes or user starts over
- **AND** no annotation history or versioning SHALL be maintained

#### Scenario: Demo mode indicator
- **WHEN** SAM2 API receives request with `imageType: "demo"`
- **THEN** the backend MAY apply different processing optimizations:
  - Skip DICOM-specific preprocessing
  - Use faster inference (lower precision if available)
  - Shorter cache TTL (1 hour instead of 24 hours)
- **AND** the backend SHALL still return the same response format
- **AND** demo requests SHALL be tracked separately in usage quotas (if applicable)

---

### Requirement: Canvas Coordinate System Management

The system SHALL correctly handle coordinate transformations between canvas display and image dimensions.

#### Scenario: Calculate image coordinates from canvas click
- **WHEN** user clicks on the canvas at display position (clientX, clientY)
- **THEN** the system SHALL:
  1. Get canvas bounding rect: `canvas.getBoundingClientRect()`
  2. Calculate click position relative to canvas: `x_canvas = clientX - rect.left`, `y_canvas = clientY - rect.top`
  3. Calculate scale factor: `scale = originalImageWidth / canvas.width`
  4. Transform to image coordinates: `x_image = x_canvas * scale`, `y_image = y_canvas * scale`
  5. Round to integers: `x = Math.round(x_image)`, `y = Math.round(y_image)`
  6. Clamp to image bounds: `x = Math.max(0, Math.min(x, imageWidth - 1))`

#### Scenario: Draw image coordinates on canvas
- **WHEN** rendering click points or masks from image coordinates
- **THEN** the system SHALL:
  1. Calculate canvas scale: `scale = canvas.width / originalImageWidth`
  2. Transform image coordinates to canvas: `x_canvas = x_image * scale`, `y_canvas = y_image * scale`
  3. Draw at transformed position on canvas

#### Scenario: Handle canvas resize
- **WHEN** canvas is resized (modal resize, window resize)
- **THEN** all click points SHALL be recalculated for the new canvas size
- **AND** mask overlay SHALL be redrawn at the new scale
- **AND** image SHALL maintain aspect ratio (no stretching)
- **AND** coordinate transformations SHALL remain accurate

---

## MODIFIED Requirements

### Requirement: SAM2 Service Integration

The system SHALL integrate with SAM2 (Segment Anything Model 2) Docker service to provide automatic image segmentation capabilities for both medical and general-purpose images.

**Changes from image-segmentation spec**: Added support for non-medical image types via `imageType: "demo"` parameter.

#### Scenario: SAM2 Docker service is available
- **WHEN** the backend starts
- **THEN** it SHALL verify SAM2 Docker container is running and accessible
- **AND** log connection status and service health

#### Scenario: Demo image type support (NEW)
- **WHEN** backend receives segmentation request with `imageType: "demo"`
- **THEN** the system SHALL process the image as a general-purpose image (not DICOM)
- **AND** skip medical-specific preprocessing (windowing, HU conversion)
- **AND** apply SAM2 model directly to RGB/grayscale image data
- **AND** return segmentation result in the same format as medical images

#### Scenario: SAM2 service unavailable
- **WHEN** SAM2 Docker container is not running or unreachable
- **THEN** the commercial demo SHALL display a warning message
- **AND** gracefully disable segmentation features
- **AND** NOT block other demo functionality (manual annotation remains available)

---

## REMOVED Requirements

None. This spec extends existing SAM2 capabilities for demo purposes without removing any existing functionality.
