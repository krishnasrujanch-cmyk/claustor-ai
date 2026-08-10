#!/bin/bash
# Claustor AI — GCP Deployment Script
set -e

PROJECT_ID="claustor-prod"
REGION="asia-south1"  # Mumbai — closest to India
REPO="claustor"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/api"
TAG=$(git rev-parse --short HEAD)

echo "🚀 Deploying Claustor AI to GCP"
echo "   Project: $PROJECT_ID"
echo "   Region:  $REGION"
echo "   Tag:     $TAG"

# 1. Build image
echo "📦 Building Docker image..."
docker build -t $IMAGE:$TAG -t $IMAGE:latest .

# 2. Push to Artifact Registry
echo "📤 Pushing to Artifact Registry..."
docker push $IMAGE:$TAG
docker push $IMAGE:latest

# 3. Deploy API
echo "🌐 Deploying API..."
gcloud run deploy claustor-api \
    --image=$IMAGE:latest \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --min-instances=1 \
    --max-instances=10 \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300 \
    --concurrency=80 \
    --set-secrets="ENV_FILE=claustor-env:latest" \
    --project=$PROJECT_ID

# 4. Deploy Celery Worker
echo "⚙️  Deploying Celery Worker..."
gcloud run deploy claustor-worker \
    --image=$IMAGE:latest \
    --region=$REGION \
    --platform=managed \
    --no-allow-unauthenticated \
    --min-instances=1 \
    --max-instances=3 \
    --memory=4Gi \
    --cpu=2 \
    --timeout=3600 \
    --concurrency=1 \
    --command="/app/docker-entrypoint-worker.sh" \
    --set-secrets="ENV_FILE=claustor-env:latest" \
    --project=$PROJECT_ID

echo "✅ Deployment complete!"
echo "   API: https://claustor-api-xxx-$REGION.run.app"
echo "   Map api.claustor.com → Cloud Run domain"
