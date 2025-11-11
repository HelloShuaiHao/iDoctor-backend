# image-segmentation Specification

## Purpose
TBD - created by archiving change add-sam2-one-click-segmentation. Update Purpose after archive.
## Requirements
### Requirement: SAM2 Service Integration

The system SHALL integrate with SAM2 (Segment Anything Model 2) Docker service to provide automatic image segmentation capabilities for medical images.

#### Scenario: SAM2 Docker service is available
- **WHEN** the backend starts
- **THEN** it SHALL verify SAM2 Docker container is running and accessible
- **AND** log connection status and service health

#### Scenario: SAM2 service unavailable
- **WHEN** SAM2 Docker container is not running or unreachable
- **THEN** the system SHALL gracefully degrade to manual-only annotation mode
- **AND** display warning message to administrators
- **AND** NOT block core application functionality

### Requirement: Automatic Segmentation API

The backend SHALL provide a REST API endpoint for invoking SAM2-based automatic segmentation.

#### Scenario: Successful segmentation request
- **WHEN** client sends POST request to `/api/segmentation/sam2` with valid image data
- **THEN** the system SHALL forward the image to SAM2 Docker service
- **AND** return the segmentation mask in PNG format
- **AND** respond within 30 seconds or return timeout error

#### Scenario: Invalid image format
- **WHEN** client sends unsupported image format (not PNG, JPEG, or DICOM)
- **THEN** the system SHALL return HTTP 400 with error message describing supported formats

#### Scenario: SAM2 processing failure
- **WHEN** SAM2 service returns an error during processing
- **THEN** the system SHALL return HTTP 503 with descriptive error message
- **AND** log the failure details for debugging

### Requirement: SAM2 Request/Response Format

The SAM2 segmentation API SHALL accept and return standardized data formats compatible with the frontend mask editors.

#### Scenario: Request payload structure
- **WHEN** frontend sends segmentation request
- **THEN** the payload SHALL include:
  - `image_data`: Base64-encoded image or file reference
  - `image_type`: "L3" or "middle" to indicate annotation context
  - `patient_id`: Identifier for tracking
  - `slice_index`: (optional) For multi-slice processing

#### Scenario: Response payload structure
- **WHEN** SAM2 completes segmentation successfully
- **THEN** the response SHALL include:
  - `mask_data`: Base64-encoded PNG mask or file URL
  - `confidence_score`: Float between 0.0 and 1.0
  - `processing_time_ms`: Milliseconds taken for segmentation
  - `bounding_box`: Optional object with {x, y, width, height}

### Requirement: Segmentation Result Caching

The system SHALL cache SAM2 segmentation results to avoid redundant processing of identical images.

#### Scenario: Cache hit on repeated request
- **WHEN** the same image is submitted for segmentation again (based on image hash)
- **THEN** the system SHALL return the cached mask result
- **AND** NOT invoke SAM2 Docker service
- **AND** include `cached: true` flag in response

#### Scenario: Cache expiration
- **WHEN** cached segmentation result is older than 24 hours
- **THEN** the system SHALL invalidate the cache entry
- **AND** reprocess the image with SAM2 on next request

