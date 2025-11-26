"""
SAM2 Segmentation Service
Provides REST API for automatic image segmentation using SAM2 model.
"""

import os
import time
import logging
import json
from typing import Optional
from io import BytesIO
import base64

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np
from PIL import Image
import cv2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SAM2 Segmentation Service", version="1.0.0")

# Global variables for model
sam2_predictor = None
model_loaded = False

class SegmentationRequest(BaseModel):
    """Request model for segmentation"""
    image_type: str = "auto"  # "L3" or "middle" or "auto"
    return_format: str = "png"  # "png" or "base64"

class SegmentationResponse(BaseModel):
    """Response model for segmentation"""
    mask_data: str
    confidence_score: float
    processing_time_ms: int
    cached: bool = False
    bounding_box: Optional[dict] = None

def load_sam2_model():
    """Load SAM2 model on startup"""
    global sam2_predictor, model_loaded

    try:
        logger.info("Loading SAM2 model...")

        # Model path from environment variable
        model_path = os.getenv("SAM2_MODEL_PATH", "/app/models/sam2_hiera_large.pt")
        device = os.getenv("SAM2_DEVICE", "cpu")

        # Check if model file exists
        if not os.path.exists(model_path):
            logger.warning(f"Model file not found at {model_path}. Service will run in mock mode.")
            model_loaded = False
            return

        # Import SAM2 (delayed import to handle missing model gracefully)
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        # Build model
        # SAM2 needs config name and checkpoint path separately
        # For sam2.1_hiera_large, use config "sam2.1_hiera_l.yaml"
        model_cfg = "configs/sam2.1/sam2.1_hiera_l.yaml"  # Config file in SAM2 package
        sam2_model = build_sam2(model_cfg, ckpt_path=model_path, device=device)
        sam2_predictor = SAM2ImagePredictor(sam2_model)

        model_loaded = True
        logger.info(f"SAM2 model loaded successfully on {device}")

    except Exception as e:
        logger.error(f"Failed to load SAM2 model: {e}")
        logger.warning("Service will run in mock mode for development/testing")
        model_loaded = False

def detect_muscle_centroid(image_array: np.ndarray) -> tuple:
    """
    Detect muscle region centroid using simple image processing.
    Returns (x, y) coordinates of the detected centroid.
    """
    try:
        # Convert to grayscale
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_array

        # Apply Otsu thresholding to detect tissue
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            # Fallback to image center
            h, w = image_array.shape[:2]
            return (w // 2, h // 2)

        # Find largest contour (likely the main muscle group)
        largest_contour = max(contours, key=cv2.contourArea)

        # Calculate centroid
        M = cv2.moments(largest_contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            logger.info(f"Detected muscle centroid at ({cx}, {cy})")
            return (cx, cy)
        else:
            # Fallback to image center
            h, w = image_array.shape[:2]
            return (w // 2, h // 2)

    except Exception as e:
        logger.warning(f"Muscle detection failed: {e}, using image center")
        h, w = image_array.shape[:2]
        return (w // 2, h // 2)

def mock_segmentation(image_array: np.ndarray) -> np.ndarray:
    """
    Mock segmentation for development when model is not available.
    Creates a simple threshold-based mask.
    """
    logger.warning("Using mock segmentation (model not loaded)")

    # Convert to grayscale if needed
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_array

    # Simple Otsu thresholding as mock segmentation
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Apply morphological operations to clean up
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    return mask

def perform_sam2_segmentation(
    image_array: np.ndarray,
    click_points: list = None
) -> tuple[np.ndarray, float]:
    """
    Perform SAM2 segmentation on image.

    Args:
        image_array: Input image as numpy array (H, W, C)
        click_points: Optional list of click points [{"x": int, "y": int, "label": int}]
                     label: 1 = foreground, 0 = background
                     If None, uses image center as default

    Returns:
        (mask, confidence_score)
    """
    if not model_loaded or sam2_predictor is None:
        mask = mock_segmentation(image_array)
        return mask, 0.5  # Mock confidence

    try:
        import torch

        # Use no_grad context to prevent gradient computation and save memory
        with torch.no_grad():
            # Set image for SAM2
            sam2_predictor.set_image(image_array)

            # Prepare point prompts
            h, w = image_array.shape[:2]

            if click_points and len(click_points) > 0:
                # Use user-provided click points
                point_coords = np.array([[p["x"], p["y"]] for p in click_points])
                point_labels = np.array([p["label"] for p in click_points])
                logger.info(f"Using {len(click_points)} user-provided click points")
            else:
                # Smart automatic detection: find muscle centroid
                cx, cy = detect_muscle_centroid(image_array)
                point_coords = np.array([[cx, cy]])
                point_labels = np.array([1])  # Foreground point
                logger.info(f"Using smart muscle detection at ({cx}, {cy})")

            # Predict mask
            masks, scores, _ = sam2_predictor.predict(
                point_coords=point_coords,
                point_labels=point_labels,
                multimask_output=True
            )

            # Debug: log all candidate masks
            h, w = image_array.shape[:2]
            total_pixels = h * w
            logger.info(f"SAM2 returned {len(masks)} candidate masks:")
            for i, (mask, score) in enumerate(zip(masks, scores)):
                area_pct = (np.sum(mask) / total_pixels) * 100
                logger.info(f"  Mask {i}: score={score:.3f}, area={area_pct:.1f}%")

            # Select mask with highest score
            best_idx = np.argmax(scores)
            mask = masks[best_idx]
            confidence = float(scores[best_idx])

            area_pct = (np.sum(mask) / total_pixels) * 100
            logger.info(f"Selected mask {best_idx}: score={confidence:.3f}, area={area_pct:.1f}%")

            # Convert boolean mask to uint8
            mask_uint8 = (mask * 255).astype(np.uint8)

            logger.info(f"SAM2 segmentation completed with confidence: {confidence:.3f}")

        # CRITICAL: Reset predictor state to free GPU memory
        # This clears the cached image features and embeddings
        sam2_predictor.reset_state()

        # CRITICAL: Clear CUDA cache to free fragmented memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            # Log memory usage for debugging
            allocated = torch.cuda.memory_allocated() / 1024**2  # MB
            reserved = torch.cuda.memory_reserved() / 1024**2  # MB
            logger.debug(f"GPU Memory after cleanup: allocated={allocated:.1f}MB, reserved={reserved:.1f}MB")

        return mask_uint8, confidence

    except Exception as e:
        logger.error(f"SAM2 segmentation failed: {e}")
        # Ensure cleanup even on failure
        try:
            import torch
            if sam2_predictor is not None:
                sam2_predictor.reset_state()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
        # Fallback to mock
        mask = mock_segmentation(image_array)
        return mask, 0.3

def calculate_bounding_box(mask: np.ndarray) -> Optional[dict]:
    """Calculate bounding box from mask"""
    try:
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        return {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}

    except Exception as e:
        logger.error(f"Failed to calculate bounding box: {e}")
        return None

@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    # Configure PyTorch memory management to reduce fragmentation
    import os
    # Enable expandable segments to avoid fragmentation (as suggested by error message)
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    # Load the model
    load_sam2_model()

    # Log initial GPU memory state
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
            logger.info(f"Total GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    except:
        pass

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_info = {
        "status": "healthy",
        "model_loaded": model_loaded,
        "service": "sam2_segmentation",
        "version": "1.0.0"
    }

    # Add GPU memory info if available
    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3  # GB
            reserved = torch.cuda.memory_reserved() / 1024**3  # GB
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
            health_info["gpu_memory"] = {
                "allocated_gb": round(allocated, 2),
                "reserved_gb": round(reserved, 2),
                "total_gb": round(total, 2),
                "free_gb": round(total - allocated, 2)
            }
    except:
        pass

    return health_info

@app.post("/segment", response_model=SegmentationResponse)
async def segment_image(
    file: UploadFile = File(...),
    image_type: str = Form("auto"),
    return_format: str = Form("base64"),
    click_points: str = Form(None)
):
    """
    Segment an image using SAM2.

    Args:
        file: Image file (PNG, JPEG, or DICOM)
        image_type: Type hint for segmentation ("L3", "middle", or "auto")
        return_format: Response format ("png" or "base64")
        click_points: Optional JSON string of click points
                     e.g., '[{"x": 100, "y": 200, "label": 1}]'
                     label: 1 = foreground, 0 = background

    Returns:
        SegmentationResponse with mask data and metadata
    """
    start_time = time.time()

    try:
        # Read image file
        contents = await file.read()

        # Convert to PIL Image
        try:
            image = Image.open(BytesIO(contents))
            image_array = np.array(image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")

        # Ensure RGB format
        if len(image_array.shape) == 2:
            # Grayscale to RGB
            image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
        elif image_array.shape[2] == 4:
            # RGBA to RGB
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)

        # Parse click points if provided
        parsed_click_points = None
        if click_points:
            try:
                parsed_click_points = json.loads(click_points)
                logger.info(f"Parsed {len(parsed_click_points)} click points")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse click_points JSON: {e}")

        logger.info(f"Processing image: shape={image_array.shape}, type={image_type}")

        # Perform segmentation with optional click points
        mask, confidence = perform_sam2_segmentation(image_array, parsed_click_points)

        # Calculate bounding box
        bbox = calculate_bounding_box(mask)

        # Encode mask based on return format
        if return_format == "base64":
            # Convert mask to PNG and encode as base64
            _, buffer = cv2.imencode('.png', mask)
            mask_base64 = base64.b64encode(buffer).decode('utf-8')
            mask_data = mask_base64
        else:
            # Return as bytes (will be handled by FastAPI)
            mask_data = "binary"  # Placeholder

        processing_time = int((time.time() - start_time) * 1000)

        logger.info(f"Segmentation completed in {processing_time}ms")

        return SegmentationResponse(
            mask_data=mask_data,
            confidence_score=confidence,
            processing_time_ms=processing_time,
            cached=False,
            bounding_box=bbox
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Segmentation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SAM2 Segmentation Service",
        "status": "running",
        "model_loaded": model_loaded,
        "endpoints": {
            "health": "/health",
            "segment": "/segment (POST)",
            "cleanup": "/cleanup (POST)"
        }
    }

@app.post("/cleanup")
async def manual_cleanup():
    """Manually trigger GPU memory cleanup"""
    try:
        import torch
        import gc

        # Reset predictor state if available
        if sam2_predictor is not None:
            sam2_predictor.reset_state()
            logger.info("SAM2 predictor state reset")

        # Run Python garbage collection
        gc.collect()

        # Clear CUDA cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()  # Wait for all operations to complete

            # Get memory stats after cleanup
            allocated = torch.cuda.memory_allocated() / 1024**2  # MB
            reserved = torch.cuda.memory_reserved() / 1024**2  # MB
            logger.info(f"Manual cleanup completed: allocated={allocated:.1f}MB, reserved={reserved:.1f}MB")

            return {
                "status": "success",
                "message": "GPU memory cleanup completed",
                "memory_mb": {
                    "allocated": round(allocated, 2),
                    "reserved": round(reserved, 2)
                }
            }
        else:
            return {
                "status": "success",
                "message": "Cleanup completed (CPU mode, no GPU cleanup needed)"
            }

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {
            "status": "error",
            "message": f"Cleanup failed: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
