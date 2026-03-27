"""Pipeline configuration and constants."""
import os

PROJECT_ID = "prisme-wamba-2026"
DATASET = "prisme_dataset"
REGION = "europe-west1"
GCS_BUCKET = "prisme-assets"
GCS_ORIGINALS_PREFIX = "originals"
GCS_THUMBNAILS_PREFIX = "thumbnails"

# Vision API
VISION_API_KEY = os.environ.get("VISION_API_KEY", "")

# Vertex AI
VERTEX_MODEL = "gemini-1.5-flash"
VERTEX_LOCATION = "europe-west1"

# CLIP
CLIP_MODEL = "openai/clip-vit-base-patch32"
CLIP_BATCH_SIZE = 32
CLIP_CHECKPOINT_EVERY = 320  # rows before writing to BQ

# Download
DOWNLOAD_CONCURRENT = 64
DOWNLOAD_TIMEOUT = 10  # seconds per image
DOWNLOAD_RETRY = 3
DOWNLOAD_MIN_SIZE_KB = 5

# Thumbnail sizes (px)
THUMBNAIL_SIZES = [128, 256, 512]

# Sharpness threshold (Laplacian variance)
SHARPNESS_THRESHOLD = 100.0

# Pipeline subset
MAX_PRODUCTS_PER_CATEGORY = 50
