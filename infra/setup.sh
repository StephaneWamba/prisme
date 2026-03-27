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
  bigquerymigration.googleapis.com \
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
gsutil iam ch allUsers:objectViewer gs://prisme-assets || true

echo "Creating BQ dataset..."
bq mk --location=$REGION --dataset $PROJECT_ID:prisme_dataset || true

echo "Done. Run infra/iam.sh next."
