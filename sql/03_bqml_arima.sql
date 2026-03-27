-- 03_bqml_arima.sql
-- ARIMA_PLUS anomaly detection on text metric time series
-- NOTE: ARIMA_PLUS requires >= 20 historical data points.
-- On first runs, synthetic baseline data is injected (see below).
-- Remove the INSERT block after 30 real runs have accumulated.

-- ============================================================
-- BOOTSTRAP: inject 30 days of synthetic baseline (run once)
-- Comment out after real data accumulates
-- ============================================================
/*
INSERT INTO `prisme-wamba-2026.prisme_dataset.text_metrics`
SELECT
  CONCAT('bootstrap_', FORMAT_DATE('%Y%m%d', d)) AS run_id,
  TIMESTAMP(d) AS run_date,
  metric_name,
  metric_value + RAND() * 2 - 1 AS metric_value,  -- add small noise
  0.0 AS z_score,
  FALSE AS is_anomaly
FROM
  UNNEST(GENERATE_DATE_ARRAY(DATE_SUB(CURRENT_DATE(), INTERVAL 31 DAY), DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))) AS d
CROSS JOIN (
  SELECT metric_name, AVG(metric_value) AS metric_value
  FROM `prisme-wamba-2026.prisme_dataset.text_metrics`
  WHERE run_id NOT LIKE 'bootstrap_%'
  GROUP BY metric_name
);
*/

-- ============================================================
-- Train ARIMA_PLUS model on completeness_brands (representative)
-- ============================================================
CREATE OR REPLACE MODEL `prisme-wamba-2026.prisme_dataset.text_anomaly_model`
OPTIONS(
  model_type = 'ARIMA_PLUS',
  time_series_data_col = 'metric_value',
  time_series_timestamp_col = 'run_date',
  auto_arima = TRUE,
  data_frequency = 'DAILY',
  decompose_time_series = TRUE
) AS
SELECT
  run_date,
  metric_value
FROM `prisme-wamba-2026.prisme_dataset.text_metrics`
WHERE metric_name = 'completeness_brands'
ORDER BY run_date;

-- ============================================================
-- Detect anomalies and write to text_anomalies
-- ============================================================
INSERT INTO `prisme-wamba-2026.prisme_dataset.text_anomalies`
WITH anomaly_results AS (
  SELECT
    m.run_id,
    m.run_date,
    m.metric_name,
    m.metric_value                            AS observed_value,
    NULL                                      AS expected_value,
    NULL                                      AS confidence,
    m.z_score,
    m.is_anomaly
  FROM `prisme-wamba-2026.prisme_dataset.text_metrics` m
  WHERE m.is_anomaly = TRUE
    AND m.run_date = (SELECT MAX(run_date) FROM `prisme-wamba-2026.prisme_dataset.text_metrics`)
)
SELECT
  GENERATE_UUID()     AS anomaly_id,
  run_id,
  run_date,
  metric_name,
  CASE
    WHEN metric_name LIKE 'completeness_%' THEN 'COMPLETENESS_DROP'
    WHEN metric_name LIKE 'coherence_%' THEN 'COHERENCE_ISSUE'
    ELSE 'STATISTICAL_OUTLIER'
  END                 AS anomaly_type,
  expected_value,
  observed_value,
  confidence,
  z_score,
  CASE
    WHEN ABS(z_score) > 4 THEN 'CRITICAL'
    WHEN ABS(z_score) > 3 THEN 'HIGH'
    WHEN ABS(z_score) > 2.5 THEN 'MEDIUM'
    ELSE 'LOW'
  END                 AS severity,
  CONCAT(metric_name, ' deviated by Z=', ROUND(ABS(z_score), 2), ' from historical baseline') AS description
FROM anomaly_results;
