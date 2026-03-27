-- 02_text_profiling.sql
-- Compute text completeness metrics and Z-scores per pipeline run
-- Call this AFTER staging, passing the run_id as a parameter

DECLARE run_id STRING DEFAULT @run_id;
DECLARE run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP();
DECLARE total INT64;

SET total = (SELECT COUNT(*) FROM `prisme-wamba-2026.prisme_dataset.products_selected`);

-- Completeness metrics: % non-null per field
INSERT INTO `prisme-wamba-2026.prisme_dataset.text_metrics`
WITH raw_metrics AS (
  SELECT
    run_id                                                       AS run_id,
    run_date                                                     AS run_date,
    'completeness_product_name'                                  AS metric_name,
    ROUND(COUNTIF(product_name IS NOT NULL AND TRIM(product_name) != '') * 100.0 / total, 2) AS metric_value
  FROM `prisme-wamba-2026.prisme_dataset.products_selected`

  UNION ALL
  SELECT run_id, run_date, 'completeness_brands',
    ROUND(COUNTIF(brands IS NOT NULL AND TRIM(brands) != '') * 100.0 / total, 2)
  FROM `prisme-wamba-2026.prisme_dataset.products_selected`

  UNION ALL
  SELECT run_id, run_date, 'completeness_categories',
    ROUND(COUNTIF(categories IS NOT NULL AND TRIM(categories) != '') * 100.0 / total, 2)
  FROM `prisme-wamba-2026.prisme_dataset.products_selected`

  UNION ALL
  SELECT run_id, run_date, 'completeness_ingredients',
    ROUND(COUNTIF(ingredients_text IS NOT NULL AND TRIM(ingredients_text) != '') * 100.0 / total, 2)
  FROM `prisme-wamba-2026.prisme_dataset.products_selected`

  UNION ALL
  SELECT run_id, run_date, 'completeness_nutriscore',
    ROUND(COUNTIF(nutriscore_grade IS NOT NULL AND TRIM(nutriscore_grade) != '') * 100.0 / total, 2)
  FROM `prisme-wamba-2026.prisme_dataset.products_selected`

  UNION ALL
  SELECT run_id, run_date, 'completeness_quantity',
    ROUND(COUNTIF(quantity IS NOT NULL AND TRIM(quantity) != '') * 100.0 / total, 2)
  FROM `prisme-wamba-2026.prisme_dataset.products_selected`

  UNION ALL
  SELECT run_id, run_date, 'completeness_packaging',
    ROUND(COUNTIF(packaging IS NOT NULL AND TRIM(packaging) != '') * 100.0 / total, 2)
  FROM `prisme-wamba-2026.prisme_dataset.products_selected`

  UNION ALL
  -- Coherence: nutriscore should be present when ingredients are present
  SELECT run_id, run_date, 'coherence_nutriscore_with_ingredients',
    ROUND(
      COUNTIF(nutriscore_grade IS NOT NULL OR ingredients_text IS NULL) * 100.0 /
      NULLIF(COUNTIF(ingredients_text IS NOT NULL), 0),
      2
    )
  FROM `prisme-wamba-2026.prisme_dataset.products_selected`

  UNION ALL
  -- Avg length of product_name (aberrant if too short)
  SELECT run_id, run_date, 'avg_length_product_name',
    ROUND(AVG(LENGTH(product_name)), 2)
  FROM `prisme-wamba-2026.prisme_dataset.products_selected`
  WHERE product_name IS NOT NULL
),
history_stats AS (
  SELECT
    metric_name,
    AVG(metric_value) AS hist_mean,
    STDDEV(metric_value) AS hist_std
  FROM `prisme-wamba-2026.prisme_dataset.text_metrics`
  WHERE run_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY metric_name
)
SELECT
  m.run_id,
  m.run_date,
  m.metric_name,
  m.metric_value,
  CASE
    WHEN h.hist_std > 0 THEN ROUND((m.metric_value - h.hist_mean) / h.hist_std, 3)
    ELSE 0.0
  END AS z_score,
  CASE
    WHEN h.hist_std > 0 AND ABS((m.metric_value - h.hist_mean) / h.hist_std) > 2.5 THEN TRUE
    ELSE FALSE
  END AS is_anomaly
FROM raw_metrics m
LEFT JOIN history_stats h USING (metric_name);
