"""CLIP embeddings: encode product images, write to BQ with checkpoints."""
import gc
import logging
import time
from io import BytesIO

import torch
from google.cloud import storage
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

import bq_client
from config import (
    GCS_BUCKET,
    GCS_ORIGINALS_PREFIX,
    CLIP_MODEL,
    CLIP_BATCH_SIZE,
    CLIP_CHECKPOINT_EVERY,
)

logger = logging.getLogger(__name__)

_model: CLIPModel | None = None
_processor: CLIPProcessor | None = None


def _load_model() -> tuple[CLIPModel, CLIPProcessor]:
    global _model, _processor
    if _model is None:
        logger.info(f"Loading CLIP model {CLIP_MODEL}...")
        _processor = CLIPProcessor.from_pretrained(CLIP_MODEL)
        _model = CLIPModel.from_pretrained(CLIP_MODEL)
        _model.eval()
    return _model, _processor


def _encode_batch(images: list[Image.Image], model: CLIPModel, processor: CLIPProcessor) -> list[list[float]]:
    inputs = processor(images=images, return_tensors="pt", padding=True)
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().numpy().tolist()


def encode_all(eans: list[str], run_id: str, run_date: str) -> None:
    """Encode all images and write embeddings to BQ with periodic checkpoints."""
    gcs = storage.Client()
    bucket = gcs.bucket(GCS_BUCKET)
    model, processor = _load_model()

    pending_rows: list[dict] = []

    for batch_start in range(0, len(eans), CLIP_BATCH_SIZE):
        batch_eans = eans[batch_start : batch_start + CLIP_BATCH_SIZE]
        images: list[Image.Image] = []
        valid_eans: list[str] = []

        for ean in batch_eans:
            try:
                blob = bucket.blob(f"{GCS_ORIGINALS_PREFIX}/{ean}.jpg")
                data = blob.download_as_bytes()
                img = Image.open(BytesIO(data)).convert("RGB")
                images.append(img)
                valid_eans.append(ean)
            except Exception as e:
                logger.warning(f"CLIP load failed for {ean}: {e}")

        if not images:
            continue

        t0 = time.time()
        embeddings = _encode_batch(images, model, processor)
        elapsed_ms = int((time.time() - t0) * 1000)

        for ean, embedding in zip(valid_eans, embeddings):
            pending_rows.append(
                {
                    "ean": ean,
                    "run_id": run_id,
                    "run_date": run_date,
                    "embedding": embedding,
                    "embedding_model_name": CLIP_MODEL,
                    "embedding_compute_time_ms": elapsed_ms // len(valid_eans),
                }
            )

        if len(pending_rows) >= CLIP_CHECKPOINT_EVERY:
            bq_client.insert_rows("visual_embeddings", pending_rows)
            logger.info(f"CLIP checkpoint: wrote {len(pending_rows)} rows, total {batch_start + CLIP_BATCH_SIZE}/{len(eans)}")
            pending_rows = []
            gc.collect()

    if pending_rows:
        bq_client.insert_rows("visual_embeddings", pending_rows)
        logger.info(f"CLIP final checkpoint: wrote {len(pending_rows)} rows")

    gc.collect()
    logger.info("CLIP encoding complete")


def run(successful_eans: list[str], run_id: str, run_date: str) -> None:
    encode_all(successful_eans, run_id, run_date)
