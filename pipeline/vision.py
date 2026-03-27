"""Cloud Vision API: object detection, label detection, safe search."""
import logging
import os

import requests

from config import GCS_BUCKET, GCS_ORIGINALS_PREFIX

logger = logging.getLogger(__name__)

VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


def _get_api_key() -> str:
    key = os.environ.get("VISION_API_KEY", "")
    if not key:
        raise RuntimeError("VISION_API_KEY not set")
    return key


def _gcs_uri(ean: str) -> str:
    return f"gs://{GCS_BUCKET}/{GCS_ORIGINALS_PREFIX}/{ean}.jpg"


def _annotate_batch(eans: list[str], api_key: str) -> list[dict]:
    requests_payload = [
        {
            "image": {"source": {"gcsImageUri": _gcs_uri(ean)}},
            "features": [
                {"type": "OBJECT_LOCALIZATION", "maxResults": 5},
                {"type": "LABEL_DETECTION", "maxResults": 5},
                {"type": "SAFE_SEARCH_DETECTION"},
            ],
        }
        for ean in eans
    ]
    resp = requests.post(
        f"{VISION_ENDPOINT}?key={api_key}",
        json={"requests": requests_payload},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("responses", [])


def _parse_response(ean: str, response: dict) -> dict:
    labels = response.get("labelAnnotations", [])
    objects = response.get("localizedObjectAnnotations", [])
    safe = response.get("safeSearchAnnotation", {})

    primary_label = labels[0]["description"] if labels else None
    primary_confidence = labels[0]["score"] if labels else None

    # Centration score: 1 if a dominant object covers > 40% of the image
    centration_score = 0
    if objects:
        best = objects[0]
        verts = best.get("boundingPoly", {}).get("normalizedVertices", [])
        if len(verts) >= 4:
            w = abs(verts[1].get("x", 0) - verts[0].get("x", 0))
            h = abs(verts[2].get("y", 0) - verts[1].get("y", 0))
            if w * h > 0.4:
                centration_score = 100
            elif w * h > 0.2:
                centration_score = 50

    return {
        "ean": ean,
        "primary_object_label": primary_label,
        "primary_object_confidence": primary_confidence,
        "centration_score": centration_score,
        "safe_search_adult": safe.get("adult", "UNKNOWN"),
        "safe_search_violence": safe.get("violence", "UNKNOWN"),
    }


def run(successful_eans: list[str]) -> dict[str, dict]:
    """Run Cloud Vision on all EANs in batches of 16 (API limit)."""
    api_key = _get_api_key()
    results: dict[str, dict] = {}
    batch_size = 16

    for i in range(0, len(successful_eans), batch_size):
        batch = successful_eans[i : i + batch_size]
        try:
            responses = _annotate_batch(batch, api_key)
            for ean, resp in zip(batch, responses):
                results[ean] = _parse_response(ean, resp)
        except Exception as e:
            logger.error(f"Vision API batch {i//batch_size} failed: {e}")
            for ean in batch:
                results[ean] = {"ean": ean, "primary_object_label": None, "centration_score": 0}
        if (i + batch_size) % 160 == 0:
            logger.info(f"Vision API: {i + batch_size}/{len(successful_eans)}")

    return results
