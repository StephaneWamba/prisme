# Prisme Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-stack GCP catalogue quality audit platform (text + visual) on Open Food Facts (~10k products), deployed on Cloud Run + Vercel, ready for a Davidson Consulting interview demo.

**Architecture:** BigQuery public dataset -> pipeline Cloud Run Job (text profiling + ARIMA_PLUS + CLIP + Cloud Vision) -> FastAPI Cloud Run Service -> Next.js Vercel frontend. One pipeline job covers all 10k products in under 1 hour.

**Tech Stack:** Python 3.11, FastAPI, BigQuery ML, Cloud Vision API, CLIP (HuggingFace CPU-only), Vertex AI Gemini 1.5 Flash, Next.js 14, Tailwind CSS v4, Framer Motion, Recharts, GCP Cloud Run, Vercel, GitHub Actions + WIF.

**Design doc:** `docs/plans/2026-03-26-prisme-design.md`

---

## PHASE 1 - GCP Infrastructure

### Task 1: GCP project setup + enable APIs

**Files:**
- Create: `infra/setup.sh`

**Step 1: Write setup.sh**

```bash
#!/bin/bash
set -e

PROJECT_ID="prisme-wamba-2026"
REGION="europe-west1"

gcloud config set project $PROJECT_ID

echo "Enabling APIs..."
gcloud services enable \
  cloudrun.googleapis.com \
  artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  storage-api.googleapis.com \
  vision.googleapis.com \
  aiplatform.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  containerregistry.googleapis.com

echo "Creating Artifact Registry..."
gcloud artifacts repositories create prisme-docker \
  --repository-format=docker \
  --location=$REGION || true

echo "Creating GCS bucket..."
gsutil mb -b on -l $REGION gs://prisme-assets || true

echo "Creating BQ dataset..."
bq mk --location=$REGION --dataset $PROJECT_ID:prisme_dataset || true

echo "Done."
```

**Step 2: Run**
```bash
chmod +x infra/setup.sh && ./infra/setup.sh
```
Expected: all APIs enabled, resources created.

**Step 3: Commit**
```bash
git add infra/setup.sh
git commit -m "infra: GCP project setup script"
```

---

### Task 2: Service accounts + Workload Identity Federation

**Files:**
- Create: `infra/iam.sh`

**Step 1: Write iam.sh**

```bash
#!/bin/bash
set -e

PROJECT_ID="prisme-wamba-2026"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
GITHUB_ORG="StephaneWamba"
GITHUB_REPO="prisme"

echo "Creating service accounts..."
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer" --project=$PROJECT_ID || true

gcloud iam service-accounts create prisme-cloud-run \
  --display-name="Prisme Cloud Run Runtime" --project=$PROJECT_ID || true

echo "Deployer roles..."
for role in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
    --role=$role
done

echo "Runtime roles..."
for role in roles/bigquery.dataViewer roles/bigquery.jobUser roles/secretmanager.secretAccessor \
            roles/storage.objectAdmin roles/logging.logWriter roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:prisme-cloud-run@$PROJECT_ID.iam.gserviceaccount.com" \
    --role=$role
done

echo "Setting up WIF..."
gcloud iam workload-identity-pools create github-pool \
  --location=global --display-name="GitHub WIF Pool" --project=$PROJECT_ID || true

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --project=$PROJECT_ID || true

gcloud iam service-accounts add-iam-policy-binding \
  github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/$GITHUB_ORG/$GITHUB_REPO"

WIF_PROVIDER="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo ""
echo "Add to GitHub Secrets:"
echo "WIF_PROVIDER=$WIF_PROVIDER"
echo "WIF_SERVICE_ACCOUNT=github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com"
```

**Step 2: Run**
```bash
chmod +x infra/iam.sh && ./infra/iam.sh
```
Copy the WIF_PROVIDER and WIF_SERVICE_ACCOUNT values to GitHub Secrets.

**Step 3: Commit**
```bash
git add infra/iam.sh
git commit -m "infra: service accounts and WIF setup"
```

---

### Task 3: BigQuery tables DDL

**Files:**
- Create: `infra/create_bq_tables.py`

**Step 1: Write create_bq_tables.py**

```python
"""Create all BigQuery tables for Prisme dataset."""
from google.cloud import bigquery

PROJECT_ID = "prisme-wamba-2026"
DATASET = "prisme_dataset"
client = bigquery.Client(project=PROJECT_ID)

TABLES = {
    "products_selected": """
        ean STRING NOT NULL,
        product_name STRING,
        brands STRING,
        categories STRING,
        ingredients_text STRING,
        nutriscore_grade STRING,
        quantity STRING,
        packaging STRING,
        image_url STRING NOT NULL,
        image_small_url STRING,
        country_code STRING,
        last_modified_t TIMESTAMP,
        ingestion_timestamp TIMESTAMP NOT NULL
    """,
    "text_metrics": """
        run_id STRING NOT NULL,
        run_date TIMESTAMP NOT NULL,
        metric_name STRING NOT NULL,
        metric_value FLOAT64 NOT NULL,
        z_score FLOAT64,
        is_anomaly BOOL
    """,
    "text_anomalies": """
        anomaly_id STRING NOT NULL,
        run_id STRING NOT NULL,
        run_date TIMESTAMP NOT NULL,
        metric_name STRING NOT NULL,
        anomaly_type STRING,
        expected_value FLOAT64,
        observed_value FLOAT64,
        confidence FLOAT64,
        z_score FLOAT64,
        severity STRING NOT NULL,
        description STRING
    """,
    "visual_detections": """
        ean STRING NOT NULL,
        run_id STRING NOT NULL,
        run_date TIMESTAMP NOT NULL,
        image_url STRING,
        image_width_px INT64,
        image_height_px INT64,
        image_size_kb FLOAT64,
        download_success BOOL,
        download_error_msg STRING,
        resolution_score INT64,
        sharpness_score INT64,
        centration_score INT64,
        primary_object_label STRING,
        primary_object_confidence FLOAT64,
        safe_search_adult STRING,
        safe_search_violence STRING,
        vision_quality_score INT64
    """,
    "visual_embeddings": """
        ean STRING NOT NULL,
        run_id STRING NOT NULL,
        run_date TIMESTAMP NOT NULL,
        embedding ARRAY<FLOAT64>,
        embedding_model_name STRING,
        embedding_compute_time_ms INT64
    """,
    "product_scores": """
        ean STRING NOT NULL,
        run_id STRING NOT NULL,
        run_date TIMESTAMP NOT NULL,
        text_score INT64 NOT NULL,
        visual_score INT64 NOT NULL,
        catalog_score INT64 NOT NULL,
        product_name STRING,
        categories STRING,
        image_url STRING,
        thumbnail_url_128 STRING,
        thumbnail_url_256 STRING,
        thumbnail_url_512 STRING,
        has_anomaly_text BOOL,
        has_anomaly_visual BOOL
    """,
    "reports": """
        report_id STRING NOT NULL,
        report_date TIMESTAMP NOT NULL,
        executive_summary STRING,
        catalog_score INT64,
        text_score INT64,
        visual_score INT64,
        critical_issues JSON,
        worst_categories JSON,
        recommendations JSON,
        gemini_response_json STRING
    """,
}

for table_name, schema_str in TABLES.items():
    table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"
    schema = [
        bigquery.SchemaField(
            field.strip().split()[0],
            " ".join(field.strip().split()[1:]).split("NOT NULL")[0].strip(),
        )
        for field in schema_str.strip().split(",\n")
        if field.strip()
    ]
    table = bigquery.Table(table_id)
    try:
        client.create_table(table)
        print(f"Created {table_name}")
    except Exception as e:
        print(f"Skipped {table_name}: {e}")

print("Done.")
```

**Step 2: Run**
```bash
pip install google-cloud-bigquery
python infra/create_bq_tables.py
```

**Step 3: Commit**
```bash
git add infra/create_bq_tables.py
git commit -m "infra: BigQuery DDL script"
```

---

## PHASE 2 - SQL Files

### Task 4: SQL 01 - Staging

**Files:**
- Create: `sql/01_staging.sql`

```sql
-- 01_staging.sql
-- Charge ~10k produits depuis Open Food Facts public dataset
-- Top 50 produits par categorie, France uniquement, image_url non nulle

CREATE OR REPLACE TABLE `prisme-wamba-2026.prisme_dataset.products_selected`
PARTITION BY DATE(ingestion_timestamp) AS

WITH ranked AS (
  SELECT
    code AS ean,
    TRIM(LOWER(product_name)) AS product_name,
    TRIM(LOWER(brands)) AS brands,
    TRIM(LOWER(categories)) AS categories,
    ingredients_text,
    UPPER(nutriscore_grade) AS nutriscore_grade,
    TRIM(quantity) AS quantity,
    TRIM(packaging) AS packaging,
    image_url,
    image_small_url,
    CASE WHEN countries LIKE '%France%' THEN 'FR' ELSE NULL END AS country_code,
    last_modified_t,
    CURRENT_TIMESTAMP() AS ingestion_timestamp,
    ROW_NUMBER() OVER (
      PARTITION BY SPLIT(TRIM(LOWER(categories)), ',')[SAFE_OFFSET(0)]
      ORDER BY last_modified_t DESC NULLS LAST
    ) AS rn
  FROM `bigquery-public-data.open_food_facts.products`
  WHERE countries LIKE '%France%'
    AND image_url IS NOT NULL
    AND TRIM(image_url) != ''
    AND TRIM(product_name) IS NOT NULL
    AND CHAR_LENGTH(TRIM(product_name)) > 0
    AND CHAR_LENGTH(code) >= 8
)

SELECT * EXCEPT(rn) FROM ranked WHERE rn <= 50;
```

Validate after run:
```sql
SELECT COUNT(*), COUNT(DISTINCT categories) FROM `prisme-wamba-2026.prisme_dataset.products_selected`;
-- Expected: ~8000-12000 rows, ~200 categories
```

**Commit:**
```bash
git add sql/01_staging.sql
git commit -m "sql: Open Food Facts staging query"
```

---

### Task 5: SQL 02 - Text profiling

**Files:**
- Create: `sql/02_text_profiling.sql`

Key metrics to compute per run:
- `completeness_product_name`, `completeness_brands`, `completeness_categories`, `completeness_ingredients`, `completeness_nutriscore`
- `avg_length_product_name`, `avg_length_ingredients`
- `consistency_nutriscore_vs_ingredients`
- `duplicate_pct_name_brand`

Insert into `text_metrics` with `run_id` (UUID passed as param from Python).

**Commit:**
```bash
git add sql/02_text_profiling.sql
git commit -m "sql: text profiling metrics"
```

---

### Task 6: SQL 03 - BQML ARIMA + anomaly detection

**Files:**
- Create: `sql/03_bqml_arima.sql`

```sql
-- 03_bqml_arima.sql
-- PHASE 1: Creer modele ARIMA_PLUS (ou remplacer si existant)
-- Necessite >= 20 points dans text_metrics. En DEV: utiliser WITH synthetic_baseline AS (...)

CREATE OR REPLACE MODEL `prisme-wamba-2026.prisme_dataset.arima_text_model`
OPTIONS(
  model_type='ARIMA_PLUS',
  time_series_timestamp_col='run_date',
  time_series_data_col='metric_value',
  time_series_id_col='metric_name',
  auto_arima=TRUE,
  data_frequency='DAY'
) AS
SELECT run_date, metric_value, metric_name
FROM `prisme-wamba-2026.prisme_dataset.text_metrics`
WHERE metric_name IN (
  'completeness_product_name','completeness_brands','completeness_categories',
  'completeness_ingredients','completeness_nutriscore'
)
ORDER BY metric_name, run_date;

-- PHASE 2: Detecter anomalies (executer quotidiennement via anomaly_detector.py)
-- ML.DETECT_ANOMALIES est appele depuis Python, pas en SQL standalone
```

**Commit:**
```bash
git add sql/03_bqml_arima.sql
git commit -m "sql: BQML ARIMA_PLUS model definition"
```

---

### Task 7: SQL 04 + 05 - Scores et vues Looker

**Files:**
- Create: `sql/04_scores.sql`
- Create: `sql/05_looker_views.sql`

`04_scores.sql`: fusionne text_metrics + visual_detections -> product_scores (0.6 text + 0.4 visual).

`05_looker_views.sql`: 5 vues pour Looker Studio:
- `v_kpi_daily` - KPIs journaliers
- `v_categories_ranked` - classement rayons
- `v_text_anomalies_by_severity` - distribution anomalies
- `v_coverage_metrics` - taux couverture assets
- `v_worst_products` - top 20 produits pires scores

**Commit:**
```bash
git add sql/04_scores.sql sql/05_looker_views.sql
git commit -m "sql: fusion scores et vues Looker"
```

---

## PHASE 3 - Pipeline Python

### Task 8: Pipeline config + requirements

**Files:**
- Create: `pipeline/config.py`
- Create: `pipeline/requirements.txt`

```python
# pipeline/config.py
import os

PROJECT_ID = os.environ.get("PROJECT_ID", "prisme-wamba-2026")
BQ_DATASET = os.environ.get("BQ_DATASET", "prisme_dataset")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "prisme-assets")
REGION = os.environ.get("REGION", "europe-west1")
CLIP_MODEL = "openai/clip-vit-base-patch32"
VISION_API_KEY = os.environ.get("VISION_API_KEY")  # from Secret Manager

DOWNLOAD_BATCH_SIZE = 5000
DOWNLOAD_CONCURRENT = 64
DOWNLOAD_TIMEOUT = 30
DOWNLOAD_RETRY_MAX = 3

CLIP_BATCH_SIZE = 32
CLIP_CHECKPOINT_EVERY = 320  # images avant flush BQ

THUMBNAIL_SIZES = [128, 256, 512]
SIGNED_URL_EXPIRY_DAYS = 30
```

```text
# pipeline/requirements.txt
google-cloud-bigquery==3.17.0
google-cloud-storage==2.15.0
google-cloud-vision==3.7.0
google-cloud-aiplatform==1.43.0
aiohttp==3.9.3
torch==2.1.2+cpu --extra-index-url https://download.pytorch.org/whl/cpu
transformers==4.38.0
Pillow==10.2.0
opencv-python-headless==4.9.0.80
numpy==1.26.4
pandas==2.2.0
```

**Commit:**
```bash
git add pipeline/config.py pipeline/requirements.txt
git commit -m "pipeline: config and dependencies"
```

---

### Task 9: Downloader

**Files:**
- Create: `pipeline/downloader.py`

Key implementation:
```python
# pipeline/downloader.py
import asyncio, aiohttp
from google.cloud import storage, bigquery
from PIL import Image
from io import BytesIO
from pipeline.config import *

async def download_image(session, ean, url, retry=0):
    """Download image, validate (magic bytes + min 5KB + PIL decode), upload to GCS."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.read()
                if len(data) < 5_000:
                    return (ean, None, resp.status, False, "too_small")
                if data[:2] not in (b'\xff\xd8', b'\x89P'):
                    return (ean, None, resp.status, False, "bad_magic")
                try:
                    img = Image.open(BytesIO(data))
                    img.load()
                except Exception:
                    return (ean, None, resp.status, False, "pil_fail")
                gcs_path = f"originals/{ean}.jpg"
                _upload_to_gcs(gcs_path, data)
                return (ean, gcs_path, 200, True, "ok")
            elif resp.status == 404:
                return (ean, None, 404, False, "not_found")
            else:
                if retry < DOWNLOAD_RETRY_MAX:
                    await asyncio.sleep([1, 2, 4][retry])
                    return await download_image(session, ean, url, retry + 1)
                return (ean, None, resp.status, False, "server_error")
    except asyncio.TimeoutError:
        if retry < DOWNLOAD_RETRY_MAX:
            await asyncio.sleep([1, 2, 4][retry])
            return await download_image(session, ean, url, retry + 1)
        return (ean, None, 0, False, "timeout")

def _upload_to_gcs(path, data):
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(path)
    blob.upload_from_string(data, content_type="image/jpeg")

async def download_all(product_map: dict) -> dict:
    """Download all images. Returns {ean: (gcs_path, success)}."""
    connector = aiohttp.TCPConnector(limit=DOWNLOAD_CONCURRENT, limit_per_host=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            download_image(session, ean, row["image_url"])
            for ean, row in product_map.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        r[0]: {"gcs_path": r[1], "success": r[3], "error": r[4]}
        for r in results if not isinstance(r, Exception)
    }
```

**Commit:**
```bash
git add pipeline/downloader.py
git commit -m "pipeline: async image downloader"
```

---

### Task 10: Thumbnailer + Visual scorer

**Files:**
- Create: `pipeline/thumbnailer.py`
- Create: `pipeline/visual_scorer.py`

`thumbnailer.py`: Pillow resize to 3 formats (128, 256, 512), upload to GCS `thumbnails/{size}/{ean}.jpg`, generate signed URLs (30d), store in BigQuery `product_scores`.

`visual_scorer.py`:
```python
import cv2, numpy as np
from PIL import Image

def score_sharpness(img_bytes: bytes) -> int:
    """Laplacian variance -> 0-100 score. < 100 = blurry."""
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0
    variance = cv2.Laplacian(img, cv2.CV_64F).var()
    return min(100, int(variance / 10))

def score_resolution(width, height) -> int:
    """< 300x300 = low. 300-600 = medium. > 600 = high."""
    min_dim = min(width, height)
    if min_dim < 200: return 20
    if min_dim < 300: return 50
    if min_dim < 500: return 75
    return 100
```

**Commit:**
```bash
git add pipeline/thumbnailer.py pipeline/visual_scorer.py
git commit -m "pipeline: thumbnails and visual scoring"
```

---

### Task 11: Cloud Vision API

**Files:**
- Create: `pipeline/vision.py`

```python
# pipeline/vision.py
import os, json
from google.cloud import vision
from pipeline.config import VISION_API_KEY

def get_vision_client():
    if VISION_API_KEY:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(
            json.loads(VISION_API_KEY)
        )
        return vision.ImageAnnotatorClient(credentials=creds)
    return vision.ImageAnnotatorClient()

async def detect_batch(ean_path_map: dict) -> dict:
    """
    Runs Object Localization + Label Detection on batches of 16 images.
    Returns {ean: {labels, centration_score, vision_quality_score}}.
    """
    client = get_vision_client()
    results = {}
    eans = list(ean_path_map.keys())
    for i in range(0, len(eans), 16):
        batch = eans[i:i+16]
        requests = []
        for ean in batch:
            gcs_uri = f"gs://{GCS_BUCKET}/{ean_path_map[ean]}"
            requests.append({
                "image": {"source": {"gcs_image_uri": gcs_uri}},
                "features": [
                    {"type_": vision.Feature.Type.LABEL_DETECTION, "max_results": 5},
                    {"type_": vision.Feature.Type.OBJECT_LOCALIZATION, "max_results": 1},
                    {"type_": vision.Feature.Type.SAFE_SEARCH_DETECTION},
                ]
            })
        response = client.batch_annotate_images({"requests": requests})
        for ean, resp in zip(batch, response.responses):
            labels = [{"label": l.description, "confidence": l.score}
                      for l in resp.label_annotations]
            objects = resp.localized_object_annotations
            centration = int(objects[0].score * 100) if objects else 50
            safe = resp.safe_search_annotation
            results[ean] = {
                "labels": labels,
                "centration_score": centration,
                "safe_search_adult": str(safe.adult.name) if safe else "VERY_UNLIKELY",
                "safe_search_violence": str(safe.violence.name) if safe else "VERY_UNLIKELY",
            }
    return results
```

**Commit:**
```bash
git add pipeline/vision.py
git commit -m "pipeline: Cloud Vision API integration"
```

---

### Task 12: CLIP encoder

**Files:**
- Create: `pipeline/encoder.py`

```python
# pipeline/encoder.py
import gc, torch, numpy as np
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from io import BytesIO
from google.cloud import storage
from pipeline.config import *

class CLIPEncoder:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.device = "cpu"
        self.model = CLIPModel.from_pretrained(CLIP_MODEL)
        self.model.eval()
        self.processor = CLIPProcessor.from_pretrained(CLIP_MODEL)

    def encode_batch(self, ean_bytes_map: dict) -> dict:
        """Returns {ean: embedding_list_512}."""
        eans = list(ean_bytes_map.keys())
        results = {}
        for i in range(0, len(eans), CLIP_BATCH_SIZE):
            batch_eans = eans[i:i + CLIP_BATCH_SIZE]
            images = []
            for ean in batch_eans:
                try:
                    img = Image.open(BytesIO(ean_bytes_map[ean])).convert("RGB")
                    images.append(img)
                except Exception:
                    images.append(Image.new("RGB", (224, 224), (128, 128, 128)))
            with torch.no_grad():
                inputs = self.processor(images=images, return_tensors="pt")
                outputs = self.model.get_image_features(**inputs)
            embeddings = outputs.cpu().numpy()
            for j, ean in enumerate(batch_eans):
                results[ean] = embeddings[j].tolist()
            del images, inputs, outputs
            gc.collect()
        return results

def load_image_from_gcs(ean: str) -> bytes:
    client = storage.Client(project=PROJECT_ID)
    blob = client.bucket(GCS_BUCKET).blob(f"originals/{ean}.jpg")
    return blob.download_as_bytes()
```

**Commit:**
```bash
git add pipeline/encoder.py
git commit -m "pipeline: CLIP embedding encoder"
```

---

### Task 13: Text profiler + Anomaly detector + Scorer + Report generator

**Files:**
- Create: `pipeline/text_profiler.py`
- Create: `pipeline/anomaly_detector.py`
- Create: `pipeline/scorer.py`
- Create: `pipeline/report_generator.py`

`text_profiler.py`: execute `sql/02_text_profiling.sql` via BQ client with `run_id` param, insert results to `text_metrics`.

`anomaly_detector.py`: call `ML.DETECT_ANOMALIES(MODEL arima_text_model, ...)`, classify severity (CRITICAL if confidence > 0.95 AND deviation > 15%, HIGH > 0.90 > 10%, MEDIUM > 0.85 > 5%, else LOW), insert to `text_anomalies`.

`scorer.py`: JOIN product_scores + text_metrics + visual_detections, compute `catalog_score = 0.6 * text_score + 0.4 * visual_score`, MERGE into `product_scores`.

`report_generator.py`:
```python
import vertexai
from vertexai.generative_models import GenerativeModel
from pipeline.config import PROJECT_ID, REGION

vertexai.init(project=PROJECT_ID, location=REGION)

def generate_report(context: dict) -> dict:
    model = GenerativeModel("gemini-1.5-flash")
    prompt = f"""
    Tu es un expert qualite catalogue retail. Analyse ces donnees d'audit:

    Scores globaux: Catalogue {context['catalog_score']}, Texte {context['text_score']}, Visuel {context['visual_score']}
    Anomalies critiques: {context['critical_anomalies']}
    Pires categories: {context['worst_categories']}

    Genere un rapport JSON avec ces champs exactement:
    {{
        "executive_summary": "3 phrases en francais pour un directeur retail",
        "catalog_score": {context['catalog_score']},
        "text_score": {context['text_score']},
        "visual_score": {context['visual_score']},
        "critical_issues": [{{"issue": "...", "affected_count": N, "severity": "CRITICAL"}}],
        "worst_categories": [{{"name": "...", "score": N}}],
        "recommendations": ["action 1", "action 2", "action 3"]
    }}
    Reponds uniquement avec le JSON valide.
    """
    response = model.generate_content(prompt)
    import json
    return json.loads(response.text)
```

**Commit:**
```bash
git add pipeline/text_profiler.py pipeline/anomaly_detector.py pipeline/scorer.py pipeline/report_generator.py
git commit -m "pipeline: text audit, scoring, Gemini report"
```

---

### Task 14: main.py orchestration + Docker

**Files:**
- Create: `pipeline/main.py`
- Create: `docker/Dockerfile.pipeline`

```python
# pipeline/main.py
import asyncio, uuid
from google.cloud import bigquery
from pipeline import config, downloader, thumbnailer, visual_scorer, vision, encoder
from pipeline import text_profiler, anomaly_detector, scorer, report_generator

async def run():
    run_id = str(uuid.uuid4())
    print(f"[Pipeline] Starting run {run_id}")
    bq = bigquery.Client(project=config.PROJECT_ID)

    # Load product list
    rows = list(bq.query(
        f"SELECT ean, image_url, product_name, brands, categories FROM "
        f"`{config.PROJECT_ID}.{config.BQ_DATASET}.products_selected`"
    ))
    product_map = {r.ean: dict(r) for r in rows}
    print(f"[Pipeline] {len(product_map)} products loaded")

    # Branch 1: Text audit
    text_profiler.run(bq, run_id)
    try:
        anomaly_detector.run(bq, run_id)
    except Exception as e:
        print(f"[Pipeline] ARIMA skip (first run?): {e}")

    # Branch 2: Visual audit
    download_results = await downloader.download_all(product_map)
    success_eans = {ean for ean, r in download_results.items() if r["success"]}
    print(f"[Pipeline] Downloaded {len(success_eans)}/{len(product_map)} images")

    thumbnailer.generate_all(success_eans, bq, run_id)
    visual_scores = visual_scorer.score_all(success_eans)
    vision_results = await vision.detect_batch(
        {ean: f"originals/{ean}.jpg" for ean in success_eans}
    )
    clip_encoder = encoder.CLIPEncoder.get()
    ean_bytes = {
        ean: encoder.load_image_from_gcs(ean) for ean in list(success_eans)[:1000]
    }
    embeddings = clip_encoder.encode_batch(ean_bytes)

    # Write visual results to BQ
    visual_scorer.write_to_bq(bq, run_id, visual_scores, vision_results)
    encoder.write_embeddings_to_bq(bq, run_id, embeddings)

    # Fusion
    scorer.fuse_and_write(bq, run_id)

    # Report
    context = scorer.get_report_context(bq)
    report = report_generator.generate_report(context)
    report_generator.write_report(bq, run_id, report)

    print(f"[Pipeline] Run {run_id} complete.")

if __name__ == "__main__":
    asyncio.run(run())
```

```dockerfile
# docker/Dockerfile.pipeline
FROM pytorch/pytorch:2.1.1-cpu-py39 AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pipeline/ ./pipeline/
COPY sql/ ./sql/
ENV PYTHONPATH=/app
CMD ["python", "-m", "pipeline.main"]
```

**Commit:**
```bash
git add pipeline/main.py docker/Dockerfile.pipeline
git commit -m "pipeline: orchestration and Docker"
```

---

## PHASE 4 - FastAPI

### Task 15: API setup + main.py + config

**Files:**
- Create: `api/main.py`
- Create: `api/config.py`
- Create: `api/requirements.txt`
- Create: `docker/Dockerfile.api`

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import catalog, products, anomalies, search, reports, quality

app = FastAPI(title="Prisme API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://prisme.stephanewamba.com",
        "https://prisme-wamba.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(products.router)
app.include_router(anomalies.router)
app.include_router(search.router)
app.include_router(reports.router)
app.include_router(quality.router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

```dockerfile
# docker/Dockerfile.api
FROM python:3.11-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ ./api/
ENV PYTHONPATH=/app PORT=8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Commit:**
```bash
git add api/main.py api/config.py api/requirements.txt docker/Dockerfile.api
git commit -m "api: FastAPI setup and Docker"
```

---

### Task 16: BigQuery service + GCS service + cache

**Files:**
- Create: `api/services/bigquery.py`
- Create: `api/services/gcs.py`

```python
# api/services/bigquery.py
from google.cloud import bigquery
from cachetools import TTLCache
from functools import wraps
import hashlib, json

_cache = TTLCache(maxsize=500, ttl=600)
_bq = bigquery.Client(project="prisme-wamba-2026")

def cached_query(sql: str, params: dict = None) -> list:
    key = hashlib.md5(f"{sql}{json.dumps(params or {}, sort_keys=True)}".encode()).hexdigest()
    if key in _cache:
        return _cache[key]
    job = _bq.query(sql)
    result = [dict(row) for row in job.result()]
    _cache[key] = result
    return result

def vector_search(embedding: list, top_k: int = 10) -> list:
    """BigQuery COSINE_DISTANCE search on visual_embeddings."""
    sql = """
    SELECT ean, COSINE_DISTANCE(embedding, @emb) AS distance
    FROM `prisme-wamba-2026.prisme_dataset.visual_embeddings`
    WHERE DATE(run_date) = CURRENT_DATE()
    ORDER BY distance ASC
    LIMIT @k
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ArrayQueryParameter("emb", "FLOAT64", embedding),
        bigquery.ScalarQueryParameter("k", "INT64", top_k),
    ])
    return [dict(row) for row in _bq.query(sql, job_config=job_config).result()]
```

**Commit:**
```bash
git add api/services/
git commit -m "api: BigQuery service with TTL cache"
```

---

### Task 17: All 8 routers

**Files:**
- Create: `api/routers/catalog.py` - GET /catalog/health, GET /categories
- Create: `api/routers/products.py` - GET /products/{ean}, POST /products/audit
- Create: `api/routers/anomalies.py` - GET /anomalies
- Create: `api/routers/search.py` - POST /search/visual
- Create: `api/routers/reports.py` - GET /reports/latest
- Create: `api/routers/quality.py` - GET /quality/coverage
- Create: `api/models/schemas.py` - All Pydantic models

Key schemas (`api/models/schemas.py`):
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class HealthResponse(BaseModel):
    catalog_score: float
    text_score: float
    visual_score: float
    evolution_30d: List[dict]
    last_audit_run: datetime
    product_count: int

class ProductDetail(BaseModel):
    ean: str
    product_name: str
    brands: Optional[str]
    categories: Optional[str]
    text_score: float
    visual_score: float
    catalog_score: float
    thumbnail_urls: dict
    vision_labels: List[dict]
    text_anomalies: List[dict]
    visual_anomalies: List[dict]
    has_visual_audit: bool

class VisualSearchRequest(BaseModel):
    image_url: str

class VisualSearchResponse(BaseModel):
    similar_products: List[dict]
```

Test each endpoint locally:
```bash
uvicorn api.main:app --reload
# Then:
curl http://localhost:8000/catalog/health
curl http://localhost:8000/categories
curl http://localhost:8000/anomalies?type=text&severity=HIGH
curl -X POST http://localhost:8000/search/visual -H "Content-Type: application/json" -d '{"image_url": "https://..."}'
```

**Commit:**
```bash
git add api/routers/ api/models/
git commit -m "api: all 8 endpoints"
```

---

## PHASE 5 - CI/CD

### Task 18: GitHub Actions deploy.yml

**Files:**
- Create: `.github/workflows/deploy.yml`

```yaml
name: Deploy Prisme
on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  PROJECT_ID: prisme-wamba-2026
  REGION: europe-west1

jobs:
  deploy-api:
    runs-on: ubuntu-latest
    outputs:
      api_url: ${{ steps.deploy.outputs.url }}
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: |
          gcloud builds submit \
            --tag $REGION-docker.pkg.dev/$PROJECT_ID/prisme-docker/prisme-api:$GITHUB_SHA \
            --file docker/Dockerfile.api .
      - id: deploy
        run: |
          gcloud run deploy prisme-api \
            --image $REGION-docker.pkg.dev/$PROJECT_ID/prisme-docker/prisme-api:$GITHUB_SHA \
            --region $REGION --min-instances 1 --max-instances 3 \
            --memory 512Mi --cpu 1 --allow-unauthenticated \
            --service-account prisme-cloud-run@$PROJECT_ID.iam.gserviceaccount.com
          echo "url=$(gcloud run services describe prisme-api --region $REGION --format='value(status.url)')" >> $GITHUB_OUTPUT

  deploy-pipeline:
    if: github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: |
          gcloud builds submit \
            --tag $REGION-docker.pkg.dev/$PROJECT_ID/prisme-docker/prisme-pipeline:$GITHUB_SHA \
            --file docker/Dockerfile.pipeline .
          gcloud run jobs update prisme-pipeline \
            --image $REGION-docker.pkg.dev/$PROJECT_ID/prisme-docker/prisme-pipeline:$GITHUB_SHA \
            --region $REGION --memory 4Gi --cpu 2 \
            --service-account prisme-cloud-run@$PROJECT_ID.iam.gserviceaccount.com || \
          gcloud run jobs create prisme-pipeline \
            --image $REGION-docker.pkg.dev/$PROJECT_ID/prisme-docker/prisme-pipeline:$GITHUB_SHA \
            --region $REGION --memory 4Gi --cpu 2 \
            --service-account prisme-cloud-run@$PROJECT_ID.iam.gserviceaccount.com

  deploy-frontend:
    needs: [deploy-api]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          echo "NEXT_PUBLIC_API_URL=${{ needs.deploy-api.outputs.api_url }}" >> frontend/.env.production
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: frontend
          vercel-args: --prod
```

**Commit:**
```bash
git add .github/workflows/deploy.yml
git commit -m "ci: GitHub Actions deploy pipeline"
```

---

## PHASE 6 - Frontend

### Task 19: Next.js init + globals.css + layout

**Files:**
- Create: `frontend/` (Next.js 14 scaffold)
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/app/layout.tsx`

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir
# Then move files to src/app structure
```

```css
/* frontend/src/app/globals.css */
@import "tailwindcss";
@source "../**/*.tsx";

:root {
  --bg: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-tertiary: #f3f4f6;
  --text: #111827;
  --text-secondary: #6b7280;
  --accent: #10b981;
  --border: #e5e7eb;
  --border-strong: #d1d5db;
  --score-good: #10b981;
  --score-medium: #f59e0b;
  --score-poor: #ef4444;
  --text-score: #3b82f6;
  --visual-score: #a855f7;
  --severity-critical: #dc2626;
  --severity-high: #f59e0b;
  --severity-medium: #eab308;
  --severity-low: #6b7280;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: "Inter", -apple-system, system-ui, sans-serif;
}

/* Grain texture */
body::before {
  content: "";
  position: fixed;
  inset: 0;
  background-image: url("/grain.png");
  opacity: 0.02;
  pointer-events: none;
  z-index: 1;
}

h1 { font-size: clamp(2rem, 5vw, 3.5rem); font-weight: 600; line-height: 1.2; letter-spacing: -0.02em; }
h2 { font-size: clamp(1.5rem, 4vw, 2.5rem); font-weight: 600; line-height: 1.3; letter-spacing: -0.02em; }
h3 { font-size: clamp(1.125rem, 2.5vw, 1.5rem); font-weight: 600; line-height: 1.4; }

@keyframes enterRow {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}
.row-enter { animation: enterRow 400ms cubic-bezier(0.34, 1.56, 0.64, 1); }

.search-line { height: 1px; background: var(--border-strong); transition: background 200ms ease; }
.search-wrap:focus-within .search-line { background: var(--text); }
```

```tsx
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Prisme - Audit qualite catalogue",
  description: "Plateforme d audit qualite catalogue retail FMCG",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className={inter.className}>
        <Nav />
        <main>{children}</main>
      </body>
    </html>
  );
}
```

```bash
# Install dependencies
cd frontend
npm install framer-motion recharts lucide-react
```

**Commit:**
```bash
git add frontend/src/app/globals.css frontend/src/app/layout.tsx
git commit -m "frontend: Next.js init, globals, layout"
```

---

### Task 20: Nav + OnboardingGuide components

**Files:**
- Create: `frontend/src/components/Nav.tsx`
- Create: `frontend/src/components/OnboardingGuide.tsx`

`Nav.tsx`: Links = Tableau de bord | Rayons | Alertes | Recherche visuelle | Rapports. Hamburger < 768px, animated X transform. Active link = border-bottom 2px.

`OnboardingGuide.tsx`: 5 steps (see design doc), backdrop blur, localStorage check, progress dots, Passer + Suivant buttons. Framer Motion fade between steps.

**Commit:**
```bash
git add frontend/src/components/Nav.tsx frontend/src/components/OnboardingGuide.tsx
git commit -m "frontend: navigation and onboarding modal"
```

---

### Task 21: Core components (ScoreGauge, ProductCard, AnomalyBadge)

**Files:**
- Create: `frontend/src/components/ScoreGauge.tsx`
- Create: `frontend/src/components/ProductCard.tsx`
- Create: `frontend/src/components/AnomalyBadge.tsx`

`ScoreGauge.tsx`:
- SVG arc 270 degrees, stroke-dashoffset animation 900ms ease-out
- CountUp 0 to value (Framer Motion motionValue)
- Color: green >= 70, orange 40-69, red < 40
- Props: value, label, size ("sm" | "md" | "lg")

`ProductCard.tsx`:
- Vertical layout: image (256px) + name + brand + score badge
- Framer Motion: scale 0.95->1 + opacity, stagger
- Hover: translateY(-2px), shadow, border brighten
- Skeleton: animate-pulse placeholder

`AnomalyBadge.tsx`:
- Pill shape, compact (icon + severity) or expanded (+ description max 60 chars)
- Lucide icons: AlertCircle (missing), XCircle (invalid), TrendingUp (outlier), Eye (blur)
- Colors from CSS variables (--severity-critical etc.)

**Commit:**
```bash
git add frontend/src/components/ScoreGauge.tsx frontend/src/components/ProductCard.tsx frontend/src/components/AnomalyBadge.tsx
git commit -m "frontend: core components ScoreGauge, ProductCard, AnomalyBadge"
```

---

### Task 22: Data components + API client

**Files:**
- Create: `frontend/src/components/LineChart.tsx`
- Create: `frontend/src/components/StatCard.tsx`
- Create: `frontend/src/components/FilterBar.tsx`
- Create: `frontend/src/lib/api.ts`

`LineChart.tsx`: Recharts ResponsiveContainer, 3 lines (catalog/text/visual), minimal grid (horizontal only), tooltip, legend bottom. Framer Motion wrapper fade-in on scroll.

`api.ts`:
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getCatalogHealth() {
  const res = await fetch(`${API_URL}/catalog/health`, { next: { revalidate: 600 } });
  if (!res.ok) throw new Error("API error");
  return res.json();
}

export async function getCategories() {
  const res = await fetch(`${API_URL}/categories`, { next: { revalidate: 600 } });
  return res.json();
}

export async function getProduct(ean: string) {
  const res = await fetch(`${API_URL}/products/${ean}`);
  return res.json();
}

export async function getAnomalies(params: Record<string, string> = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${API_URL}/anomalies${qs ? `?${qs}` : ""}`);
  return res.json();
}

export async function searchVisual(imageUrl: string) {
  const res = await fetch(`${API_URL}/search/visual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_url: imageUrl }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getLatestReport() {
  const res = await fetch(`${API_URL}/reports/latest`);
  return res.json();
}
```

**Commit:**
```bash
git add frontend/src/components/LineChart.tsx frontend/src/components/StatCard.tsx frontend/src/components/FilterBar.tsx frontend/src/lib/api.ts
git commit -m "frontend: data components and API client"
```

---

### Task 23: Page / (Health overview)

**Files:**
- Modify: `frontend/src/app/page.tsx`

Layout:
1. Hero: titre "Tableau de bord" + sous-titre
2. 3 ScoreGauge cote a cote (catalog/text/visual) avec animation au montage
3. LineChart 30j
4. CTA: "Voir les alertes critiques ->"
5. 3 StatCard (produits, anomalies, couverture)
6. OnboardingGuide (premier visit)

Key implementation:
```tsx
"use client";
import { useEffect, useState } from "react";
import { getCatalogHealth } from "@/lib/api";

// Scores animate from 0 on mount
// framer-motion animate presence for OnboardingGuide
```

**Commit:**
```bash
git add frontend/src/app/page.tsx
git commit -m "frontend: page tableau de bord"
```

---

### Task 24: Pages /categories, /products/[ean], /anomalies

**Files:**
- Create: `frontend/src/app/categories/page.tsx`
- Create: `frontend/src/app/products/[ean]/page.tsx`
- Create: `frontend/src/app/anomalies/page.tsx`

`categories/page.tsx`:
- Table: Rang | Rayon | Score (colored) | Delta 7j | Produits | Anomalies
- Click ligne: drawer lateral (right panel, Framer Motion slide-in)
- Sort on header click
- Pagination 30 items

`products/[ean]/page.tsx`:
- Desktop: image left (640px) + metadata right
- Breadcrumb
- 3 ScoreGauge
- Expandable anomalies list (AnomalyBadge)
- Vision AI labels

`anomalies/page.tsx`:
- FilterBar: type (Text/Visual/Tous) + severite toggle buttons + categorie dropdown
- Table: Produit | Type | Severite | Rayon | ->
- Client-side filtering (fetch 1000 items, filter in React)
- Pagination 30 items
- Row stagger animation (.row-enter, 50ms/row)

**Commit:**
```bash
git add frontend/src/app/categories/ frontend/src/app/products/ frontend/src/app/anomalies/
git commit -m "frontend: pages categories, fiche produit, anomalies"
```

---

### Task 25: Pages /search et /reports

**Files:**
- Create: `frontend/src/app/search/page.tsx`
- Create: `frontend/src/app/reports/page.tsx`

`search/page.tsx`:
- Input URL style search-line (bordure basse uniquement, focus -> text color)
- Preview image 256px (s'affiche apres validation URL)
- Loading spinner pendant POST /search/visual
- Grille 5x2 (desktop) / 2x5 (mobile) de ProductCard
- Score similarite: % + barre visuelle coloree

`reports/page.tsx`:
- Dropdown selection date rapport
- Sections: Resume executif | 3 ScoreGauge | Problemes critiques (AnomalyBadge) | Pires rayons | Recommandations
- Traduire champs Gemini en francais (reportFieldLabels map)

**Commit:**
```bash
git add frontend/src/app/search/ frontend/src/app/reports/
git commit -m "frontend: pages recherche visuelle et rapports"
```

---

## PHASE 7 - Deploy + Validation

### Task 26: Premier deploy complet

**Steps:**

1. Push to main -> GitHub Actions triggers deploy-api
```bash
git push origin main
```
Expected: API deployed on Cloud Run URL

2. Check API health:
```bash
curl https://prisme-api-xxx-ew.a.run.app/health
# {"status": "ok"}
```

3. Check frontend on Vercel preview URL
4. Trigger pipeline manually:
```bash
gcloud run jobs execute prisme-pipeline --region europe-west1
```
Expected: pipeline completes in < 1h, BQ tables populated

5. Verify BQ data:
```sql
SELECT COUNT(*) FROM `prisme-wamba-2026.prisme_dataset.product_scores`;
-- Expected: ~8000-12000 rows
```

6. Test all API endpoints against production data
7. Verify frontend pages render correctly

**Commit after any fixes:**
```bash
git commit -m "fix: post-deploy corrections"
```

---

### Task 27: Looker Studio dashboard

**Steps:**

1. Open https://lookerstudio.google.com
2. Create new report, connect BigQuery source
3. Connect `prisme-wamba-2026.prisme_dataset`
4. Add 6 charts (see design doc section 7):
   - Gauge: catalog_score global (from v_kpi_daily)
   - Bullet chart: text_score vs visual_score
   - Line chart 30j: v_scores_evolution_30d
   - Bar chart horizontal: v_categories_ranked (top 15)
   - Stacked bar: v_text_anomalies_by_severity
   - Table: v_worst_products (top 20)
5. Set report to public (Share > Manage access > Anyone with link can view)
6. Copy link

---

### Task 28: README

**Files:**
- Create: `README.md` (force-tracked despite .gitignore)

Content (en anglais):
- Project description (2 paragraphs)
- Architecture diagram (text)
- Tech stack table
- 3 links: app live, Looker dashboard, GitHub
- How to run locally

```bash
git add -f README.md
git commit -m "docs: README"
```

---

### Task 29: Final checks + .gitignore

**Files:**
- Create: `.gitignore`

```
*.md
docs/
.env
.env.local
__pycache__/
*.pyc
.venv/
node_modules/
.next/
```

Force-add markdown that must be tracked:
```bash
git add -f README.md docs/plans/2026-03-26-prisme-design.md docs/plans/2026-03-26-prisme-implementation.md
```

Pre-commit checklist:
```bash
# Check for em dashes
grep -r "—" --include="*.tsx" --include="*.py" --include="*.md" .
# Expected: 0 results

# Check no secrets in git
git diff --cached | grep -E "(API_KEY|SECRET|PASSWORD|TOKEN)" | grep -v ".github"
```

---

## Recapitulatif fichiers

```
32 fichiers a creer:
  infra/ : setup.sh, iam.sh, create_bq_tables.py
  sql/ : 01-05 (5 fichiers)
  pipeline/ : main.py, config.py, + 8 modules Python + requirements.txt
  api/ : main.py, config.py, requirements.txt + 6 routers + 5 services + models/
  docker/ : Dockerfile.api, Dockerfile.pipeline
  frontend/ : layout.tsx, globals.css, page.tsx + 5 pages + 7 composants + api.ts
  .github/ : deploy.yml
  README.md
```

---

*Plan ecrit le 26/03/2026 - Pret pour execution*
