## ADDED Requirements

### Requirement: One-Click Segmentation Button UI

The mask editor components (L3MaskEditor and MiddleMaskEditor) SHALL provide a user-accessible "One-Click Segmentation" button for triggering SAM2-based automatic annotation.

#### Scenario: Button visibility in L3MaskEditor
- **WHEN** user opens L3MaskEditor component
- **THEN** a prominent "One-Click Segmentation" button SHALL be displayed
- **AND** the button SHALL be visually distinct from manual drawing tools
- **AND** show icon indicating AI-assisted functionality

#### Scenario: Button visibility in MiddleMaskEditor
- **WHEN** user opens MiddleMaskEditor component for muscle annotation
- **THEN** a "One-Click Segmentation" button SHALL be displayed alongside existing tools
- **AND** preserve all existing manual annotation tools and workflows

#### Scenario: Button disabled state
- **WHEN** SAM2 service is unavailable or image is not loaded
- **THEN** the button SHALL be disabled with tooltip explaining the reason
- **AND** prevent user clicks until prerequisites are met

### Requirement: Segmentation Workflow Selection

Users SHALL be able to choose between manual annotation and SAM2-assisted segmentation without disrupting existing workflows.

#### Scenario: Default workflow unchanged
- **WHEN** user opens a mask editor without clicking SAM2 button
- **THEN** the existing manual annotation tools SHALL work exactly as before
- **AND** no automatic segmentation SHALL be triggered

#### Scenario: SAM2 workflow initiation
- **WHEN** user clicks "One-Click Segmentation" button
- **THEN** the system SHALL display loading indicator
- **AND** send current image to SAM2 API endpoint
- **AND** disable manual editing tools during processing

#### Scenario: Switching between workflows mid-session
- **WHEN** user has partially completed manual annotation and clicks SAM2 button
- **THEN** the system SHALL prompt for confirmation: "This will replace current annotations. Continue?"
- **AND** preserve existing annotations if user cancels
- **AND** replace with SAM2 result if user confirms

### Requirement: SAM2 Result Loading and Display

The mask editor SHALL load and overlay SAM2-generated segmentation masks on the image canvas for user review.

#### Scenario: Successful segmentation display
- **WHEN** SAM2 API returns a valid mask
- **THEN** the mask SHALL be overlaid on the image canvas with configurable opacity
- **AND** the loading indicator SHALL be hidden
- **AND** manual editing tools SHALL be re-enabled
- **AND** display success message: "Auto-segmentation complete. You can now refine the result."

#### Scenario: Segmentation failure handling
- **WHEN** SAM2 API returns an error or timeout
- **THEN** the system SHALL display error notification to the user
- **AND** keep existing annotations unchanged
- **AND** re-enable all manual editing tools
- **AND** log error details for debugging

### Requirement: Manual Correction After SAM2

Users SHALL be able to manually edit SAM2-generated masks using all existing annotation tools.

#### Scenario: Editing SAM2 result
- **WHEN** SAM2 segmentation is loaded and user selects a manual tool (brush, eraser, polygon)
- **THEN** the tool SHALL work on the SAM2-generated mask exactly as it does for manual masks
- **AND** preserve undo/redo functionality
- **AND** allow saving the corrected mask

#### Scenario: Discarding SAM2 result
- **WHEN** user is unsatisfied with SAM2 result and clicks "Clear Mask" button
- **THEN** the SAM2-generated mask SHALL be cleared
- **AND** user can restart with either manual annotation or retry SAM2 segmentation

### Requirement: Progress and Feedback Indicators

The system SHALL provide clear visual feedback during SAM2 segmentation processing.

#### Scenario: Processing state display
- **WHEN** SAM2 segmentation is in progress
- **THEN** display spinner/loading animation over the canvas
- **AND** show estimated processing time message: "Processing... This may take up to 30 seconds"
- **AND** disable the "One-Click Segmentation" button to prevent duplicate requests

#### Scenario: Processing completion notification
- **WHEN** segmentation completes (success or failure)
- **THEN** display toast notification with result status
- **AND** include confidence score in success notification if available
- **AND** provide actionable error message for failures (e.g., "Retry" button)
