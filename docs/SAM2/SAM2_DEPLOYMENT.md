# SAM2 One-Click Segmentation Deployment Guide

## Quick Start

The SAM2 service has been configured to work in **mock mode** by default, so you can test the integration immediately without downloading the actual model.

### 1. Build and Start Services

```bash
cd commercial/docker
docker-compose build sam2_service
docker-compose up -d sam2_service
```

### 2. Verify Service is Running

```bash
# Check service health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","model_loaded":false,"service":"sam2_segmentation","version":"1.0.0"}
```

### 3. Test from Backend

```bash
# Check SAM2 availability from backend
curl http://localhost:4200/api/segmentation/sam2/health

# Expected response:
# {"enabled":true,"available":true,"cache_stats":{...}}
```

### 4. Test from Frontend

1. Upload DICOM files
2. Open L3MaskEditor or MiddleMaskEditor
3. Click the **"AI一键分割"** (AI One-Click Segmentation) button
4. In mock mode, you'll see a simple threshold-based segmentation

## Production Deployment (with Real SAM2 Model)

### Step 1: Download SAM2 Model

```bash
# Create model directory
mkdir -p ~/sam2_models

# Download SAM2 checkpoint (example - use official link)
# Replace with actual SAM2 model download URL
wget https://example.com/sam2_hiera_large.pt -O ~/sam2_models/sam2_hiera_large.pt
```

### Step 2: Copy Model to Docker Volume

```bash
# Find the Docker volume
docker volume inspect commercial_docker_sam2_models

# Copy model to volume (adjust path based on volume inspect output)
docker run --rm -v commercial_docker_sam2_models:/app/models \
  -v ~/sam2_models:/source alpine \
  cp /source/sam2_hiera_large.pt /app/models/
```

### Step 3: Restart SAM2 Service

```bash
docker-compose restart sam2_service

# Check logs
docker-compose logs -f sam2_service
```

### Step 4: Verify Model Loaded

```bash
curl http://localhost:8000/health

# Expected response with model loaded:
# {"status":"healthy","model_loaded":true,"service":"sam2_segmentation","version":"1.0.0"}
```

## Configuration

### Environment Variables

Edit `commercial/docker/.env.prod` or `commercial/.env`:

```bash
# SAM2 Model Configuration
SAM2_MODEL_PATH=/app/models/sam2_hiera_large.pt
SAM2_DEVICE=cpu  # or 'cuda' if GPU available
SAM2_BATCH_SIZE=1
SAM2_CONFIDENCE_THRESHOLD=0.5
SAM2_ENABLED=true

# Backend Configuration
SAM2_SERVICE_URL=http://sam2_service:8000  # Docker environment
# SAM2_SERVICE_URL=http://localhost:8000  # Local development
SAM2_REQUEST_TIMEOUT=30
SAM2_CACHE_EXPIRE_HOURS=24
```

## Troubleshooting

### Issue: Docker Build Fails on ARM (Apple Silicon)

**Solution**: The Dockerfile has been updated to handle ARM architecture. If you still have issues:

```bash
# Build with platform specification
docker-compose build --platform linux/amd64 sam2_service
```

### Issue: SAM2 Service Keeps Restarting

**Check logs**:
```bash
docker-compose logs sam2_service
```

**Common causes**:
- Missing dependencies → Should work in mock mode
- Out of memory → Increase Docker memory limit
- Port conflict → Check if port 8000 is available

### Issue: "SAM2 service is unavailable" Error

**Solutions**:
1. Check SAM2 service is running:
   ```bash
   docker ps | grep sam2
   ```

2. Check health endpoint:
   ```bash
   curl http://sam2_service:8000/health  # from within Docker network
   curl http://localhost:8000/health     # from host
   ```

3. Check backend can reach SAM2:
   ```bash
   docker-compose exec auth_service curl http://sam2_service:8000/health
   ```

### Issue: Segmentation is Slow

**Optimizations**:
1. Enable GPU (if available):
   ```yaml
   # In docker-compose.yml
   sam2_service:
     deploy:
       resources:
         reservations:
           devices:
             - driver: nvidia
               count: 1
               capabilities: [gpu]
   ```

2. Adjust timeout:
   ```bash
   SAM2_REQUEST_TIMEOUT=60  # Increase to 60 seconds
   ```

3. Check cache is working:
   ```bash
   curl http://localhost:4200/api/segmentation/sam2/health
   # Check cache_stats.cache_size
   ```

## Mock Mode vs Production Mode

### Mock Mode (Default)
- ✅ No model download required
- ✅ Fast startup
- ✅ Good for testing integration
- ❌ Simple threshold-based segmentation (not accurate)

### Production Mode (with SAM2 Model)
- ✅ State-of-the-art segmentation quality
- ✅ Works on complex medical images
- ✅ High confidence scores
- ⚠️  Requires model download (~2GB)
- ⚠️  Slower inference (5-30 seconds per image)

## Next Steps

1. **Test Integration**: Use mock mode to verify the UI and API work correctly
2. **Download Model**: Get the official SAM2 checkpoint for production
3. **Benchmark Performance**: Test segmentation speed on your hardware
4. **User Training**: Train medical staff on when to use AI vs manual annotation
5. **Monitor**: Set up alerts for SAM2 service health

## Resources

- SAM2 Official Repository: https://github.com/facebookresearch/segment-anything-2
- SAM2 Model Checkpoints: Check the official repo for download links
- API Documentation: See `app.py` line 884 for endpoint details

## Support

If you encounter issues:
1. Check logs: `docker-compose logs sam2_service`
2. Check health: `curl http://localhost:8000/health`
3. Review `openspec/changes/add-sam2-one-click-segmentation/tasks.md`
4. The service will gracefully degrade if SAM2 is unavailable
