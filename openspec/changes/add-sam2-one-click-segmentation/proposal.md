## Why

The current system requires users to manually annotate muscle regions using L3MaskEditor and MiddleMaskEditor components, which is time-consuming and requires expertise. Integrating SAM2 (Segment Anything Model 2) as a Docker-based service will provide an AI-assisted "one-click segmentation" option that accelerates the annotation workflow while maintaining the ability for manual correction.

## What Changes

- **Backend API**: Add new endpoint `/api/segmentation/sam2` to invoke SAM2 Docker service for automatic segmentation
- **Docker Integration**: Configure SAM2 as a containerized microservice with API interface for DICOM/image segmentation
- **Frontend UI**: Add "One-Click Segmentation" button in L3MaskEditor and MiddleMaskEditor components
- **Segmentation Workflow**: Allow users to choose between manual annotation (existing) or SAM2-assisted segmentation (new)
- **Result Editing**: SAM2 segmentation results can be manually corrected using existing mask editor tools

This is a **non-breaking** additive change that preserves the current manual annotation workflow.

## Impact

### Affected Specs
- **image-segmentation** (new capability): SAM2-based automatic segmentation requirements
- **annotation-workflow** (new capability): User interaction flow for choosing segmentation methods
- **docker-services** (new capability): SAM2 container orchestration and API integration

### Affected Code
- **Backend**:
  - `app.py`: Add SAM2 API endpoint and Docker service integration
  - New file: `sam2_client.py` for SAM2 Docker communication
  - New file: `docker-compose.yml` updates for SAM2 service
- **Frontend**:
  - `CTAI_web/src/components/L3MaskEditor.vue`: Add one-click button UI
  - `CTAI_web/src/components/MiddleMaskEditor.vue`: Add one-click button UI
  - `CTAI_web/src/api.js`: Add SAM2 API client methods
- **Infrastructure**:
  - `commercial/docker/`: Add SAM2 Dockerfile and configuration
  - `commercial/nginx/`: Add proxy routes for SAM2 service

### Dependencies
- SAM2 Docker image (to be provided or built)
- Docker Compose for orchestration
- Network connectivity between app.py and SAM2 container
