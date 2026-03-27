"""Generate thumbnails in 3 sizes from GCS originals, store back to GCS."""
import logging
from io import BytesIO

from google.cloud import storage
from PIL import Image

from config import (
    GCS_BUCKET,
    GCS_ORIGINALS_PREFIX,
    GCS_THUMBNAILS_PREFIX,
    THUMBNAIL_SIZES,
)

logger = logging.getLogger(__name__)


def _thumbnail_path(size: int, ean: str) -> str:
    return f"{GCS_THUMBNAILS_PREFIX}/{size}/{ean}.jpg"


def _public_url(path: str) -> str:
    return f"https://storage.googleapis.com/{GCS_BUCKET}/{path}"


def generate_thumbnails(ean: str, bucket: storage.Bucket) -> dict[int, str | None]:
    """Generate 3 thumbnail sizes for one EAN. Returns {size: public_url or None}."""
    original_blob = bucket.blob(f"{GCS_ORIGINALS_PREFIX}/{ean}.jpg")
    urls: dict[int, str | None] = {s: None for s in THUMBNAIL_SIZES}

    try:
        data = original_blob.download_as_bytes()
        img = Image.open(BytesIO(data)).convert("RGB")
        for size in THUMBNAIL_SIZES:
            thumb = img.copy()
            thumb.thumbnail((size, size), Image.LANCZOS)
            buf = BytesIO()
            thumb.save(buf, format="JPEG", quality=85, optimize=True)
            buf.seek(0)
            path = _thumbnail_path(size, ean)
            blob = bucket.blob(path)
            blob.upload_from_file(buf, content_type="image/jpeg")
            urls[size] = _public_url(path)
    except Exception as e:
        logger.warning(f"Thumbnail failed for {ean}: {e}")

    return urls


def run(successful_eans: list[str]) -> dict[str, dict[int, str | None]]:
    """Generate thumbnails for all successfully downloaded EANs."""
    gcs = storage.Client()
    bucket = gcs.bucket(GCS_BUCKET)
    results: dict[str, dict[int, str | None]] = {}

    for i, ean in enumerate(successful_eans):
        results[ean] = generate_thumbnails(ean, bucket)
        if (i + 1) % 100 == 0:
            logger.info(f"Thumbnails: {i + 1}/{len(successful_eans)}")

    logger.info(f"Thumbnails complete for {len(results)} products")
    return results
