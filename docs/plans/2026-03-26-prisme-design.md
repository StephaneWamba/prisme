# Prisme - Design Document
*26 mars 2026 - Validé par Wamba*

---

## 1. Contexte et objectifs

Prisme est une plateforme d'audit qualité catalogue retail/FMCG. Projet portfolio pour un entretien Davidson Consulting (secteurs retail, luxe, FMCG).

**Audience principale:** Consultant Davidson technique, visite 5-10 min, doit être impressionné.

**Livrable attendu:**
1. App live `prisme.stephanewamba.com`
2. Dashboard Looker Studio (lien public)
3. GitHub repo `github.com/StephaneWamba/prisme`

---

## 2. Donnees source

**Dataset:** `bigquery-public-data.open_food_facts.products`

**Subset retenu:** ~10 000 produits - top 50 par categorie (garantit diversite par rayon)

```sql
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY SPLIT(categories, ',')[SAFE_OFFSET(0)]
      ORDER BY last_modified_t DESC
    ) AS rn
  FROM `bigquery-public-data.open_food_facts.products`
  WHERE countries LIKE '%France%'
    AND image_url IS NOT NULL
    AND TRIM(product_name) != ''
)
SELECT * EXCEPT(rn) FROM ranked WHERE rn <= 50
```

Raison du subset: CLIP encoding 180k images = 5-6h, Cloud Run timeout = 50 min. 10k produits = pipeline < 1h, un seul Cloud Run Job, pas de split.

---

## 3. Architecture globale

```
[BigQuery public - Open Food Facts]
        |
        v
[products_selected ~10k] --- SQL 01_staging.sql
        |
        v
[Cloud Run Job - prisme-pipeline - 1h max]
  |-- text_profiler.py     -> prisme_dataset.text_metrics
  |-- anomaly_detector.py  -> prisme_dataset.text_anomalies
  |-- downloader.py        -> GCS gs://prisme-assets/originals/
  |-- thumbnailer.py       -> GCS gs://prisme-assets/thumbnails/
  |-- visual_scorer.py     -> prisme_dataset.visual_detections
  |-- vision.py            -> prisme_dataset.visual_detections
  |-- encoder.py           -> prisme_dataset.visual_embeddings
  |-- scorer.py            -> prisme_dataset.product_scores
  |-- report_generator.py  -> prisme_dataset.reports
        |
        v
[FastAPI - Cloud Run Service - min-instances=1]
  8 endpoints
        |
        v
[Next.js - Vercel]
  6 pages
        |
        v
[Looker Studio - dashboard public]
```

---

## 4. BigQuery - Schema des tables

### 4.1 Tables principales (7)

| Table | Description | Partitioning |
|-------|-------------|--------------|
| `products_selected` | Staging, ~10k produits normalises | DATE(ingestion_timestamp) |
| `text_metrics` | Series temporelles metriques completude | DATE(run_date) |
| `text_anomalies` | Output BQML ARIMA_PLUS | DATE(run_date) |
| `visual_detections` | Cloud Vision labels + scores image | DATE(run_date) |
| `visual_embeddings` | CLIP 512 dims par produit | DATE(run_date) |
| `product_scores` | Fusion text_score(0.6) + visual_score(0.4) | DATE(run_date) |
| `reports` | Rapports Gemini JSON | DATE(report_date) |

### 4.2 Cles de schema

**product_scores (table centrale API):**
```sql
ean STRING, run_date TIMESTAMP, run_id STRING,
text_score INT64, visual_score INT64,
catalog_score INT64,  -- 0.6 * text + 0.4 * visual
product_name STRING, categories STRING,
thumbnail_url_128 STRING, thumbnail_url_256 STRING, thumbnail_url_512 STRING,
has_anomaly_text BOOL, has_anomaly_visual BOOL
```

**visual_embeddings (VECTOR_SEARCH):**
```sql
ean STRING, run_date TIMESTAMP,
embedding ARRAY<FLOAT64>,  -- 512 dimensions CLIP
embedding_model_name STRING
```

### 4.3 ARIMA_PLUS - Bootstrap

Probleme: ARIMA necessite 20+ points historiques. Solution pour la demo: generer 30 jours de donnees synthetiques avec patterns realistes dans `03_bqml_arima.sql`, commenter apres 30j reels.

### 4.4 SQL files (5 fichiers)

```
sql/
  01_staging.sql        -- Open Food Facts -> products_selected (subset 10k)
  02_text_profiling.sql -- completude + Z-scores + insertion text_metrics
  03_bqml_arima.sql     -- CREATE MODEL + DETECT_ANOMALIES
  04_scores.sql         -- fusion text+visual -> product_scores
  05_looker_views.sql   -- vues analytiques pour Looker Studio
```

---

## 5. Pipeline Python - Cloud Run Job

### 5.1 Architecture

Un seul Cloud Run Job (`prisme-pipeline`). Deux branches sequentielles (pas paralleles - un seul CPU).

```python
# main.py - orchestration
async def run_pipeline():
    # Branch 1: Text audit (SQL-based, rapide)
    await text_profiler.run()
    await anomaly_detector.run()

    # Branch 2: Visual audit (I/O-bound, asyncio)
    await downloader.download_all()       # asyncio aiohttp, 64 concurrent
    await thumbnailer.generate_all()      # Pillow 3 formats
    await visual_scorer.score_all()       # Laplacian + resolution
    await vision.detect_all()             # Cloud Vision API batch
    await encoder.encode_all()            # CLIP batch_size=32, checkpoint BQ

    # Fusion + rapport
    await scorer.fuse_scores()
    await report_generator.generate()
```

### 5.2 Details techniques

**Downloader (asyncio + aiohttp):**
- 64 connexions simultanees
- Retry x3 avec backoff exponentiel (1s, 2s, 4s)
- Validation: magic bytes + taille > 5KB + decode PIL
- Fallback: image_small_url si image_url echoue

**CLIP Encoder:**
- Modele: `openai/clip-vit-base-patch32` (HuggingFace)
- CPU-only (pas de GPU sur Cloud Run)
- batch_size=32, checkpoint BQ tous les 320 images
- gc.collect() apres chaque batch
- RAM estimee: ~1.5 GB peak (safe sur 4 GiB)

**Vision API:**
- Object Localization + Label Detection + Safe Search
- Batch: 16 images par request (limite API)
- Rate limit: 1800 requests/min, throttle si besoin

**Sizing Cloud Run Job:**
```
memory: 4Gi
cpu: 2
timeout: 3600  -- 1 heure
max_instances: 1
```

### 5.3 Fichiers pipeline (10 fichiers)

```
pipeline/
  main.py              -- orchestration asyncio
  config.py            -- env vars (PROJECT_ID, BUCKET_NAME, BQ_DATASET)
  text_profiler.py     -- completude champs, Z-scores, insert text_metrics
  anomaly_detector.py  -- lecture BQML DETECT_ANOMALIES + severite
  downloader.py        -- asyncio aiohttp download + GCS upload
  thumbnailer.py       -- Pillow 3 formats + GCS signed URLs
  visual_scorer.py     -- resolution + sharpness (Laplacian OpenCV)
  vision.py            -- Cloud Vision API batch
  encoder.py           -- CLIP vit-base-patch32 + insert visual_embeddings
  scorer.py            -- fusion 0.6*text + 0.4*visual
  report_generator.py  -- Vertex AI Gemini 1.5 Flash -> JSON -> BQ
```

---

## 6. FastAPI - 8 endpoints

### 6.1 Liste endpoints

| Method | Path | Description | Latence |
|--------|------|-------------|---------|
| GET | /catalog/health | 3 scores + evolution 30j | ~200ms |
| GET | /categories | Classement rayons par score | ~150ms |
| GET | /products/{ean} | Fiche complete produit | ~300ms |
| POST | /products/audit | Audit a la volee (on-demand) | 1-3s |
| GET | /anomalies | Liste filtree anomalies | ~200ms |
| POST | /search/visual | CLIP + VECTOR_SEARCH top 10 | 400ms-1.6s |
| GET | /reports/latest | Dernier rapport Gemini | ~100ms |
| GET | /quality/coverage | Taux image/thumbnail/CLIP | ~100ms |

### 6.2 Services (5 fichiers)

```
api/services/
  bigquery.py   -- BigQuery client + query_and_cache (cachetools TTL 10min)
  gcs.py        -- GCS signed URLs (valides 30j, stockees dans BQ)
  vision.py     -- Cloud Vision API (pour /products/audit)
  clip.py       -- CLIP embeddings (charge modele au startup, warm)
  vertex.py     -- Gemini 1.5 Flash via Vertex AI (ADC, pas de cle)
```

### 6.3 Points critiques

- **Cache:** `cachetools.TTLCache(maxsize=1000, ttl=600)` - evite re-query BQ
- **CORS:** origines autorisees = localhost:3000 + prisme.stephanewamba.com
- **Cold start:** `min_instances=1` elimine les cold starts
- **POST /search/visual:** CLIP modele charge une fois au startup (pas au request)
- **Thumbnails GCS:** URLs signees generees en batch par le pipeline, stockees dans product_scores - pas de signing au request

---

## 7. Frontend - Direction artistique et UX

### 7.1 Theme light - Palette officielle

```css
--bg: #ffffff
--bg-secondary: #f9fafb
--bg-tertiary: #f3f4f6
--text: #111827
--text-secondary: #6b7280
--accent: #10b981        /* vert emeraude CTA */
--border: #e5e7eb
--border-strong: #d1d5db
--score-good: #10b981
--score-medium: #f59e0b
--score-poor: #ef4444
--text-score: #3b82f6    /* bleu */
--visual-score: #a855f7  /* violet */
--severity-critical: #dc2626
--severity-high: #f59e0b
--severity-medium: #eab308
--severity-low: #6b7280
```

**Typographie:** Inter (Google Fonts), font unique, poids 400/500/600
**Grain texture:** PNG bruit Perlin, opacity 0.02 sur body::before - signature non-AI-slop

### 7.2 References design

- **Linear.app** - stagger animations, palette minimaliste, hover discret
- **Vercel Dashboard** - layout KPIs, line chart minimal grid
- **Stripe Billing** - usage parcimonieux couleur, badges opacity

### 7.3 Navigation (6 items)

| Route | Label UI |
|-------|----------|
| `/` | Tableau de bord |
| `/categories` | Rayons |
| `/anomalies` | Alertes |
| `/search` | Recherche visuelle |
| `/reports` | Rapports |

### 7.4 Pages (6)

**Page `/` - Health Overview**
- Hero: 3 x ScoreGauge (catalog/text/visual) cote a cote
- WOW MOMENT: gauges comptent de 0 a la valeur au chargement (1.5s ease-out)
- Line chart 30j sous les gauges (Recharts, 3 courbes, minimal grid)
- CTA primaire: "Voir les anomalies critiques ->" (navigate /anomalies?severity=CRITICAL)
- Stats rapides: 3 StatCard (produits audites, anomalies detectees, couverture images)

**Page `/categories` - Rayons**
- Table sortable (Score ASC par defaut - pires en haut)
- Colonnes: Rang | Rayon | Score | Delta 7j | Produits | Anomalies
- Click ligne: drawer lateral (pas navigation)
- Filtres top bar: dropdown multi-select
- Pagination 30 items

**Page `/products/[ean]` - Fiche produit**
- Layout desktop: image gauche + metadata droite
- ThumbnailGrid: image principale 640px + 3 thumbnails formats
- 3 gauges scores (catalog/text/visual)
- Anomalies: expandable list (rouge CRITICAL)
- Vision AI labels
- Breadcrumb: Tableau de bord > Rayon > Produit

**Page `/anomalies` - Alertes**
- Filtres top bar: Type (Text/Visual/Tous) + Severite (toggle buttons) + Categorie + EAN search
- Table: Produit | Type | Severite | Rayon | Action
- Tri par severite DESC par defaut
- Pagination 30 items
- Filtrage client-side (initial load 1000 items)

**Page `/search` - Recherche visuelle**
- Input URL centre (style search-line: bordure basse uniquement)
- Preview image 256px avant envoi
- Top 10 resultats: grille 5x2 desktop / 2x5 mobile
- Score similarite en % + barre visuelle

**Page `/reports` - Rapports**
- Dropdown selection rapport par date
- Sections: Resume executif | 3 Gauges scores | Problemes critiques | Pires rayons | Recommandations

### 7.5 Composants (7 fichiers)

```
src/components/
  ScoreGauge.tsx    -- SVG arc, CountUp animation, 3 tailles (sm/md/lg)
  ProductCard.tsx   -- vertical, image top, hover elevation
  AnomalyBadge.tsx  -- pill arrondie, compact + expanded, Lucide icons
  LineChart.tsx     -- Recharts 3 courbes, minimal grid
  ProgressBar.tsx   -- barre remplie animee (couverture assets)
  StatCard.tsx      -- KPI box (valeur + label + tendance)
  FilterBar.tsx     -- dropdowns inline
```

### 7.6 Animations (Framer Motion)

| Composant | Animation | Duree |
|-----------|-----------|-------|
| ScoreGauge | stroke-dashoffset 0->final + CountUp | 900ms ease-out |
| ProductCard | scale 0.95->1 + opacity, stagger index*50ms | 400ms |
| AnomalyBadge | scale 0.95->1 + opacity, stagger index*50ms | 300ms |
| LineChart | fade-in + slide-up (scroll trigger) | 600ms |
| ProgressBar | width 0->target% | 1000ms |
| Page transition | cross-fade | 300ms |
| Row stagger (tables) | translateX(-20px)->0 + opacity, 50ms/ligne | 400ms |

### 7.7 Onboarding modal (5 etapes)

localStorage key: `prisme_onboarding_done`

1. **"Catalogue ou chaos?"** - 180k produits, sait-on quels sont incomplets?
2. **"Audit texte + visuel"** - completude metadata + qualite images, fusionnes
3. **"Anomalies prioritaires"** - detection automatique, triees par severite
4. **"Recherche par image"** - coller URL -> 10 produits visuellement similaires
5. **"Rapports IA quotidiens"** - Gemini resume les tendances chaque matin

---

## 8. Infrastructure GCP

### 8.1 Projet

```
GCP Project: prisme-wamba-2026
Region: europe-west1
```

### 8.2 Services actives

```bash
cloudrun.googleapis.com
artifactregistry.googleapis.com
bigquery.googleapis.com
storage-api.googleapis.com
vision.googleapis.com
aiplatform.googleapis.com
cloudscheduler.googleapis.com
secretmanager.googleapis.com
```

### 8.3 Service accounts

**Deployer** `github-actions-deployer@prisme-wamba-2026.iam.gserviceaccount.com`
- `roles/run.admin`
- `roles/artifactregistry.writer`
- `roles/iam.serviceAccountUser`
- Auth: Workload Identity Federation (WIF, pas de cle JSON)

**Runtime** `prisme-cloud-run@prisme-wamba-2026.iam.gserviceaccount.com`
- `roles/bigquery.dataViewer`
- `roles/bigquery.jobUser`
- `roles/secretmanager.secretAccessor`
- `roles/storage.objectAdmin`
- `roles/logging.logWriter`
- `roles/aiplatform.user`

### 8.4 Secrets

- `vision-api-key`: cle JSON Cloud Vision API
- Vertex AI Gemini: ADC via service account (pas de cle)
- GitHub Actions: `VERCEL_TOKEN`, `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`

### 8.5 Cloud Run sizing

**API Service:**
```
--min-instances=1  (elimine cold starts - obligatoire pour demo)
--max-instances=3
--memory=512Mi
--cpu=1
```

**Pipeline Job:**
```
--memory=4Gi
--cpu=2
--timeout=3600
--max-instances=1
```

### 8.6 Docker

**Dockerfile.api:** `python:3.11-slim` + FastAPI + uvicorn
**Dockerfile.pipeline:** `pytorch/pytorch:2.1.1-runtime-cpu` (900 MB, CPU-only)

CPU-only PyTorch: CLIP tourne en CPU, pas de GPU. Taille image: 900 MB vs 4-5 GB avec GPU. Cold start: 25s vs 3-4 min.

### 8.7 Cloud Scheduler

```
schedule: "0 2 * * *"  -- 02:00 UTC = 04:00 CET
trigger: HTTP POST sur prisme-pipeline job
```

### 8.8 CI/CD (.github/workflows/deploy.yml)

```
job deploy-api:      push main -> build -> Cloud Run Service
job deploy-pipeline: workflow_dispatch ONLY (pas sur push - 10k images = couteux)
job deploy-frontend: needs: [deploy-api] -> Vercel prod
```

### 8.9 Fichiers infra

```
infra/
  setup.sh              -- enable APIs, creer ressources GCP
  iam.sh                -- service accounts + WIF pool + provider
  create_bq_tables.py   -- DDL BigQuery (7 tables + vues Looker)
```

---

## 9. Structure repo finale

```
prisme/
  sql/
    01_staging.sql
    02_text_profiling.sql
    03_bqml_arima.sql
    04_scores.sql
    05_looker_views.sql
  pipeline/
    main.py
    config.py
    text_profiler.py
    anomaly_detector.py
    downloader.py
    thumbnailer.py
    visual_scorer.py
    vision.py
    encoder.py
    scorer.py
    report_generator.py
    requirements.txt
  api/
    main.py
    config.py
    routers/
      catalog.py
      products.py
      anomalies.py
      search.py
      reports.py
      quality.py
    services/
      bigquery.py
      gcs.py
      vision.py
      clip.py
      vertex.py
    models/
      schemas.py
      enums.py
    requirements.txt
  frontend/
    src/
      app/
        page.tsx
        categories/page.tsx
        products/[ean]/page.tsx
        anomalies/page.tsx
        search/page.tsx
        reports/page.tsx
        layout.tsx
        globals.css
      components/
        ScoreGauge.tsx
        ProductCard.tsx
        AnomalyBadge.tsx
        LineChart.tsx
        ProgressBar.tsx
        StatCard.tsx
        FilterBar.tsx
        Nav.tsx
        OnboardingGuide.tsx
      lib/
        api.ts
  docker/
    Dockerfile.api
    Dockerfile.pipeline
  infra/
    setup.sh
    iam.sh
    create_bq_tables.py
  .github/
    workflows/
      deploy.yml
```

---

## 10. Planning 4 jours

**Jour 1 (mer 26/03):**
- infra/setup.sh + infra/iam.sh (GCP setup)
- sql/ : 5 fichiers SQL, validation dans BQ console
- infra/create_bq_tables.py
- pipeline/config.py + pipeline/downloader.py + pipeline/thumbnailer.py

**Jour 2 (jeu 27/03):**
- pipeline complet: visual_scorer, vision, encoder, text_profiler, anomaly_detector, scorer, report_generator, main.py
- Premier run pipeline sur ~10k produits
- Validation BQ: product_scores populated

**Jour 3 (ven 28/03):**
- api/ complet: 8 endpoints + services
- Dockeriser + deploy Cloud Run
- frontend/ complet: 6 pages + 7 composants
- Deploy Vercel

**Dim 29/03:**
- Looker Studio dashboard (brancher sur BQ views)
- README propre (en anglais)
- 3 liens envoyes a Arnaud

---

## 11. Regles absolues (du lessons-learned.md)

- Em dashes (`-`) INTERDITES partout - remplacer par `-`
- UI 100% en francais, vocabulaire retail ("rayons", "catalogue", "alertes")
- JAMAIS de termes techniques dans UI: CLIP, embedding, HDBSCAN, ARIMA
- Tailwind v4: `@source "../**/*.tsx"` dans globals.css
- `"use client"` sur tout composant avec useState/useEffect
- Locale fr-FR: `toLocaleString("fr-FR")` pour tous les nombres
- `<html lang="fr">` dans root layout
- Commits: une ligne, pas de mention Claude/AI
- grep pour `-` avant chaque commit

---

*Design doc ecrit le 26/03/2026 - pret pour implementation*
