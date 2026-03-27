"""BigQuery service with TTL cache."""
import time
from typing import Any

from google.cloud import bigquery

from config import PROJECT_ID, DATASET, CACHE_TTL_SECONDS

_client: bigquery.Client | None = None
_cache: dict[str, tuple[Any, float]] = {}


def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT_ID)
    return _client


def _cached(key: str, fn):
    now = time.time()
    if key in _cache and now - _cache[key][1] < CACHE_TTL_SECONDS:
        return _cache[key][0]
    result = fn()
    _cache[key] = (result, now)
    return result


def query(sql: str, params: list | None = None) -> list[dict]:
    client = get_client()
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    rows = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]


def query_cached(key: str, sql: str, params: list | None = None) -> list[dict]:
    return _cached(key, lambda: query(sql, params))


def table(name: str) -> str:
    return f"`{PROJECT_ID}.{DATASET}.{name}`"


def latest_run_date() -> str:
    rows = query(f"SELECT MAX(run_date) AS max_run FROM {table('product_scores')}")
    return rows[0]["max_run"] if rows else None


# --- Catalog ---

def get_catalog_health() -> dict:
    def _fetch():
        rows = query(f"""
            SELECT
              ROUND(AVG(catalog_score), 1) AS catalog_score,
              ROUND(AVG(text_score), 1)    AS text_score,
              ROUND(AVG(visual_score), 1)  AS visual_score,
              COUNT(*)                     AS product_count
            FROM {table('product_scores')}
            WHERE run_date = (SELECT MAX(run_date) FROM {table('product_scores')})
        """)
        return rows[0] if rows else {}
    return _cached("catalog_health", _fetch)


def get_score_evolution() -> list[dict]:
    def _fetch():
        return query(f"""
            SELECT
              FORMAT_TIMESTAMP('%Y-%m-%d', run_date) AS date,
              ROUND(AVG(catalog_score), 1) AS catalog_score,
              ROUND(AVG(text_score), 1)    AS text_score,
              ROUND(AVG(visual_score), 1)  AS visual_score
            FROM {table('product_scores')}
            WHERE run_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            GROUP BY date
            ORDER BY date
        """)
    return _cached("score_evolution", _fetch)


def get_categories(limit: int = 50) -> list[dict]:
    def _fetch():
        return query(f"""
            WITH latest AS (SELECT MAX(run_date) AS max_run FROM {table('product_scores')})
            SELECT
              TRIM(SPLIT(categories, ',')[SAFE_OFFSET(0)]) AS category,
              ROUND(AVG(catalog_score), 1) AS avg_catalog_score,
              ROUND(AVG(text_score), 1)    AS avg_text_score,
              ROUND(AVG(visual_score), 1)  AS avg_visual_score,
              COUNT(*)                     AS product_count
            FROM {table('product_scores')}
            WHERE run_date = (SELECT max_run FROM latest)
              AND categories IS NOT NULL
            GROUP BY category
            ORDER BY avg_catalog_score ASC
            LIMIT {limit}
        """)
    return _cached(f"categories_{limit}", _fetch)


# --- Products ---

def get_products(
    page: int = 1,
    per_page: int = 30,
    min_score: int | None = None,
    max_score: int | None = None,
    category: str | None = None,
) -> dict:
    offset = (page - 1) * per_page
    filters = ["run_date = (SELECT MAX(run_date) FROM `prisme-wamba-2026.prisme_dataset.product_scores`)"]
    if min_score is not None:
        filters.append(f"catalog_score >= {min_score}")
    if max_score is not None:
        filters.append(f"catalog_score <= {max_score}")
    if category:
        filters.append(f"LOWER(categories) LIKE LOWER('%{category}%')")

    where = " AND ".join(filters)
    rows = query(f"""
        SELECT ean, product_name, categories, catalog_score, text_score, visual_score,
               thumbnail_url_128, has_anomaly_text, has_anomaly_visual
        FROM {table('product_scores')}
        WHERE {where}
        ORDER BY catalog_score ASC
        LIMIT {per_page} OFFSET {offset}
    """)
    count_rows = query(f"SELECT COUNT(*) AS n FROM {table('product_scores')} WHERE {where}")
    total = count_rows[0]["n"] if count_rows else 0
    return {"items": rows, "total": total, "page": page, "per_page": per_page}


def get_product_detail(ean: str) -> dict | None:
    rows = query(f"""
        SELECT ps.*, vd.primary_object_label, vd.resolution_score, vd.sharpness_score,
               vd.centration_score, vd.safe_search_adult, vd.image_width_px, vd.image_height_px
        FROM {table('product_scores')} ps
        LEFT JOIN {table('visual_detections')} vd ON ps.ean = vd.ean AND DATE(ps.run_date) = DATE(vd.run_date)
        WHERE ps.ean = @ean
        ORDER BY ps.run_date DESC
        LIMIT 1
    """, [bigquery.ScalarQueryParameter("ean", "STRING", ean)])
    return rows[0] if rows else None


# --- Anomalies ---

def get_anomalies(type_filter: str | None = None, severity: str | None = None, limit: int = 50) -> list[dict]:
    filters = ["run_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)"]
    if severity:
        filters.append(f"severity = '{severity}'")
    if type_filter and type_filter != "all":
        filters.append(f"anomaly_type LIKE '%{type_filter.upper()}%'")
    where = " AND ".join(filters)
    return query(f"""
        SELECT * FROM {table('text_anomalies')}
        WHERE {where}
        ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END
        LIMIT {limit}
    """)


# --- Reports ---

def get_latest_report() -> dict | None:
    rows = query(f"SELECT * FROM {table('reports')} ORDER BY report_date DESC LIMIT 1")
    return rows[0] if rows else None


# --- Visual search ---

def vector_search(embedding: list[float], top_k: int = 10) -> list[dict]:
    import json
    emb_json = json.dumps(embedding)
    return query(f"""
        SELECT ean, COSINE_DISTANCE(embedding, {emb_json}) AS distance
        FROM {table('visual_embeddings')}
        WHERE DATE(run_date) = CURRENT_DATE()
        ORDER BY distance ASC
        LIMIT {top_k}
    """)


# --- Quality coverage ---

def get_quality_coverage() -> dict:
    def _fetch():
        rows = query(f"""
            WITH latest AS (SELECT MAX(run_date) AS max_run FROM {table('product_scores')})
            SELECT
              COUNT(*) AS total,
              COUNTIF(image_url IS NOT NULL) AS has_image_url,
              COUNTIF(thumbnail_url_128 IS NOT NULL) AS has_thumbnail,
              COUNTIF(thumbnail_url_128 IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) AS thumbnail_pct
            FROM {table('product_scores')}
            WHERE run_date = (SELECT max_run FROM latest)
        """)
        return rows[0] if rows else {}
    return _cached("quality_coverage", _fetch)


def get_field_completeness() -> list[dict]:
    def _fetch():
        return query(f"""
            SELECT metric_name, metric_value
            FROM {table('text_metrics')}
            WHERE run_date = (SELECT MAX(run_date) FROM {table('text_metrics')})
              AND metric_name LIKE 'completeness_%'
            ORDER BY metric_value ASC
        """)
    return _cached("field_completeness", _fetch)
