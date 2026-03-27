-- 05_looker_views.sql
-- BigQuery views for Looker Studio dashboard
-- Connect Looker Studio to these views (not the raw tables)

-- View 1: Latest catalog health KPIs
CREATE OR REPLACE VIEW `prisme-wamba-2026.prisme_dataset.v_catalog_health` AS
SELECT
  run_id,
  run_date,
  ROUND(AVG(catalog_score), 1) AS avg_catalog_score,
  ROUND(AVG(text_score), 1)    AS avg_text_score,
  ROUND(AVG(visual_score), 1)  AS avg_visual_score,
  COUNT(*)                     AS product_count
FROM `prisme-wamba-2026.prisme_dataset.product_scores`
GROUP BY run_id, run_date
ORDER BY run_date DESC;

-- View 2: Category ranking by catalog_score (latest run)
CREATE OR REPLACE VIEW `prisme-wamba-2026.prisme_dataset.v_category_ranking` AS
WITH latest_run AS (
  SELECT MAX(run_date) AS max_run FROM `prisme-wamba-2026.prisme_dataset.product_scores`
)
SELECT
  TRIM(SPLIT(categories, ',')[SAFE_OFFSET(0)]) AS category,
  ROUND(AVG(catalog_score), 1)  AS avg_catalog_score,
  ROUND(AVG(text_score), 1)     AS avg_text_score,
  ROUND(AVG(visual_score), 1)   AS avg_visual_score,
  COUNT(*)                      AS product_count,
  COUNTIF(has_anomaly_text OR has_anomaly_visual) AS anomaly_count
FROM `prisme-wamba-2026.prisme_dataset.product_scores`
WHERE run_date = (SELECT max_run FROM latest_run)
GROUP BY category
ORDER BY avg_catalog_score ASC;

-- View 3: Anomaly distribution by severity and type (latest run)
CREATE OR REPLACE VIEW `prisme-wamba-2026.prisme_dataset.v_anomaly_distribution` AS
SELECT
  severity,
  anomaly_type,
  COUNT(*) AS count
FROM `prisme-wamba-2026.prisme_dataset.text_anomalies`
WHERE run_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY severity, anomaly_type
ORDER BY
  CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END;

-- View 4: Score evolution over 30 days
CREATE OR REPLACE VIEW `prisme-wamba-2026.prisme_dataset.v_score_evolution` AS
SELECT
  DATE(run_date) AS run_day,
  ROUND(AVG(catalog_score), 1) AS avg_catalog_score,
  ROUND(AVG(text_score), 1)    AS avg_text_score,
  ROUND(AVG(visual_score), 1)  AS avg_visual_score
FROM `prisme-wamba-2026.prisme_dataset.product_scores`
WHERE run_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY run_day
ORDER BY run_day;

-- View 5: Asset coverage (image valid / thumbnail / CLIP encoded)
CREATE OR REPLACE VIEW `prisme-wamba-2026.prisme_dataset.v_asset_coverage` AS
WITH latest_run AS (
  SELECT MAX(run_date) AS max_run FROM `prisme-wamba-2026.prisme_dataset.product_scores`
)
SELECT
  COUNT(*)                                                           AS total_products,
  COUNTIF(image_url IS NOT NULL)                                     AS has_image_url,
  COUNTIF(thumbnail_url_128 IS NOT NULL)                             AS has_thumbnail,
  COUNTIF(thumbnail_url_128 IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) AS thumbnail_coverage_pct
FROM `prisme-wamba-2026.prisme_dataset.product_scores`
WHERE run_date = (SELECT max_run FROM latest_run);

-- View 6: Top 20 worst products
CREATE OR REPLACE VIEW `prisme-wamba-2026.prisme_dataset.v_worst_products` AS
WITH latest_run AS (
  SELECT MAX(run_date) AS max_run FROM `prisme-wamba-2026.prisme_dataset.product_scores`
)
SELECT
  ean,
  product_name,
  categories,
  catalog_score,
  text_score,
  visual_score,
  has_anomaly_text,
  has_anomaly_visual,
  thumbnail_url_128
FROM `prisme-wamba-2026.prisme_dataset.product_scores`
WHERE run_date = (SELECT max_run FROM latest_run)
ORDER BY catalog_score ASC
LIMIT 20;
