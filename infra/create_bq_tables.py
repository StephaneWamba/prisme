"""Create all BigQuery tables for Prisme dataset."""
from google.cloud import bigquery

PROJECT_ID = "prisme-wamba-2026"
DATASET = "prisme_dataset"
client = bigquery.Client(project=PROJECT_ID)

SCHEMAS = {
    "products_selected": [
        bigquery.SchemaField("ean", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_name", "STRING"),
        bigquery.SchemaField("brands", "STRING"),
        bigquery.SchemaField("categories", "STRING"),
        bigquery.SchemaField("ingredients_text", "STRING"),
        bigquery.SchemaField("nutriscore_grade", "STRING"),
        bigquery.SchemaField("quantity", "STRING"),
        bigquery.SchemaField("packaging", "STRING"),
        bigquery.SchemaField("image_url", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("image_small_url", "STRING"),
        bigquery.SchemaField("country_code", "STRING"),
        bigquery.SchemaField("last_modified_t", "TIMESTAMP"),
        bigquery.SchemaField("ingestion_timestamp", "TIMESTAMP", mode="REQUIRED"),
    ],
    "text_metrics": [
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("run_date", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("metric_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("metric_value", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("z_score", "FLOAT64"),
        bigquery.SchemaField("is_anomaly", "BOOL"),
    ],
    "text_anomalies": [
        bigquery.SchemaField("anomaly_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("run_date", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("metric_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("anomaly_type", "STRING"),
        bigquery.SchemaField("expected_value", "FLOAT64"),
        bigquery.SchemaField("observed_value", "FLOAT64"),
        bigquery.SchemaField("confidence", "FLOAT64"),
        bigquery.SchemaField("z_score", "FLOAT64"),
        bigquery.SchemaField("severity", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("description", "STRING"),
    ],
    "visual_detections": [
        bigquery.SchemaField("ean", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("run_date", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("image_url", "STRING"),
        bigquery.SchemaField("image_width_px", "INT64"),
        bigquery.SchemaField("image_height_px", "INT64"),
        bigquery.SchemaField("image_size_kb", "FLOAT64"),
        bigquery.SchemaField("download_success", "BOOL"),
        bigquery.SchemaField("download_error_msg", "STRING"),
        bigquery.SchemaField("resolution_score", "INT64"),
        bigquery.SchemaField("sharpness_score", "INT64"),
        bigquery.SchemaField("centration_score", "INT64"),
        bigquery.SchemaField("primary_object_label", "STRING"),
        bigquery.SchemaField("primary_object_confidence", "FLOAT64"),
        bigquery.SchemaField("safe_search_adult", "STRING"),
        bigquery.SchemaField("safe_search_violence", "STRING"),
        bigquery.SchemaField("vision_quality_score", "INT64"),
    ],
    "visual_embeddings": [
        bigquery.SchemaField("ean", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("run_date", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
        bigquery.SchemaField("embedding_model_name", "STRING"),
        bigquery.SchemaField("embedding_compute_time_ms", "INT64"),
    ],
    "product_scores": [
        bigquery.SchemaField("ean", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("run_date", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("text_score", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("visual_score", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("catalog_score", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("product_name", "STRING"),
        bigquery.SchemaField("categories", "STRING"),
        bigquery.SchemaField("image_url", "STRING"),
        bigquery.SchemaField("thumbnail_url_128", "STRING"),
        bigquery.SchemaField("thumbnail_url_256", "STRING"),
        bigquery.SchemaField("thumbnail_url_512", "STRING"),
        bigquery.SchemaField("has_anomaly_text", "BOOL"),
        bigquery.SchemaField("has_anomaly_visual", "BOOL"),
    ],
    "reports": [
        bigquery.SchemaField("report_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("report_date", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("executive_summary", "STRING"),
        bigquery.SchemaField("catalog_score", "INT64"),
        bigquery.SchemaField("text_score", "INT64"),
        bigquery.SchemaField("visual_score", "INT64"),
        bigquery.SchemaField("critical_issues", "JSON"),
        bigquery.SchemaField("worst_categories", "JSON"),
        bigquery.SchemaField("recommendations", "JSON"),
        bigquery.SchemaField("gemini_response_json", "STRING"),
    ],
}


def create_tables():
    for table_name, schema in SCHEMAS.items():
        table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"
        table = bigquery.Table(table_id, schema=schema)
        try:
            client.create_table(table)
            print(f"Created {table_name}")
        except Exception as e:
            print(f"Skipped {table_name}: {e}")
    print("Done.")


if __name__ == "__main__":
    create_tables()
