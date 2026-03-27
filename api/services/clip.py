"""CLIP embedding for visual search queries (encode a new image by URL)."""
import logging
from io import BytesIO

import requests
import torch
from PIL import Image
from transformers import CLIPModel

logger = logging.getLogger(__name__)

_CLIP_MODEL = "openai/clip-vit-base-patch32"
_CLIP_SIZE = 224
_CLIP_MEAN = torch.tensor([0.48145466, 0.4578275, 0.40821073]).view(3, 1, 1)
_CLIP_STD = torch.tensor([0.26862954, 0.26130258, 0.27577711]).view(3, 1, 1)

_model: CLIPModel | None = None


def _load() -> CLIPModel:
    global _model
    if _model is None:
        logger.info("Loading CLIP model for API...")
        _model = CLIPModel.from_pretrained(_CLIP_MODEL)
        _model.eval()
    return _model


def _preprocess(img: Image.Image) -> torch.Tensor:
    """Apply CLIP preprocessing using pure PyTorch (no numpy, no tokenizer)."""
    img = img.resize((_CLIP_SIZE, _CLIP_SIZE), Image.BICUBIC)
    buf = bytes(img.tobytes())
    arr = torch.frombuffer(buf, dtype=torch.uint8).clone()
    arr = arr.view(_CLIP_SIZE, _CLIP_SIZE, 3).permute(2, 0, 1).float() / 255.0
    arr = (arr - _CLIP_MEAN) / _CLIP_STD
    return arr.unsqueeze(0)  # [1, 3, 224, 224]


def encode_image_url(image_url: str) -> list[float]:
    resp = requests.get(image_url, timeout=10)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content)).convert("RGB")
    model = _load()
    pixel_values = _preprocess(img)
    with torch.no_grad():
        features = model.get_image_features(pixel_values=pixel_values)
        features = features / features.norm(dim=-1, keepdim=True)
    return features[0].tolist()
