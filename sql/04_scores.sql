-- 04_scores.sql
-- Compute text_score per product and write to product_scores
-- Visual score columns are set to 0 here; updated by pipeline after visual audit
-- Run AFTER 02_text_profiling.sql

DECLARE run_id STRING DEFAULT @run_id;
DECLARE run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP();

INSERT INTO `prisme-wamba-2026.prisme_dataset.product_scores`
WITH field_weights AS (
  -- Weight per field for text_score
  SELECT 'product_name'   AS field, 30 AS weight UNION ALL
  SELECT 'brands',                              15 UNION ALL
  SELECT 'categories',                          20 UNION ALL
  SELECT 'ingredients_text',                    20 UNION ALL
  SELECT 'nutriscore_grade',                    10 UNION ALL
  SELECT 'quantity',                             3 UNION ALL
  SELECT 'packaging',                            2
),
per_product AS (
  SELECT
    p.ean,
    p.product_name,
    p.categories,
    p.image_url,
    -- text_score: sum of weights for non-null fields
    (
      CASE WHEN p.product_name IS NOT NULL AND TRIM(p.product_name) != '' THEN 30 ELSE 0 END +
      CASE WHEN p.brands IS NOT NULL AND TRIM(p.brands) != '' THEN 15 ELSE 0 END +
      CASE WHEN p.categories IS NOT NULL AND TRIM(p.categories) != '' THEN 20 ELSE 0 END +
      CASE WHEN p.ingredients_text IS NOT NULL AND TRIM(p.ingredients_text) != '' THEN 20 ELSE 0 END +
      CASE WHEN p.nutriscore_grade IS NOT NULL AND TRIM(p.nutriscore_grade) != '' THEN 10 ELSE 0 END +
      CASE WHEN p.quantity IS NOT NULL AND TRIM(p.quantity) != '' THEN 3 ELSE 0 END +
      CASE WHEN p.packaging IS NOT NULL AND TRIM(p.packaging) != '' THEN 2 ELSE 0 END
    ) AS text_score
  FROM `prisme-wamba-2026.prisme_dataset.products_selected` p
)
SELECT
  pp.ean,
  run_id,
  run_date,
  pp.text_score,
  0  AS visual_score,      -- updated by pipeline/scorer.py
  CAST(ROUND(0.6 * pp.text_score + 0.4 * 0) AS INT64) AS catalog_score,
  pp.product_name,
  pp.categories,
  pp.image_url,
  NULL AS thumbnail_url_128,
  NULL AS thumbnail_url_256,
  NULL AS thumbnail_url_512,
  FALSE AS has_anomaly_text,
  FALSE AS has_anomaly_visual
FROM per_product pp;
