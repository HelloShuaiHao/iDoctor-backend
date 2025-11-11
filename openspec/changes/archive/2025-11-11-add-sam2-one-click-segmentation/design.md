## Context

The current IDoctor system provides manual annotation tools for medical image segmentation (L3 spine and muscle annotation via L3MaskEditor and MiddleMaskEditor). Users must manually draw or trace anatomical regions, which is time-consuming and requires medical expertise.

SAM2 (Segment Anything Model 2) is a state-of-the-art computer vision model capable of automatic segmentation. Integrating SAM2 as a one-click option will:
- **Accelerate workflow**: Reduce annotation time from minutes to seconds
- **Maintain quality**: Users can manually correct SAM2 results using existing tools
- **Preserve flexibility**: Existing manual annotation remains available

### Constraints
- Must not disrupt existing manual annotation workflows
- SAM2 service should be optional (system continues if SAM2 is unavailable)
- Integration should work with existing DICOM processing pipeline
- Must support both L3 and muscle annotation contexts

### Stakeholders
- **Medical professionals**: Primary users who annotate images
- **Backend developers**: Integrate SAM2 Docker service
- **Frontend developers**: Add UI controls and result handling
- **DevOps**: Deploy and monitor SAM2 container

## Goals / Non-Goals

### Goals
- Deploy SAM2 as a containerized microservice accessible to backend
- Add "One-Click Segmentation" button in mask editors
- Allow users to manually refine SAM2 results
- Cache segmentation results to avoid redundant processing
- Gracefully handle SAM2 service failures

### Non-Goals
- Replacing existing nnUNet-based segmentation pipeline (L3 spine detection, muscle segmentation)
- Training or fine-tuning SAM2 models (use pre-trained models)
- Real-time segmentation during DICOM upload (triggered manually by user)
- Multi-slice batch segmentation in single request (process one slice at a time)

## Decisions

### Decision 1: SAM2 as Docker Microservice

**What**: Deploy SAM2 as a separate Docker container rather than integrating directly into app.py

**Why**:
- **Isolation**: Model inference is resource-intensive; isolating in a container prevents impacting main app performance
- **Scalability**: Can horizontally scale SAM2 service independently
- **Flexibility**: Easy to swap SAM2 versions or replace with alternative models
- **Resource management**: Dedicated GPU allocation for SAM2 without affecting other services

**Alternatives considered**:
- **In-process integration**: Import SAM2 directly in app.py
  - Rejected: Would bloat main application memory footprint and complicate dependency management
- **External API service**: Use third-party SAM2 API
  - Rejected: Data privacy concerns (medical images) and network latency

### Decision 2: RESTful API Contract

**What**: SAM2 service exposes simple REST API with `/health` and `/segment` endpoints

**Why**:
- **Simplicity**: Standard HTTP makes integration straightforward
- **Language-agnostic**: Backend (Python FastAPI) can easily call SAM2 service
- **Tooling**: Standard HTTP clients, logging, and monitoring work out-of-box

**Alternatives considered**:
- **gRPC**: Higher performance but adds complexity
- **Message queue (RabbitMQ/Kafka)**: Overkill for synchronous request-response pattern

### Decision 3: Manual Button Trigger (Not Automatic)

**What**: Users must click "One-Click Segmentation" button; automatic segmentation is not triggered on image load

**Why**:
- **User control**: Medical professionals should decide when to use AI assistance vs manual annotation
- **Cost efficiency**: Avoid unnecessary SAM2 invocations for users who prefer manual workflow
- **Error handling**: Easier for users to understand failures when explicitly triggered

**Alternatives considered**:
- **Auto-trigger on load**: Rejected per user requirement for manual control

### Decision 4: Client-Side Mask Editing Unchanged

**What**: SAM2 results are treated as standard mask overlays; all existing editing tools work on them

**Why**:
- **Code reuse**: No changes needed to existing brush/eraser/polygon tools
- **Consistency**: Users have familiar editing experience regardless of mask source
- **Simplicity**: Avoids creating special "AI-generated mask" data structure

### Decision 5: Cache with 24-Hour Expiration

**What**: Cache SAM2 results based on image hash with 24-hour TTL

**Why**:
- **Performance**: Avoid redundant segmentation for repeated requests (e.g., user retrying)
- **Cost reduction**: Minimize GPU compute usage
- **Freshness**: 24-hour expiration ensures stale results don't persist indefinitely

**Alternatives considered**:
- **No caching**: Simpler but wasteful for repeated requests
- **Permanent cache**: Risk of stale results if SAM2 model is updated

### Decision 6: Graceful Degradation When SAM2 Unavailable

**What**: If SAM2 service is down, the application continues functioning with manual annotation only

**Why**:
- **Reliability**: Core medical imaging workflow should not depend on optional AI service
- **Operational simplicity**: Avoid hard dependency that can cause cascading failures

**Implementation**:
- Health check on startup logs warning if SAM2 is unreachable
- Button is disabled with tooltip if SAM2 is unavailable
- No blocking errors or application crashes

## Risks / Trade-offs

### Risk 1: SAM2 Performance Bottleneck
- **Risk**: SAM2 inference may take longer than expected (>30s), causing user frustration
- **Mitigation**:
  - Set aggressive timeout (30s) and return error with retry option
  - Display progress indicator with expected time ("up to 30 seconds")
  - Consider GPU acceleration in production deployment
  - Monitor P95 latency and optimize if needed

### Risk 2: SAM2 Model Quality Issues
- **Risk**: SAM2 may produce poor segmentation for certain medical images (e.g., low contrast, artifacts)
- **Mitigation**:
  - Always allow manual correction after SAM2 segmentation
  - Provide "Discard and Start Over" option
  - Collect user feedback on SAM2 quality for future model fine-tuning
  - Display confidence score so users can judge quality

### Risk 3: Docker Container Resource Contention
- **Risk**: SAM2 container may consume excessive memory/GPU, impacting other services
- **Mitigation**:
  - Set explicit memory limits (4GB+) in docker-compose
  - Use separate GPU if available (via device reservation)
  - Monitor container resource usage with Prometheus/Grafana
  - Implement rate limiting if needed (max N concurrent requests)

### Trade-off 1: Synchronous vs Asynchronous Processing
- **Decision**: Use synchronous API (frontend waits for result)
- **Trade-off**:
  - ✅ Simpler implementation (no background jobs, polling, or webhooks)
  - ✅ Immediate user feedback
  - ❌ Frontend must handle 30s timeout (but acceptable per requirements)
  - ❌ No ability to queue multiple requests (acceptable for one-at-a-time workflow)

### Trade-off 2: Single-Slice vs Batch Processing
- **Decision**: Process one slice at a time
- **Trade-off**:
  - ✅ Faster feedback (user sees result for current slice immediately)
  - ✅ Simpler error handling (no partial batch failures)
  - ❌ Cannot leverage batch processing efficiency (acceptable given user-triggered workflow)

## Migration Plan

### Phase 1: Infrastructure Setup (Week 1)
1. Create SAM2 Dockerfile with model dependencies
2. Add SAM2 service to docker-compose.yml
3. Deploy to staging environment
4. Verify health check and basic connectivity

### Phase 2: Backend Integration (Week 2)
1. Implement `sam2_client.py` and API endpoint
2. Add caching layer
3. Implement error handling and graceful degradation
4. Integration tests

### Phase 3: Frontend Integration (Week 2-3)
1. Add "One-Click Segmentation" buttons to both mask editors
2. Implement loading states and error feedback
3. Verify manual editing works on SAM2 results
4. User acceptance testing

### Phase 4: Production Deployment (Week 4)
1. Deploy to production with monitoring
2. Gradual rollout (enable for subset of users)
3. Collect feedback and iterate
4. Full rollout after stability confirmed

### Rollback Plan
- If SAM2 causes issues, disable via feature flag (set `SAM2_ENABLED=false` in .env)
- Frontend buttons will be hidden/disabled automatically
- No data loss risk (manual annotation remains functional)

## Open Questions

1. **SAM2 Docker Image Source**: Will we build the SAM2 Docker image ourselves, or is there an official image to pull?
   - **Action**: Confirm with team; document in README if custom build required

2. **GPU Availability**: Do we have GPU-enabled Docker hosts in production?
   - **Action**: If yes, configure GPU passthrough; if no, use CPU inference (slower but functional)

3. **Model Checkpoint Location**: Where are SAM2 model weights stored (cloud storage, local volume)?
   - **Action**: Document in deployment guide; consider using persistent volume

4. **Monitoring and Alerts**: What metrics should trigger alerts (SAM2 down, high latency, high error rate)?
   - **Action**: Define SLOs (e.g., 95% requests < 30s, 99% uptime)

5. **User Training**: Do medical professionals need training on when to use SAM2 vs manual annotation?
   - **Action**: Create user guide with best practices and example cases
