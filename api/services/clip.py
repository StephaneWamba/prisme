"""CLIP embedding for visual search queries (encode a new image by URL)."""
import logging
from io import BytesIO

import requests
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

logger = logging.getLogger(__name__)

_CLIP_MODEL = "openai/clip-vit-base-patch32"
_model: CLIPModel | None = None
_processor: CLIPProcessor | None = None


def _load() -> tuple[CLIPModel, CLIPProcessor]:
    global _model, _processor
    if _model is None:
        logger.info("Loading CLIP model for API...")
        _processor = CLIPProcessor.from_pretrained(_CLIP_MODEL)
        _model = CLIPModel.from_pretrained(_CLIP_MODEL)
        _model.eval()
    return _model, _processor


def encode_image_url(image_url: str) -> list[float]:
    resp = requests.get(image_url, timeout=10)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content)).convert("RGB")
    model, processor = _load()
    inputs = processor(images=img, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().numpy()[0].tolist()
