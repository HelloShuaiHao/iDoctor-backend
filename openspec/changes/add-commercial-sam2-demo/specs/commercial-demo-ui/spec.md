# commercial-demo-ui Specification Delta

## Purpose

Defines the user interface requirements for the Commercial SAM2 Interactive Demo feature, including dashboard integration, modal components, and visual design standards.

## ADDED Requirements

### Requirement: Dashboard Demo Card Entry Point

The commercial frontend dashboard SHALL provide a prominent entry point to access the SAM2 interactive demo feature.

#### Scenario: Card displayed on dashboard
- **WHEN** authenticated user navigates to `/dashboard`
- **THEN** a "AI Image Segmentation Demo" card SHALL be displayed in the quick actions grid
- **AND** the card SHALL have a modern design with rounded corners (`border-radius ≥ 12px`)
- **AND** the card SHALL display a descriptive icon (magic wand or AI chip)
- **AND** the card SHALL include call-to-action text: "Try AI Segmentation"

#### Scenario: Card click interaction
- **WHEN** user clicks the demo card
- **THEN** a full-screen modal SHALL open containing the ImageSegmentationDemo component
- **AND** the modal SHALL have a close button in the top-right corner
- **AND** clicking outside the modal content SHALL NOT close the modal (prevent accidental closure)
- **AND** pressing Escape key SHALL close the modal

#### Scenario: Card visual design compliance
- **WHEN** dashboard is rendered
- **THEN** the demo card SHALL match the existing card design system (shadcn/ui)
- **AND** have a 2px solid border (`border-2 border-gray-200`)
- **AND** apply hover effects (scale and shadow increase)
- **AND** use consistent spacing with other dashboard cards

---

### Requirement: Image Upload Interface

The demo SHALL provide an intuitive image upload interface for PNG and JPG files.

#### Scenario: Upload zone display
- **WHEN** demo modal opens without an uploaded image
- **THEN** a drag-and-drop upload zone SHALL be displayed as the primary UI element
- **AND** the zone SHALL show instructional text: "Drag & drop an image here, or click to browse"
- **AND** the zone SHALL have a dashed border and hover state indicating interactivity
- **AND** supported formats SHALL be listed: "Supports: PNG, JPG, JPEG (max 10MB)"

#### Scenario: Valid image upload
- **WHEN** user drops or selects a PNG or JPG file under 10MB
- **THEN** the image SHALL be loaded and displayed on a canvas element
- **AND** the upload zone SHALL be hidden
- **AND** the interactive canvas SHALL become active
- **AND** click mode instructions SHALL be displayed

#### Scenario: Invalid file format
- **WHEN** user uploads a file with unsupported format (e.g., GIF, BMP, PDF)
- **THEN** an error toast SHALL be displayed: "Unsupported format. Please upload PNG or JPG."
- **AND** the upload zone SHALL remain visible
- **AND** the invalid file SHALL NOT be loaded

#### Scenario: File size exceeded
- **WHEN** user uploads a file larger than 10MB
- **THEN** an error toast SHALL be displayed: "File too large. Maximum size: 10MB"
- **AND** the upload zone SHALL remain visible

#### Scenario: Image dimension handling
- **WHEN** uploaded image exceeds 2048x2048 pixels
- **THEN** the image SHALL be automatically resized client-side to fit within 2048x2048
- **AND** aspect ratio SHALL be preserved
- **AND** a notification SHALL inform user: "Image resized to 2048x2048 for optimal processing"

---

### Requirement: SAM2 Interactive Canvas

The canvas component SHALL support interactive click-based segmentation with visual feedback.

#### Scenario: Canvas rendering
- **WHEN** image is successfully uploaded
- **THEN** the image SHALL be rendered on an HTML5 canvas element
- **AND** the canvas SHALL have a dark background (`bg-black`)
- **AND** the canvas SHALL be bordered with rounded corners (`border-2 border-gray-300 rounded-lg`)
- **AND** the canvas SHALL scale to fit the modal width while maintaining aspect ratio

#### Scenario: Foreground point click
- **WHEN** user left-clicks on the canvas
- **THEN** a green circle marker SHALL be drawn at the clicked position
- **AND** the marker SHALL have a visible border (outer: dark green, inner: light green)
- **AND** the click point coordinates SHALL be added to state with `label: 1` (foreground)
- **AND** a counter SHALL update showing total click points

#### Scenario: Background point click
- **WHEN** user right-clicks on the canvas
- **THEN** a red circle marker SHALL be drawn at the clicked position
- **AND** the marker SHALL have a visible border (outer: dark red, inner: light red)
- **AND** the click point coordinates SHALL be added to state with `label: 0` (background)
- **AND** the default browser context menu SHALL be prevented
- **AND** instructional text SHALL remind: "Left-click: foreground | Right-click: background"

#### Scenario: Point removal
- **WHEN** user clicks "Clear Points" button
- **THEN** all click point markers SHALL be removed from canvas
- **AND** the click points state SHALL be reset to empty array
- **AND** any existing segmentation mask SHALL remain visible

#### Scenario: Segmentation mask display
- **WHEN** SAM2 API returns a segmentation mask (base64 PNG)
- **THEN** the mask SHALL be decoded and rendered as a semi-transparent overlay on the canvas
- **AND** the mask opacity SHALL be 40% (`opacity: 0.4`)
- **AND** the mask color SHALL be green (`color: #22c55e`) for highlighted regions
- **AND** the mask SHALL align pixel-perfectly with the original image

#### Scenario: Canvas disabled state
- **WHEN** segmentation is in progress (`isSegmenting: true`)
- **THEN** the canvas SHALL show a loading spinner overlay
- **AND** click interactions SHALL be disabled
- **AND** cursor SHALL change to "not-allowed"
- **AND** instructional text SHALL show: "Processing..."

---

### Requirement: Label Management UI

The demo SHALL provide an interface for adding and managing text labels for segmented regions.

#### Scenario: Label input panel display
- **WHEN** segmentation completes successfully
- **THEN** a label input panel SHALL appear in the right sidebar
- **AND** the panel SHALL contain a text input field with placeholder: "Enter label (e.g., 'kidney')"
- **AND** an "Add Label" primary button SHALL be displayed
- **AND** a "Get AI Suggestions" secondary button SHALL be displayed with a sparkle icon

#### Scenario: Manual label addition
- **WHEN** user types a label text and clicks "Add Label"
- **THEN** the label SHALL be added to the labels list with a unique ID
- **AND** the label SHALL appear on the canvas with a leader line connecting to the segmentation region
- **AND** the text input SHALL be cleared for next label
- **AND** the label SHALL have a white background with border and shadow

#### Scenario: Label validation
- **WHEN** user attempts to add an empty label
- **THEN** the "Add Label" button SHALL be disabled
- **AND** no action SHALL occur on click

#### Scenario: Label character limit
- **WHEN** user types more than 50 characters in the label input
- **THEN** the input SHALL prevent further typing
- **AND** a character counter SHALL display: "X/50"
- **AND** the counter SHALL turn red when approaching limit (≥ 45 characters)

#### Scenario: Label positioning
- **WHEN** a label is added
- **THEN** the label text SHALL be positioned outside the image bounds (to avoid obscuring content)
- **AND** a dashed leader line SHALL connect the label to the center of the segmentation bounding box
- **AND** the label SHALL be draggable to a new position
- **AND** the leader line SHALL update dynamically during drag

#### Scenario: Label deletion
- **WHEN** user clicks the "X" button on a label chip
- **THEN** the label SHALL be removed from the canvas
- **AND** the leader line SHALL be removed
- **AND** the label SHALL be removed from the labels list

---

### Requirement: Leader Line Label Rendering

Labels SHALL be rendered with visual leader lines connecting text to segmented regions.

#### Scenario: Leader line drawing
- **WHEN** a label is added to a segmented region
- **THEN** an SVG line element SHALL be rendered from the segmentation bounding box center to the label position
- **AND** the line SHALL be styled as dashed (`stroke-dasharray: 4 4`)
- **AND** the line width SHALL be 2px
- **AND** the line color SHALL be `#6b7280` (gray-500)

#### Scenario: Label anchor point
- **WHEN** leader line reaches the label position
- **THEN** a small circular anchor point SHALL be rendered
- **AND** the anchor SHALL have a 4px radius
- **AND** the anchor color SHALL match the primary color (`#3b82f6`)

#### Scenario: Label text box styling
- **WHEN** label text is rendered
- **THEN** the text SHALL have a white background (`bg-white`)
- **AND** a subtle border (`border border-gray-300`)
- **AND** rounded corners (`rounded-md`, 6px)
- **AND** padding (`px-3 py-2`)
- **AND** a small shadow (`shadow-sm`)
- **AND** font SHALL be medium weight (`font-medium text-sm`)

#### Scenario: Label hover state
- **WHEN** user hovers over a label
- **THEN** the label background SHALL change to light blue (`bg-blue-50`)
- **AND** the leader line SHALL become thicker (3px)
- **AND** the leader line color SHALL change to primary (`#3b82f6`)
- **AND** cursor SHALL change to "move" to indicate draggability

#### Scenario: Multiple labels rendering
- **WHEN** multiple labels are added to the same segmentation
- **THEN** labels SHALL be positioned to avoid overlapping
- **AND** leader lines SHALL NOT intersect if possible (use basic collision avoidance)
- **AND** each label SHALL maintain its individual styling and interactivity

---

### Requirement: Results and Export Panel

The demo SHALL provide a results panel with statistics and export functionality.

#### Scenario: Results panel display
- **WHEN** segmentation completes
- **THEN** a results panel SHALL appear in the right sidebar below the label input
- **AND** the panel SHALL display segmentation statistics:
  - Confidence score (as percentage)
  - Processing time (in milliseconds)
  - Number of labels added
- **AND** the panel SHALL have rounded corners and border consistent with design system

#### Scenario: Export functionality
- **WHEN** user clicks the "Export Result" button
- **THEN** a composite image SHALL be generated combining:
  - Original image
  - Segmentation mask overlay
  - All labels with leader lines
- **AND** the composite SHALL be converted to PNG format
- **AND** a browser download SHALL be triggered with filename: `segmentation_result_<timestamp>.png`
- **AND** a success toast SHALL display: "Export successful!"

#### Scenario: Clear all functionality
- **WHEN** user clicks the "Start Over" button
- **THEN** a confirmation dialog SHALL appear: "Clear all progress and start over?"
- **AND** if confirmed:
  - All click points SHALL be removed
  - Segmentation mask SHALL be cleared
  - All labels SHALL be removed
  - The upload zone SHALL reappear
- **AND** if cancelled, no action SHALL occur

---

### Requirement: Responsive Layout Design

The demo interface SHALL adapt to different screen sizes while maintaining usability.

#### Scenario: Desktop layout (≥ 1024px)
- **WHEN** modal is displayed on desktop viewport
- **THEN** layout SHALL use a 3-column grid:
  - Left sidebar: Instructions and controls (20% width)
  - Center: Canvas (60% width)
  - Right sidebar: Label input and results (20% width)
- **AND** all panels SHALL be visible simultaneously

#### Scenario: Tablet layout (768px - 1023px)
- **WHEN** modal is displayed on tablet viewport
- **THEN** layout SHALL use a 2-column grid:
  - Left: Canvas (70% width)
  - Right: Stacked controls, label input, and results (30% width)
- **AND** scrolling SHALL be enabled for the right sidebar if content overflows

#### Scenario: Mobile layout (< 768px)
- **WHEN** modal is displayed on mobile viewport
- **THEN** layout SHALL stack vertically:
  - Top: Canvas (full width, max height 400px)
  - Middle: Controls (full width)
  - Bottom: Label input and results (full width)
- **AND** modal SHALL be full-screen
- **AND** scrolling SHALL be enabled for entire modal content

---

### Requirement: Visual Design Consistency

All UI components SHALL adhere to the commercial frontend design system.

#### Scenario: Color palette compliance
- **WHEN** any demo component is rendered
- **THEN** colors SHALL match the defined palette:
  - Primary: `#3b82f6` (blue-500)
  - Success: `#22c55e` (green-500)
  - Error: `#ef4444` (red-500)
  - Background: `#ffffff`
  - Border: `#e5e7eb` (gray-200)
  - Text: `#1f2937` (gray-800)

#### Scenario: Border radius standards
- **WHEN** bordered elements are rendered
- **THEN** border radius SHALL be:
  - Cards and containers: `rounded-xl` (12px)
  - Inputs and buttons: `rounded-lg` (8px)
  - Small elements (chips, badges): `rounded-md` (6px)

#### Scenario: Shadow application
- **WHEN** elevated elements are rendered
- **THEN** shadows SHALL be applied as:
  - Cards: `shadow-lg` with `hover:shadow-xl`
  - Inputs: `shadow-sm`
  - Modals: `shadow-2xl`

#### Scenario: Typography standards
- **WHEN** text content is rendered
- **THEN** typography SHALL follow:
  - Headings: `font-semibold text-xl`
  - Body text: `text-base text-gray-700`
  - Labels: `text-sm font-medium text-gray-600`
  - Buttons: `font-medium text-sm`

---

### Requirement: Loading and Error States

The demo SHALL provide clear feedback for loading and error conditions.

#### Scenario: Initial loading state
- **WHEN** demo modal first opens
- **THEN** a brief skeleton loader SHALL be displayed while components initialize
- **AND** the skeleton SHALL match the expected layout structure

#### Scenario: Segmentation loading state
- **WHEN** segmentation request is sent to SAM2 API
- **THEN** a loading spinner SHALL overlay the canvas
- **AND** progress text SHALL display: "AI is analyzing your image..."
- **AND** estimated time SHALL be shown: "This usually takes 3-5 seconds"
- **AND** all interactive buttons SHALL be disabled

#### Scenario: Segmentation success
- **WHEN** segmentation completes successfully
- **THEN** the loading overlay SHALL fade out smoothly (300ms transition)
- **AND** the mask SHALL fade in smoothly
- **AND** a success toast SHALL display: "Segmentation complete! Add labels below."

#### Scenario: Segmentation failure
- **WHEN** SAM2 API returns an error or times out (> 30 seconds)
- **THEN** the loading overlay SHALL be hidden
- **AND** an error toast SHALL display: "Segmentation failed. Please try again or choose a different image."
- **AND** a "Retry" button SHALL appear
- **AND** click points SHALL remain visible for retry

#### Scenario: Network error handling
- **WHEN** network request fails (no internet, API unavailable)
- **THEN** an error banner SHALL display at top of modal:
  - Message: "Unable to connect to AI service. Please check your connection."
  - Retry button
  - Dismiss button
- **AND** the error SHALL NOT close the modal automatically

---

### Requirement: Accessibility Compliance

The demo interface SHALL meet WCAG 2.1 AA accessibility standards.

#### Scenario: Keyboard navigation
- **WHEN** user navigates using keyboard only
- **THEN** all interactive elements SHALL be focusable via Tab key
- **AND** focus indicators SHALL be visible (blue outline)
- **AND** tab order SHALL follow logical reading flow
- **AND** Enter key SHALL activate focused buttons
- **AND** Escape key SHALL close the modal

#### Scenario: Screen reader support
- **WHEN** screen reader is active
- **THEN** all images SHALL have descriptive `alt` text
- **AND** canvas SHALL have `role="img"` with `aria-label` describing content
- **AND** loading states SHALL announce via `aria-live="polite"`
- **AND** error messages SHALL announce via `aria-live="assertive"`
- **AND** button purposes SHALL be clear from text or `aria-label`

#### Scenario: Color contrast
- **WHEN** any text is rendered
- **THEN** contrast ratio SHALL meet WCAG AA standards (≥ 4.5:1 for normal text, ≥ 3:1 for large text)
- **AND** interactive elements SHALL have sufficient contrast against backgrounds
- **AND** disabled states SHALL be distinguishable without relying solely on color

#### Scenario: Focus management
- **WHEN** modal opens
- **THEN** focus SHALL move to the modal container
- **AND** focus SHALL be trapped within modal (Tab SHALL NOT reach elements behind modal)
- **WHEN** modal closes
- **THEN** focus SHALL return to the dashboard card that opened the modal
