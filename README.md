# Prisme

**Catalogue quality audit platform for FMCG / retail.**
Prisme ingests 1 000 Open Food Facts products, runs a dual-branch audit pipeline (text metadata + visual assets), exposes a REST API, and serves a Next.js dashboard with CLIP-powered visual search and daily Gemini AI reports.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-GCP-4285F4?logo=google-cloud&logoColor=white)
![Cloud Run](https://img.shields.io/badge/Cloud_Run-GCP-4285F4?logo=google-cloud&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-deployed-black?logo=vercel&logoColor=white)
![CLIP](https://img.shields.io/badge/CLIP-openai%2Fvit--base--patch32-412991?logo=huggingface&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google&logoColor=white)
![Vision API](https://img.shields.io/badge/Vision_API-GCP-4285F4?logo=google-cloud&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-container-2496ED?logo=docker&logoColor=white)

**Live demo:** [prisme.stephanewamba.com](https://prisme.stephanewamba.com)

---

## Architecture

```mermaid
graph TD
    OFF[Open Food Facts CSV] --> INGEST[ingest_off.py]
    INGEST --> BQ_RAW[(BigQuery\nproducts_selected)]

    BQ_RAW --> TEXT[Text branch\ntext_profiler + anomaly_detector]
    BQ_RAW --> VISUAL[Visual branch\ndownloader + encoder + thumbnailer + vision]

    TEXT --> SCORER[scorer.py\nfusion 60% text + 40% visual]
    VISUAL --> SCORER

    SCORER --> BQ_SCORES[(BigQuery\nproduct_scores)]
    TEXT --> BQ_ANOMALIES[(BigQuery\ntext_anomalies)]
    VISUAL --> BQ_CLIPS[(BigQuery\nclip_embeddings)]
    VISUAL --> GCS[(GCS\nprisme-assets)]

    BQ_SCORES --> API[FastAPI\nCloud Run]
    BQ_ANOMALIES --> API
    BQ_CLIPS --> API
    GCS --> FRONTEND[Next.js\nVercel]
    API --> FRONTEND

    GEMINI[Gemini 2.5 Flash] --> REPORT[report_generator.py]
    BQ_SCORES --> REPORT
    BQ_ANOMALIES --> REPORT
    REPORT --> BQ_REPORTS[(BigQuery\nreports)]
    BQ_REPORTS --> API
```

---

## Pipeline

```mermaid
flowchart LR
    subgraph Text branch
        T1[text_profiler\nmetadata completeness] --> T2[anomaly_detector\nCRITICAL / HIGH / MEDIUM]
    end

    subgraph Visual branch
        V1[downloader\nfetch image_url] --> V2[encoder\nCLIP embeddings to BQ]
        V1 --> V3[visual_scorer\nresolution + sharpness]
        V1 --> V4[thumbnailer\n128 / 256 / 512 px to GCS]
        V1 --> V5[vision.py\nVision API centration]
    end

    subgraph Fusion
        F1[scorer.py\ncatalog_score = text*0.6 + visual*0.4]
    end

    T2 --> F1
    V3 --> F1
    V5 --> F1
    F1 --> BQ[(product_scores)]
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/catalog/summary` | Global score averages |
| GET | `/catalog/evolution` | 30-day score history |
| GET | `/catalog/categories` | Category ranking |
| GET | `/products` | Paginated product list with filters |
| GET | `/products/{ean}` | Full product detail |
| GET | `/anomalies` | Detected anomalies (7 days) |
| GET | `/reports/latest` | Latest Gemini report |
| POST | `/search/visual` | CLIP visual similarity search |

---

## Visual search

```mermaid
sequenceDiagram
    participant UI as Next.js
    participant API as FastAPI
    participant CLIP as CLIPModel
    participant BQ as BigQuery

    UI->>API: POST /search/visual {image_url, k}
    API->>API: fetch image (PIL RGB)
    API->>CLIP: manual preprocess (224x224 BICUBIC, CLIP norm)
    CLIP-->>API: embedding float[512]
    API->>BQ: VECTOR_SEARCH(clip_embeddings, embedding, top_k)
    BQ-->>API: [{ean, distance}]
    API->>BQ: JOIN product_scores for metadata
    API-->>UI: [{ean, product_name, similarity, thumbnail_url}]
    UI->>UI: render grid sorted by similarity
```

---

## Scoring model

| Dimension | Weight | Sub-components |
|-----------|--------|----------------|
| Text score | 60% | Name, brands, categories, nutriscore, quantity, packaging completeness |
| Visual score | 40% | Resolution 40% + Sharpness 40% + Centration (Vision API) 20% |

`catalog_score = text_score * 0.6 + visual_score * 0.4`

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, App Router, Vercel |
| API | FastAPI 0.111, Python 3.12, Cloud Run |
| Pipeline | Python, BigQuery ML, Cloud Build, Docker |
| AI / ML | CLIP (openai/clip-vit-base-patch32), Gemini 2.5 Flash, Vision API |
| Storage | BigQuery (scores, embeddings, reports), GCS (thumbnails) |
| Infra | GCP: Cloud Run, Cloud Build, Artifact Registry, Cloud Storage |

---

## Project structure

```
prisme/
├── api/                     # FastAPI service (Cloud Run)
│   ├── routers/             # catalog, products, anomalies, search, reports
│   ├── services/            # bigquery.py, clip.py, vertex.py
│   └── requirements.txt
├── pipeline/                # Daily audit pipeline (Cloud Build)
│   ├── encoder.py           # CLIP batch embedding to BQ
│   ├── scorer.py            # Fusion scoring
│   ├── report_generator.py  # Gemini AI daily report
│   └── ...
├── frontend/                # Next.js app (Vercel)
│   └── src/app/
│       ├── page.tsx         # Dashboard
│       ├── categories/      # Category ranking
│       ├── anomalies/       # Alert list
│       ├── products/        # Catalogue + product detail
│       ├── search/          # CLIP visual search
│       └── reports/         # Gemini AI reports
├── sql/                     # BigQuery table DDL + ARIMA views
├── infra/                   # BQ table creation, IAM, data loading
└── docker/                  # Dockerfile.api, Dockerfile.pipeline
```

---

## Setup

### Prerequisites

- GCP project with BigQuery, Cloud Run, Cloud Build, Vision API enabled
- Artifact Registry repository for Docker images
- Vercel account

### Environment variables

**Cloud Run (API)**

```
GOOGLE_APPLICATION_CREDENTIALS or Workload Identity
GEMINI_API_KEY
```

**Vercel (frontend)**

```
NEXT_PUBLIC_API_URL=https://<cloud-run-url>
```

### Deploy API

```bash
gcloud builds submit --config cloudbuild-api.yaml
gcloud run deploy prisme-api \
  --image europe-west1-docker.pkg.dev/<project>/prisme-docker/prisme-api:latest \
  --region europe-west1
```

### Deploy frontend

```bash
cd frontend && vercel --prod
```

### Run pipeline

```bash
docker build -f docker/Dockerfile.pipeline -t prisme-pipeline .
docker run --env-file .env prisme-pipeline
```
