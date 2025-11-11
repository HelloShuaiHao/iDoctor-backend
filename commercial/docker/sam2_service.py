"""
SAM2 Segmentation Service
Provides REST API for automatic image segmentation using SAM2 model.
"""

import os
import time
import logging
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

def perform_sam2_segmentation(image_array: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Perform SAM2 segmentation on image.
    Returns (mask, confidence_score)
    """
    if not model_loaded or sam2_predictor is None:
        mask = mock_segmentation(image_array)
        return mask, 0.5  # Mock confidence

    try:
        # Set image for SAM2
        sam2_predictor.set_image(image_array)

        # Use automatic mask generation (point prompts at image center)
        h, w = image_array.shape[:2]
        point_coords = np.array([[w // 2, h // 2]])
        point_labels = np.array([1])  # Foreground point

        # Predict mask
        masks, scores, _ = sam2_predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True
        )

        # Select mask with highest score
        best_idx = np.argmax(scores)
        mask = masks[best_idx]
        confidence = float(scores[best_idx])

        # Convert boolean mask to uint8
        mask_uint8 = (mask * 255).astype(np.uint8)

        logger.info(f"SAM2 segmentation completed with confidence: {confidence:.3f}")
        return mask_uint8, confidence

    except Exception as e:
        logger.error(f"SAM2 segmentation failed: {e}")
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
    load_sam2_model()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model_loaded,
        "service": "sam2_segmentation",
        "version": "1.0.0"
    }

@app.post("/segment", response_model=SegmentationResponse)
async def segment_image(
    file: UploadFile = File(...),
    image_type: str = Form("auto"),
    return_format: str = Form("base64")
):
    """
    Segment an image using SAM2.

    Args:
        file: Image file (PNG, JPEG, or DICOM)
        image_type: Type hint for segmentation ("L3", "middle", or "auto")
        return_format: Response format ("png" or "base64")

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

        logger.info(f"Processing image: shape={image_array.shape}, type={image_type}")

        # Perform segmentation
        mask, confidence = perform_sam2_segmentation(image_array)

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
            "segment": "/segment (POST)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
