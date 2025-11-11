"""
SAM2 Client Module
Handles communication with SAM2 Docker service for automatic segmentation.
"""

import os
import time
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import base64
from io import BytesIO

import httpx
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

class SAM2Client:
    """Client for communicating with SAM2 segmentation service"""

    def __init__(
        self,
        service_url: str = None,
        timeout: int = 30,
        enabled: bool = True
    ):
        """
        Initialize SAM2 client.

        Args:
            service_url: URL of SAM2 service (default from env var)
            timeout: Request timeout in seconds
            enabled: Whether SAM2 service is enabled
        """
        self.service_url = service_url or os.getenv(
            "SAM2_SERVICE_URL",
            "http://sam2_service:8000"
        )
        self.timeout = timeout or int(os.getenv("SAM2_REQUEST_TIMEOUT", "30"))
        self.enabled = enabled and os.getenv("SAM2_ENABLED", "true").lower() == "true"

        # Cache configuration
        self.cache_expire_hours = int(os.getenv("SAM2_CACHE_EXPIRE_HOURS", "24"))
        self._cache: Dict[str, Dict[str, Any]] = {}

        # Health status
        self._is_healthy = False
        self._last_health_check = None

        logger.info(
            f"SAM2Client initialized: url={self.service_url}, "
            f"timeout={self.timeout}s, enabled={self.enabled}"
        )

    async def check_health(self) -> bool:
        """
        Check if SAM2 service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        if not self.enabled:
            logger.info("SAM2 service is disabled")
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.service_url}/health")
                response.raise_for_status()

                data = response.json()
                self._is_healthy = data.get("status") == "healthy"
                self._last_health_check = datetime.now()

                model_loaded = data.get("model_loaded", False)
                logger.info(
                    f"SAM2 health check: healthy={self._is_healthy}, "
                    f"model_loaded={model_loaded}"
                )

                return self._is_healthy

        except Exception as e:
            logger.warning(f"SAM2 health check failed: {e}")
            self._is_healthy = False
            return False

    def is_available(self) -> bool:
        """
        Check if SAM2 service is available (enabled and recently healthy).

        Returns:
            True if available, False otherwise
        """
        if not self.enabled:
            return False

        # Consider service available if last health check was successful within 5 minutes
        if self._last_health_check:
            age = (datetime.now() - self._last_health_check).total_seconds()
            if age < 300:  # 5 minutes
                return self._is_healthy

        # If no recent health check or cache expired, assume unavailable
        # Note: The startup health check should set _is_healthy and _last_health_check
        return False

    def _compute_image_hash(self, image_data: bytes) -> str:
        """
        Compute hash of image data for caching.

        Args:
            image_data: Raw image bytes

        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(image_data).hexdigest()

    def _get_from_cache(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get segmentation result from cache.

        Args:
            image_hash: Hash of image data

        Returns:
            Cached result or None if not found/expired
        """
        if image_hash not in self._cache:
            return None

        cached = self._cache[image_hash]
        cached_time = cached.get("cached_at")

        # Check expiration
        if cached_time:
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600
            if age_hours > self.cache_expire_hours:
                logger.debug(f"Cache expired for hash {image_hash[:8]}...")
                del self._cache[image_hash]
                return None

        logger.info(f"Cache hit for image hash {image_hash[:8]}...")
        return cached.get("result")

    def _save_to_cache(self, image_hash: str, result: Dict[str, Any]):
        """
        Save segmentation result to cache.

        Args:
            image_hash: Hash of image data
            result: Segmentation result to cache
        """
        self._cache[image_hash] = {
            "result": result,
            "cached_at": datetime.now()
        }
        logger.debug(f"Saved to cache: hash={image_hash[:8]}...")

    async def segment_image(
        self,
        image_path: str = None,
        image_data: bytes = None,
        image_type: str = "auto",
        use_cache: bool = True
    ) -> Tuple[Optional[bytes], Dict[str, Any]]:
        """
        Segment an image using SAM2 service.

        Args:
            image_path: Path to image file (if image_data not provided)
            image_data: Raw image bytes (if image_path not provided)
            image_type: Type hint for segmentation ("L3", "middle", or "auto")
            use_cache: Whether to use caching

        Returns:
            Tuple of (mask_image_bytes, metadata_dict)
            mask_image_bytes: PNG mask as bytes, or None if failed
            metadata_dict: Contains confidence_score, processing_time_ms, cached, error
        """
        if not self.enabled:
            return None, {"error": "SAM2 service is disabled"}

        # If service is not available or health check is stale, try checking again
        if not self.is_available():
            logger.info("SAM2 service not available, attempting health check...")
            health_ok = await self.check_health()
            if not health_ok:
                return None, {"error": "SAM2 service is unavailable"}

        start_time = time.time()

        try:
            # Load image data
            if image_data is None:
                if image_path is None:
                    raise ValueError("Either image_path or image_data must be provided")
                with open(image_path, "rb") as f:
                    image_data = f.read()

            # Check cache
            image_hash = self._compute_image_hash(image_data)
            if use_cache:
                cached_result = self._get_from_cache(image_hash)
                if cached_result:
                    cached_result["cached"] = True
                    return base64.b64decode(cached_result["mask_data"]), cached_result

            # Prepare request
            files = {"file": ("image.png", BytesIO(image_data), "image/png")}
            data = {
                "image_type": image_type,
                "return_format": "base64"
            }

            # Send request to SAM2 service
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/segment",
                    files=files,
                    data=data
                )
                response.raise_for_status()

                result = response.json()

            # Extract mask data
            mask_base64 = result.get("mask_data")
            if not mask_base64:
                raise ValueError("No mask_data in SAM2 response")

            mask_bytes = base64.b64decode(mask_base64)

            # Build metadata
            metadata = {
                "confidence_score": result.get("confidence_score", 0.0),
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "cached": False,
                "bounding_box": result.get("bounding_box"),
                "sam2_processing_time_ms": result.get("processing_time_ms", 0)
            }

            # Save to cache
            if use_cache:
                cache_data = metadata.copy()
                cache_data["mask_data"] = mask_base64
                self._save_to_cache(image_hash, cache_data)

            logger.info(
                f"SAM2 segmentation completed: "
                f"confidence={metadata['confidence_score']:.3f}, "
                f"time={metadata['processing_time_ms']}ms"
            )

            return mask_bytes, metadata

        except httpx.TimeoutException:
            logger.error("SAM2 request timeout")
            return None, {
                "error": "SAM2 request timeout",
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"SAM2 HTTP error: {e.response.status_code}")
            return None, {
                "error": f"SAM2 service error: {e.response.status_code}",
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            logger.error(f"SAM2 segmentation failed: {e}", exc_info=True)
            return None, {
                "error": f"Segmentation failed: {str(e)}",
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

    def clear_cache(self):
        """Clear all cached segmentation results"""
        self._cache.clear()
        logger.info("SAM2 cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "cache_size": len(self._cache),
            "cache_expire_hours": self.cache_expire_hours,
            "is_healthy": self._is_healthy,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None
        }


# Global SAM2 client instance
_sam2_client: Optional[SAM2Client] = None


def get_sam2_client() -> SAM2Client:
    """
    Get global SAM2 client instance (singleton pattern).

    Returns:
        SAM2Client instance
    """
    global _sam2_client

    if _sam2_client is None:
        _sam2_client = SAM2Client()

    return _sam2_client


async def init_sam2_client() -> bool:
    """
    Initialize SAM2 client and perform health check.
    Should be called on application startup.

    Returns:
        True if SAM2 is available, False otherwise
    """
    client = get_sam2_client()
    is_healthy = await client.check_health()

    if not is_healthy:
        logger.warning(
            "⚠️  SAM2 service is not available. "
            "One-click segmentation will be disabled."
        )
    else:
        logger.info("✅ SAM2 service is available and healthy")

    return is_healthy
