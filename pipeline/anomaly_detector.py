"""Read text metrics, compute Z-scores against history, write anomalies to BQ."""
import logging
import statistics
import uuid

import bq_client

logger = logging.getLogger(__name__)

ANOMALY_Z_THRESHOLD = 2.5


def detect(metrics: list[dict], run_id: str, run_date: str) -> list[dict]:
    """Compare current metrics against 30-day history from BQ, write anomalies."""
    metric_names = list({m["metric_name"] for m in metrics})
    anomalies: list[dict] = []

    for metric_name in metric_names:
        # Fetch historical values (last 30 days, excluding current run)
        history = bq_client.run_query(
            """
            SELECT metric_value
            FROM `prisme-wamba-2026.prisme_dataset.text_metrics`
            WHERE metric_name = @name
              AND run_id != @run_id
              AND run_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            ORDER BY run_date DESC
            LIMIT 30
            """,
            params=[
                bq_client.bigquery.ScalarQueryParameter("name", "STRING", metric_name),
                bq_client.bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
            ],
        )
        if len(history) < 3:
            continue

        hist_values = [r["metric_value"] for r in history]
        mean = statistics.mean(hist_values)
        std = statistics.stdev(hist_values) if len(hist_values) > 1 else 0

        current = next((m for m in metrics if m["metric_name"] == metric_name), None)
        if current is None or std == 0:
            continue

        z = (current["metric_value"] - mean) / std
        if abs(z) < ANOMALY_Z_THRESHOLD:
            continue

        severity = (
            "CRITICAL" if abs(z) > 4 else
            "HIGH" if abs(z) > 3 else
            "MEDIUM"
        )
        anomaly_type = (
            "COMPLETENESS_DROP" if metric_name.startswith("completeness_") else
            "COHERENCE_ISSUE" if metric_name.startswith("coherence_") else
            "STATISTICAL_OUTLIER"
        )
        anomalies.append(
            {
                "anomaly_id": str(uuid.uuid4()),
                "run_id": run_id,
                "run_date": run_date,
                "metric_name": metric_name,
                "anomaly_type": anomaly_type,
                "expected_value": round(mean, 2),
                "observed_value": current["metric_value"],
                "confidence": None,
                "z_score": round(z, 3),
                "severity": severity,
                "description": (
                    f"{metric_name} deviated by Z={abs(z):.2f} "
                    f"(expected ~{mean:.1f}, got {current['metric_value']:.1f})"
                ),
            }
        )

    if anomalies:
        bq_client.insert_rows("text_anomalies", anomalies)
        logger.info(f"Anomaly detector: wrote {len(anomalies)} anomalies")
    else:
        logger.info("Anomaly detector: no anomalies detected")

    return anomalies


def run(metrics: list[dict], run_id: str, run_date: str) -> list[dict]:
    return detect(metrics, run_id, run_date)
