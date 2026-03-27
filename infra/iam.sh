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

echo "Setting up Workload Identity Federation..."
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub WIF Pool" \
  --project=$PROJECT_ID || true

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
echo "=== Add to GitHub Secrets ==="
echo "WIF_PROVIDER=$WIF_PROVIDER"
echo "WIF_SERVICE_ACCOUNT=github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com"
echo "CLOUD_RUN_SA=prisme-cloud-run@$PROJECT_ID.iam.gserviceaccount.com"
