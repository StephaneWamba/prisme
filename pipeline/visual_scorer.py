"""Score image quality: resolution, sharpness, aspect ratio."""
import logging
from io import BytesIO

import cv2
import numpy as np
from google.cloud import storage
from PIL import Image

from config import GCS_BUCKET, GCS_ORIGINALS_PREFIX, SHARPNESS_THRESHOLD

logger = logging.getLogger(__name__)


def _laplacian_variance(img_array: np.ndarray) -> float:
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def score_image(ean: str, bucket: storage.Bucket, download_result: dict) -> dict:
    """Compute visual quality scores for one product image."""
    base = {
        "ean": ean,
        "image_width_px": None,
        "image_height_px": None,
        "image_size_kb": download_result.get("size_kb"),
        "resolution_score": 0,
        "sharpness_score": 0,
        "vision_quality_score": 0,
    }
    if not download_result.get("success"):
        return base

    try:
        blob = bucket.blob(f"{GCS_ORIGINALS_PREFIX}/{ean}.jpg")
        data = blob.download_as_bytes()
        img = Image.open(BytesIO(data)).convert("RGB")
        w, h = img.size
        arr = np.array(img)

        # Resolution score: 0-100
        min_dim = min(w, h)
        resolution_score = min(100, int(min_dim / 5))  # 500px -> 100

        # Sharpness score: 0-100
        lap_var = _laplacian_variance(arr)
        sharpness_score = min(100, int(lap_var / SHARPNESS_THRESHOLD * 100))

        return {
            **base,
            "image_width_px": w,
            "image_height_px": h,
            "resolution_score": resolution_score,
            "sharpness_score": sharpness_score,
        }
    except Exception as e:
        logger.warning(f"visual_scorer failed for {ean}: {e}")
        return base


def run(download_results: list[dict]) -> dict[str, dict]:
    gcs = storage.Client()
    bucket = gcs.bucket(GCS_BUCKET)
    scores: dict[str, dict] = {}
    for i, result in enumerate(download_results):
        ean = result["ean"]
        scores[ean] = score_image(ean, bucket, result)
        if (i + 1) % 200 == 0:
            logger.info(f"Visual scoring: {i + 1}/{len(download_results)}")
    return scores
