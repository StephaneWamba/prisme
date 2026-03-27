"""API configuration."""
import os

PROJECT_ID = "prisme-wamba-2026"
DATASET = "prisme_dataset"
GCS_BUCKET = "prisme-assets"
VERTEX_MODEL = "gemini-1.5-flash"
VERTEX_LOCATION = "europe-west1"
VISION_API_KEY = os.environ.get("VISION_API_KEY", "")
CACHE_TTL_SECONDS = 600  # 10 minutes
