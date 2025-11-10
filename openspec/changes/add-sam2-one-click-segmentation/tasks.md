## 1. Docker Infrastructure Setup

- [ ] 1.1 Create SAM2 Dockerfile with model dependencies (PyTorch, SAM2 library)
- [ ] 1.2 Add `sam2_service` configuration to docker-compose.yml with health check, resource limits, and volume mounts
- [ ] 1.3 Configure Docker volume for SAM2 model weights persistence
- [ ] 1.4 Set up environment variables (.env.example) for SAM2 configuration (MODEL_PATH, DEVICE, etc.)
- [ ] 1.5 Verify SAM2 container can start and health endpoint responds successfully

## 2. Backend SAM2 Integration

- [ ] 2.1 Create `sam2_client.py` module with SAM2 Docker service HTTP client
- [ ] 2.2 Implement connection pool and timeout configuration for SAM2 requests
- [ ] 2.3 Add startup health check in app.py to verify SAM2 availability
- [ ] 2.4 Implement graceful degradation when SAM2 is unavailable (log warning, continue without SAM2)
- [ ] 2.5 Add POST endpoint `/api/segmentation/sam2` in app.py
- [ ] 2.6 Implement request validation (image format, payload structure)
- [ ] 2.7 Implement response formatting (mask data, confidence score, processing time)
- [ ] 2.8 Add error handling for SAM2 failures (timeout, invalid response, service down)
- [ ] 2.9 Implement caching layer with Redis or in-memory cache (based on image hash)
- [ ] 2.10 Add cache expiration policy (24 hours)

## 3. Frontend UI Implementation

- [ ] 3.1 Add "One-Click Segmentation" button to L3MaskEditor.vue
- [ ] 3.2 Add "One-Click Segmentation" button to MiddleMaskEditor.vue
- [ ] 3.3 Implement button disabled/enabled state logic based on image load and SAM2 availability
- [ ] 3.4 Add loading spinner/overlay during SAM2 processing
- [ ] 3.5 Implement confirmation dialog for replacing existing manual annotations
- [ ] 3.6 Add toast notifications for success/failure feedback with confidence scores
- [ ] 3.7 Implement progress indicator with "Processing... up to 30s" message
- [ ] 3.8 Ensure SAM2 result masks are compatible with existing canvas rendering logic
- [ ] 3.9 Verify all manual editing tools (brush, eraser, polygon) work on SAM2-generated masks
- [ ] 3.10 Add "Retry Segmentation" button in error state

## 4. API Client Integration

- [ ] 4.1 Add `sam2Segment()` method to CTAI_web/src/api.js
- [ ] 4.2 Implement request payload formatting (image_data, image_type, patient_id, slice_index)
- [ ] 4.3 Implement response handling with error cases (timeout, 4xx, 5xx)
- [ ] 4.4 Add request timeout configuration (30 seconds)
- [ ] 4.5 Implement retry logic for transient failures (optional, 1 retry)

## 5. Testing and Validation

- [ ] 5.1 Write integration test script for SAM2 service health check
- [ ] 5.2 Create end-to-end test with sample DICOM image (upload → SAM2 segment → display)
- [ ] 5.3 Test error scenarios: SAM2 service down, invalid image, timeout
- [ ] 5.4 Test cache hit/miss scenarios
- [ ] 5.5 Test manual correction workflow after SAM2 segmentation
- [ ] 5.6 Test workflow switching: manual → SAM2 and SAM2 → manual
- [ ] 5.7 Verify graceful degradation when SAM2 is unavailable
- [ ] 5.8 Performance test: measure SAM2 segmentation latency under load
- [ ] 5.9 Test in both L3MaskEditor and MiddleMaskEditor contexts

## 6. Documentation and Deployment

- [ ] 6.1 Update README.md with SAM2 setup instructions (Docker image build/pull)
- [ ] 6.2 Document SAM2 environment variables and configuration options
- [ ] 6.3 Add deployment guide for starting SAM2 service with docker-compose
- [ ] 6.4 Create troubleshooting guide for common SAM2 issues (service not starting, GPU not detected, etc.)
- [ ] 6.5 Update API documentation with `/api/segmentation/sam2` endpoint details
- [ ] 6.6 Add user guide for "One-Click Segmentation" feature in frontend docs
- [ ] 6.7 Deploy to staging environment and verify end-to-end functionality
- [ ] 6.8 Conduct user acceptance testing with medical domain experts
- [ ] 6.9 Deploy to production with monitoring alerts for SAM2 service health
