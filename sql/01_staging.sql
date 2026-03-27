-- 01_staging.sql
-- Extract top-50 products per category from Open Food Facts (France, image non-null)
-- Result: ~10 000 products, representative sample across categories

INSERT INTO `prisme-wamba-2026.prisme_dataset.products_selected`
WITH ranked AS (
  SELECT
    COALESCE(code, CAST(FARM_FINGERPRINT(product_name) AS STRING)) AS ean,
    product_name,
    brands,
    categories,
    ingredients_text,
    nutriscore_grade,
    quantity,
    packaging,
    image_url,
    image_small_url,
    'FR'                                AS country_code,
    TIMESTAMP_SECONDS(last_modified_t)  AS last_modified_t,
    ROW_NUMBER() OVER (
      PARTITION BY SPLIT(LOWER(TRIM(categories)), ',')[SAFE_OFFSET(0)]
      ORDER BY last_modified_t DESC
    ) AS rn
  FROM `bigquery-public-data.open_food_facts.products`
  WHERE
    countries LIKE '%France%'
    AND image_url IS NOT NULL
    AND TRIM(image_url) != ''
    AND TRIM(COALESCE(product_name, '')) != ''
)
SELECT
  ean,
  product_name,
  brands,
  categories,
  ingredients_text,
  nutriscore_grade,
  quantity,
  packaging,
  image_url,
  image_small_url,
  country_code,
  last_modified_t,
  CURRENT_TIMESTAMP() AS ingestion_timestamp
FROM ranked
WHERE rn <= 50;
