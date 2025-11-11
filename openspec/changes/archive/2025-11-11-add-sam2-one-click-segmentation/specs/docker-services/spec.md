## ADDED Requirements

### Requirement: SAM2 Docker Container Configuration

The system SHALL deploy SAM2 as a containerized microservice orchestrated via Docker Compose.

#### Scenario: SAM2 service definition in docker-compose
- **WHEN** docker-compose.yml is deployed
- **THEN** it SHALL include a service named `sam2_service`
- **AND** specify the SAM2 Docker image (name and tag)
- **AND** expose a REST API port (default: 8000)
- **AND** configure health check endpoint `/health`

#### Scenario: Container resource limits
- **WHEN** SAM2 container is started
- **THEN** it SHALL have memory limit of at least 4GB
- **AND** have CPU allocation appropriate for model inference (recommend 2+ cores)
- **AND** have GPU access if available (optional, via `deploy.resources.reservations.devices`)

#### Scenario: Container restart policy
- **WHEN** SAM2 container crashes or exits unexpectedly
- **THEN** Docker SHALL automatically restart it (restart: always)
- **AND** log the restart event for monitoring

### Requirement: SAM2 API Specification

The SAM2 Docker service SHALL expose a REST API with standardized endpoints for segmentation.

#### Scenario: Health check endpoint
- **WHEN** `/health` endpoint is called
- **THEN** it SHALL return HTTP 200 with JSON body: `{"status": "healthy", "model_loaded": true}`
- **AND** respond within 2 seconds

#### Scenario: Segmentation endpoint contract
- **WHEN** POST request is sent to `/segment` endpoint
- **THEN** it SHALL accept multipart/form-data with image file
- **AND** accept optional JSON parameters: `{"mode": "auto", "return_format": "png"}`
- **AND** return HTTP 200 with segmentation mask on success
- **AND** return HTTP 4xx/5xx with error details on failure

#### Scenario: Timeout handling
- **WHEN** segmentation takes longer than 25 seconds
- **THEN** SAM2 service SHALL return HTTP 504 Gateway Timeout
- **AND** include partial results if available (optional)

### Requirement: Network Configuration

SAM2 service SHALL be accessible to the main backend service via Docker internal network.

#### Scenario: Service discovery
- **WHEN** backend service (app.py) needs to communicate with SAM2
- **THEN** it SHALL use hostname `sam2_service` (Docker Compose service name)
- **AND** connect on configured port (default: 8000)
- **AND** use URL pattern: `http://sam2_service:8000/segment`

#### Scenario: Network isolation
- **WHEN** SAM2 container is running
- **THEN** it SHALL NOT be directly accessible from external networks
- **AND** only backend service SHALL have network access to SAM2
- **AND** nginx reverse proxy SHALL NOT expose SAM2 endpoints publicly

### Requirement: Environment Configuration

SAM2 service SHALL be configurable via environment variables for flexibility.

#### Scenario: Model configuration
- **WHEN** SAM2 container starts
- **THEN** it SHALL read environment variables:
  - `SAM2_MODEL_PATH`: Path to model checkpoint file
  - `SAM2_DEVICE`: "cuda" or "cpu" for inference device
  - `SAM2_BATCH_SIZE`: Integer for batch processing (default: 1)
  - `SAM2_CONFIDENCE_THRESHOLD`: Float between 0.0-1.0 (default: 0.5)

#### Scenario: Logging configuration
- **WHEN** SAM2 processes a request
- **THEN** it SHALL log to stdout/stderr with structured format (JSON recommended)
- **AND** include request_id, processing_time, and result status
- **AND** logs SHALL be captured by Docker logging driver

### Requirement: Volume Mounts and Persistence

SAM2 service SHALL use volume mounts for model weights and temporary storage.

#### Scenario: Model weights persistence
- **WHEN** SAM2 container is deployed
- **THEN** model checkpoint files SHALL be stored in a Docker volume
- **AND** volume SHALL be mounted to `/app/models` inside container
- **AND** container SHALL NOT need to download models on every restart

#### Scenario: Temporary image storage
- **WHEN** SAM2 receives image for processing
- **THEN** it MAY use a temporary volume `/tmp/sam2_cache` for intermediate files
- **AND** clean up temporary files after processing completes
- **AND** implement cache eviction policy if disk usage exceeds 10GB

### Requirement: Integration Testing

The system SHALL provide scripts to verify SAM2 Docker service integration.

#### Scenario: Service health verification
- **WHEN** deployment completes
- **THEN** a test script SHALL check SAM2 `/health` endpoint returns 200
- **AND** verify backend can successfully reach SAM2 service
- **AND** report any connectivity or configuration issues

#### Scenario: End-to-end segmentation test
- **WHEN** running integration tests
- **THEN** send a sample test image to SAM2 via backend API
- **AND** verify returned mask is valid PNG format
- **AND** verify processing completes within expected time limits
