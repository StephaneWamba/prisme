"""Text metadata profiling: compute completeness metrics and write to BQ."""
import logging
import uuid
from datetime import datetime, timezone

import bq_client

logger = logging.getLogger(__name__)

FIELDS = [
    ("product_name", 30),
    ("brands", 15),
    ("categories", 20),
    ("ingredients_text", 20),
    ("nutriscore_grade", 10),
    ("quantity", 3),
    ("packaging", 2),
]


def compute_metrics(products: list[dict], run_id: str, run_date: str) -> list[dict]:
    n = len(products)
    if n == 0:
        return []

    metrics: list[dict] = []

    for field, _ in FIELDS:
        count_present = sum(
            1 for p in products if p.get(field) and str(p[field]).strip()
        )
        completeness = round(count_present * 100.0 / n, 2)
        metrics.append(
            {
                "run_id": run_id,
                "run_date": run_date,
                "metric_name": f"completeness_{field}",
                "metric_value": completeness,
                "z_score": None,
                "is_anomaly": False,
            }
        )

    # Coherence: nutriscore present when ingredients present
    with_ingredients = [p for p in products if p.get("ingredients_text") and str(p["ingredients_text"]).strip()]
    if with_ingredients:
        with_nutriscore = sum(1 for p in with_ingredients if p.get("nutriscore_grade"))
        coherence = round(with_nutriscore * 100.0 / len(with_ingredients), 2)
    else:
        coherence = 100.0
    metrics.append(
        {
            "run_id": run_id,
            "run_date": run_date,
            "metric_name": "coherence_nutriscore_with_ingredients",
            "metric_value": coherence,
            "z_score": None,
            "is_anomaly": False,
        }
    )

    # Avg product_name length
    lengths = [len(p["product_name"]) for p in products if p.get("product_name")]
    avg_len = round(sum(lengths) / len(lengths), 2) if lengths else 0.0
    metrics.append(
        {
            "run_id": run_id,
            "run_date": run_date,
            "metric_name": "avg_length_product_name",
            "metric_value": avg_len,
            "z_score": None,
            "is_anomaly": False,
        }
    )

    return metrics


def run(products: list[dict], run_id: str, run_date: str) -> list[dict]:
    metrics = compute_metrics(products, run_id, run_date)
    bq_client.insert_rows("text_metrics", metrics)
    logger.info(f"Text profiling: wrote {len(metrics)} metrics")
    return metrics
