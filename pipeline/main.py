"""Pipeline orchestrator: text audit + visual audit in parallel, then fusion scoring."""
import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import bq_client
import anomaly_detector
import downloader
import encoder
import report_generator
import scorer
import text_profiler
import thumbnailer
import vision
import visual_scorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def fetch_products() -> list[dict]:
    return bq_client.run_query(
        "SELECT * FROM `prisme-wamba-2026.prisme_dataset.products_selected` LIMIT 15000"
    )


def text_branch(products: list[dict], run_id: str, run_date: str) -> tuple[list[dict], list[dict]]:
    """Returns (metrics, anomalies)."""
    metrics = text_profiler.run(products, run_id, run_date)
    anomalies = anomaly_detector.run(metrics, run_id, run_date)
    return metrics, anomalies


def visual_branch(products: list[dict], run_id: str, run_date: str) -> tuple[dict, dict, dict, dict]:
    """Returns (download_results_by_ean, visual_scores, vision_results, thumbnail_urls)."""
    download_results = downloader.run(products)
    successful_eans = [r["ean"] for r in download_results if r.get("success")]
    logger.info(f"Downloaded {len(successful_eans)}/{len(products)} images")

    vs = visual_scorer.run(download_results)
    vr = vision.run(successful_eans)
    thumbs = thumbnailer.run(successful_eans)
    encoder.run(successful_eans, run_id, run_date)

    dl_by_ean = {r["ean"]: r for r in download_results}

    # Write visual_detections to BQ
    visual_detection_rows = []
    for ean in download_results:
        e = ean["ean"]
        row = {
            "ean": e,
            "run_id": run_id,
            "run_date": run_date,
            "image_url": next((p["image_url"] for p in products if p["ean"] == e), None),
            "image_width_px": vs.get(e, {}).get("image_width_px"),
            "image_height_px": vs.get(e, {}).get("image_height_px"),
            "image_size_kb": ean.get("size_kb"),
            "download_success": ean.get("success", False),
            "download_error_msg": ean.get("error"),
            "resolution_score": vs.get(e, {}).get("resolution_score", 0),
            "sharpness_score": vs.get(e, {}).get("sharpness_score", 0),
            "centration_score": vr.get(e, {}).get("centration_score", 0),
            "primary_object_label": vr.get(e, {}).get("primary_object_label"),
            "primary_object_confidence": vr.get(e, {}).get("primary_object_confidence"),
            "safe_search_adult": vr.get(e, {}).get("safe_search_adult"),
            "safe_search_violence": vr.get(e, {}).get("safe_search_violence"),
            "vision_quality_score": vs.get(e, {}).get("vision_quality_score", 0),
        }
        visual_detection_rows.append(row)

    bq_client.insert_rows("visual_detections", visual_detection_rows)

    return dl_by_ean, vs, vr, thumbs


def run_pipeline() -> None:
    run_id = str(uuid.uuid4())
    run_date = datetime.now(timezone.utc).isoformat()
    logger.info(f"Pipeline start: run_id={run_id}")

    products = fetch_products()
    logger.info(f"Loaded {len(products)} products")

    with ThreadPoolExecutor(max_workers=2) as pool:
        text_future = pool.submit(text_branch, products, run_id, run_date)
        visual_future = pool.submit(visual_branch, products, run_id, run_date)

        metrics, anomalies = text_future.result()
        dl_by_ean, visual_scores, vision_results, thumbnail_urls = visual_future.result()

    anomaly_eans = {a["ean"] for a in anomalies if "ean" in a}
    text_scores = scorer.compute_text_scores(products)

    scorer.update_scores(
        products=products,
        text_scores=text_scores,
        visual_scores=visual_scores,
        vision_results=vision_results,
        visual_detections=vision_results,
        thumbnail_urls=thumbnail_urls,
        anomaly_eans=anomaly_eans,
        run_id=run_id,
        run_date=run_date,
    )

    report_generator.run(run_id, run_date)
    logger.info("Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()
