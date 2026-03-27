"""Fusion scoring: combine text_score + visual_score -> catalog_score, write to BQ."""
import logging

import bq_client

logger = logging.getLogger(__name__)

TEXT_WEIGHT = 0.6
VISUAL_WEIGHT = 0.4


def compute_visual_score(visual_scores: dict, vision_results: dict, ean: str) -> int:
    """Combine resolution + sharpness + centration into 0-100 visual_score."""
    vs = visual_scores.get(ean, {})
    vr = vision_results.get(ean, {})

    resolution = vs.get("resolution_score", 0) or 0
    sharpness = vs.get("sharpness_score", 0) or 0
    centration = vr.get("centration_score", 0) or 0

    # Weighted: resolution 40%, sharpness 40%, centration 20%
    score = int(resolution * 0.4 + sharpness * 0.4 + centration * 0.2)
    return min(100, max(0, score))


def update_scores(
    products: list[dict],
    text_scores: dict[str, int],
    visual_scores: dict[str, dict],
    vision_results: dict[str, dict],
    visual_detections: dict[str, dict],
    thumbnail_urls: dict[str, dict[int, str | None]],
    anomaly_eans: set[str],
    run_id: str,
    run_date: str,
) -> list[dict]:
    rows: list[dict] = []

    for product in products:
        ean = product["ean"]
        text_score = text_scores.get(ean, 60)
        visual_score = compute_visual_score(visual_scores, vision_results, ean)
        catalog_score = int(round(TEXT_WEIGHT * text_score + VISUAL_WEIGHT * visual_score))

        thumbs = thumbnail_urls.get(ean, {})
        vd = visual_detections.get(ean, {})

        rows.append(
            {
                "ean": ean,
                "run_id": run_id,
                "run_date": run_date,
                "text_score": text_score,
                "visual_score": visual_score,
                "catalog_score": catalog_score,
                "product_name": product.get("product_name"),
                "categories": product.get("categories"),
                "image_url": product.get("image_url"),
                "thumbnail_url_128": thumbs.get(128),
                "thumbnail_url_256": thumbs.get(256),
                "thumbnail_url_512": thumbs.get(512),
                "has_anomaly_text": ean in anomaly_eans,
                "has_anomaly_visual": (vd.get("safe_search_adult") in ("LIKELY", "VERY_LIKELY")),
            }
        )

    bq_client.insert_rows("product_scores", rows)
    logger.info(f"Scorer: wrote {len(rows)} product_scores rows")
    return rows


def compute_text_scores(products: list[dict]) -> dict[str, int]:
    """Per-product text_score based on field weights."""
    WEIGHTS = {
        "product_name": 30,
        "brands": 15,
        "categories": 20,
        "ingredients_text": 20,
        "nutriscore_grade": 10,
        "quantity": 3,
        "packaging": 2,
    }
    scores: dict[str, int] = {}
    for p in products:
        score = sum(
            w for field, w in WEIGHTS.items()
            if p.get(field) and str(p[field]).strip()
        )
        scores[p["ean"]] = score
    return scores
