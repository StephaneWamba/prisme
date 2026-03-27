# API Reference

Base URL: `https://prisme-api-765668196773.europe-west1.run.app`

All responses are JSON. No authentication required (internal use).

---

## Health

### GET /health

Liveness probe used by Cloud Run.

**Response**
```json
{ "status": "ok" }
```

---

## Catalog

### GET /catalog/health

Global score averages and 30-day evolution series.

**Response**
```json
{
  "health": {
    "avg_catalog": 62.2,
    "avg_text": 62.8,
    "avg_visual": 61.2,
    "n_products": 1000
  },
  "evolution": [
    { "run_date": "2026-03-27", "avg_catalog": 62.2, "avg_text": 62.8, "avg_visual": 61.2 }
  ]
}
```

### GET /catalog/categories

Category ranking sorted by average catalog score (ascending).

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max number of categories |

**Response**
```json
[
  { "category": "Veloutés de légumes", "avg_score": 78.4, "n_products": 12 },
  { "category": "Soupes", "avg_score": 71.1, "n_products": 8 }
]
```

---

## Products

### GET /products

Paginated product list with optional filters.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 30 | Items per page (max 100) |
| `min_score` | int | null | Minimum catalog_score |
| `max_score` | int | null | Maximum catalog_score |
| `category` | string | null | Category substring filter |

**Response**
```json
{
  "total": 1000,
  "page": 1,
  "per_page": 30,
  "items": [
    {
      "ean": "0000112302614",
      "product_name": "Fondue de poireaux st Jacques",
      "categories": "Soupes, Veloutés",
      "catalog_score": 58,
      "text_score": 52,
      "visual_score": 67,
      "thumbnail_url_128": "https://storage.googleapis.com/prisme-assets/thumbnails/128/0000112302614.jpg"
    }
  ]
}
```

### GET /products/{ean}

Full product detail with all score dimensions.

**Path params**

| Param | Type | Description |
|-------|------|-------------|
| `ean` | string | Product EAN barcode |

**Response**
```json
{
  "ean": "0000112302614",
  "product_name": "Fondue de poireaux st Jacques",
  "brands": "Liebig",
  "categories": "Soupes, Veloutés de légumes",
  "nutriscore_grade": "b",
  "quantity": "300 g",
  "packaging": "Brique",
  "catalog_score": 58,
  "text_score": 52,
  "visual_score": 67,
  "resolution_score": 72,
  "sharpness_score": 65,
  "centration_score": 70,
  "primary_object_label": "soup",
  "image_url": "https://...",
  "thumbnail_url_128": "https://storage.googleapis.com/prisme-assets/thumbnails/128/0000112302614.jpg",
  "thumbnail_url_256": "https://storage.googleapis.com/prisme-assets/thumbnails/256/0000112302614.jpg",
  "thumbnail_url_512": "https://storage.googleapis.com/prisme-assets/thumbnails/512/0000112302614.jpg"
}
```

**Errors**

| Code | Reason |
|------|--------|
| 404 | EAN not found in dataset |

### POST /products/audit

On-demand audit for a single product. Returns all score sub-components.

**Body**
```json
{ "ean": "0000112302614" }
```

**Response**
```json
{
  "ean": "0000112302614",
  "product": { "...": "full product object" },
  "audit": {
    "text_score": 52,
    "visual_score": 67,
    "catalog_score": 58,
    "resolution": 72,
    "sharpness": 65,
    "centration": 70,
    "object_label": "soup"
  }
}
```

---

## Anomalies

### GET /anomalies

Detected anomalies from the last 7 days, sorted by severity.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | null | Metric name filter (e.g. `completeness_brands`) |
| `severity` | string | null | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `limit` | int | 50 | Max results |

**Response**
```json
[
  {
    "metric_name": "completeness_brands",
    "severity": "HIGH",
    "description": "Brand completeness dropped to 61.2% (z=-2.8, expected ~78%)",
    "run_date": "2026-03-27T10:00:00Z"
  }
]
```

---

## Reports

### GET /reports/latest

Latest Gemini AI daily report.

**Response**
```json
{
  "report_id": "uuid",
  "report_date": "2026-03-27",
  "executive_summary": "Le catalogue presente une qualite moderee...",
  "catalog_score": 62,
  "text_score": 62,
  "visual_score": 61,
  "critical_issues": ["Qualite insuffisante (62/100)", "Categories degradees"],
  "worst_categories": ["Creme de Leite bovino", "En:hot sauces", "Cabbages"],
  "recommendations": [
    "Plan d'action prioritaire pour les categories degradees",
    "Corriger la taxonomie des categories sans nom",
    "Campagne d'enrichissement texte et visuel"
  ]
}
```

**Errors**

| Code | Reason |
|------|--------|
| 404 | No report in BQ yet |

---

## Visual Search

### POST /search/visual

Find visually similar products using CLIP embeddings stored in BigQuery.

**Body**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `image_url` | string | yes | | Public URL of the query image |
| `top_k` | int | no | 10 | Number of results |

**Body example**
```json
{
  "image_url": "https://storage.googleapis.com/prisme-assets/thumbnails/128/0000112302614.jpg",
  "top_k": 10
}
```

**Response**
```json
[
  {
    "ean": "0000112302614",
    "distance": 0.234,
    "product_name": "Fondue de poireaux st Jacques",
    "categories": "",
    "thumbnail_url": "https://storage.googleapis.com/prisme-assets/thumbnails/128/0000112302614.jpg",
    "catalog_score": 58
  }
]
```

The `distance` is cosine distance (0 = identical, 1 = completely different). Similarity percentage displayed in the UI = `(1 - distance) * 100`.

**Errors**

| Code | Reason |
|------|--------|
| 400 | Image URL unreachable or not decodable as RGB |

---

## Quality

### GET /quality/coverage

Percentage of products with at least one image.

### GET /quality/fields

Completeness rate per metadata field across the full catalogue.

**Response**
```json
[
  { "field": "product_name", "completeness": 96.4 },
  { "field": "brands", "completeness": 78.1 },
  { "field": "categories", "completeness": 82.3 },
  { "field": "nutriscore_grade", "completeness": 41.7 }
]
```
