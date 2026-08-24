#!/bin/bash
# ============================================================
# Claustor AI — Deployment Scripts
# Usage: ./deploy.sh [api|worker|frontend|all]
# ============================================================

set -e

PROJECT=claustor-ai-prod
REGION=asia-south1
REPO=claustor-docker
IMAGE_API=asia-south1-docker.pkg.dev/$PROJECT/$REPO/claustor-api
IMAGE_WORKER=asia-south1-docker.pkg.dev/$PROJECT/$REPO/claustor-workeratest
API_DIR=/Users/srujan/Downloads/PYTHON/claustor-ai/apps/api
WEB_DIR=/Users/srujan/Downloads/PYTHON/claustor-ai/apps/web

# ── Load prod env ────────────────────────────────────────────
load_env() {
  set -a
  source $API_DIR/.env.production
  set +a
  echo "✅ Prod env loaded"
}

# ── Build + Deploy API ───────────────────────────────────────
deploy_api() {
  echo ""
  echo "═══════════════════════════════════════"
  echo "  Deploying API (8 CPU, 4GB RAM)"
  echo "═══════════════════════════════════════"
  cd $API_DIR
  load_env

  echo "Building API image..."
  gcloud builds submit \
    --tag=$IMAGE_API:latest \
    --project=$PROJECT \
    --machine-type=E2_HIGHCPU_8 \
    .

  echo "Deploying API to Cloud Run..."
  gcloud run deploy claustor-api \
    --image=$IMAGE_API:latest \
    --platform=managed \
    --region=$REGION \
    --service-account=claustor-api-sa@$PROJECT.iam.gserviceaccount.com \
    --allow-unauthenticated \
    --port=8080 \
    --memory=4Gi \
    --cpu=4 \  # increase to 8 for demos
    --no-cpu-throttling \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=300 \
    --project=$PROJECT \
    --set-env-vars="ENVIRONMENT=production,\
DATABASE_URL=$DATABASE_URL,\
REDIS_URL=$REDIS_URL,\
RABBITMQ_URL=$RABBITMQ_URL,\
PINECONE_API_KEY=$PINECONE_API_KEY,\
PINECONE_INDEX=$PINECONE_INDEX,\
PINECONE_HOST=$PINECONE_HOST,\
JWT_SECRET_KEY=$JWT_SECRET_KEY,\
AUTH0_DOMAIN=$AUTH0_DOMAIN,\
AUTH0_CLIENT_ID=$AUTH0_CLIENT_ID,\
AUTH0_CLIENT_SECRET=$AUTH0_CLIENT_SECRET,\
OPENAI_API_KEY=$OPENAI_API_KEY,\
OPENAI_MODEL=$OPENAI_MODEL,\
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,\
ANTHROPIC_MODEL=$ANTHROPIC_MODEL,\
GROQ_API_KEY=$GROQ_API_KEY,\
GEMINI_API_KEY=$GEMINI_API_KEY,\
RESEND_API_KEY=$RESEND_API_KEY,\
RESEND_FROM=$RESEND_FROM,\
RAZORPAY_KEY_ID=$RAZORPAY_KEY_ID,\
RAZORPAY_KEY_SECRET=$RAZORPAY_KEY_SECRET,\
GCS_BUCKET=$GCS_BUCKET,\
GCS_BUCKET_CONTRACTS=$GCS_BUCKET_CONTRACTS,\
GCP_PROJECT=$GCP_PROJECT,\
FRONTEND_URL=https://claustor.com,\
HF_HOME=/root/.cache/huggingface,\
TRANSFORMERS_CACHE=/root/.cache/huggingface/transformers,\
SENTENCE_TRANSFORMERS_HOME=/root/.cache/sentence_transformers"

  API_URL=$(gcloud run services describe claustor-api \
    --region=$REGION --project=$PROJECT \
    --format="value(status.url)")
  echo ""
  echo "✅ API deployed: $API_URL"
  echo "   Health: $(curl -s $API_URL/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"status\",\"?\"), d.get(\"environment\",\"?\"))')"
}

# ── Build + Deploy Worker + Celery Beat ─────────────────────
deploy_worker() {
  echo ""
  echo "═══════════════════════════════════════"
  echo "  Deploying Worker + Celery Beat"
  echo "═══════════════════════════════════════"
  cd $API_DIR
  load_env

  echo "Building Worker image..."
  gcloud builds submit \
    --config=cloudbuild-worker.yaml \
    --substitutions="_IMAGE=$IMAGE_WORKER:latest" \
    --project=$PROJECT \
    --machine-type=E2_HIGHCPU_8 \
    .

  echo "Deploying Worker to Cloud Run..."
  gcloud run deploy claustor-worker \
    --image=$IMAGE_WORKER:latest \
    --platform=managed \
    --region=$REGION \
    --service-account=claustor-api-sa@$PROJECT.iam.gserviceaccount.com \
    --no-allow-unauthenticated \
    --port=8080 \
    --memory=4Gi \
    --cpu=4 \
    --min-instances=1 \
    --max-instances=5 \
    --timeout=1800 \
    --concurrency=1 \
    --project=$PROJECT \
    --set-env-vars="ENVIRONMENT=production,\
DATABASE_URL=$DATABASE_URL,\
REDIS_URL=$REDIS_URL,\
RABBITMQ_URL=$RABBITMQ_URL,\
PINECONE_API_KEY=$PINECONE_API_KEY,\
PINECONE_INDEX=$PINECONE_INDEX,\
PINECONE_HOST=$PINECONE_HOST,\
JWT_SECRET_KEY=$JWT_SECRET_KEY,\
OPENAI_API_KEY=$OPENAI_API_KEY,\
OPENAI_MODEL=$OPENAI_MODEL,\
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,\
ANTHROPIC_MODEL=$ANTHROPIC_MODEL,\
GROQ_API_KEY=$GROQ_API_KEY,\
GEMINI_API_KEY=$GEMINI_API_KEY,\
RESEND_API_KEY=$RESEND_API_KEY,\
RESEND_FROM=$RESEND_FROM,\
GCS_BUCKET=$GCS_BUCKET,\
GCS_BUCKET_CONTRACTS=$GCS_BUCKET_CONTRACTS,\
GCP_PROJECT=$GCP_PROJECT,\
FRONTEND_URL=https://claustor.com,\
HF_HOME=/root/.cache/huggingface,\
TRANSFORMERS_CACHE=/root/.cache/huggingface/transformers,\
SENTENCE_TRANSFORMERS_HOME=/root/.cache/sentence_transformers"

  echo ""
  echo "✅ Worker + Celery Beat deployed"
}

# ── Deploy Frontend ──────────────────────────────────────────
deploy_frontend() {
  echo ""
  echo "═══════════════════════════════════════"
  echo "  Deploying Frontend to Vercel"
  echo "═══════════════════════════════════════"
  cd $WEB_DIR
  vercel --prod --force
  echo ""
  echo "✅ Frontend deployed: https://claustor.com"
}

# ── Health Check ─────────────────────────────────────────────
health_check() {
  echo ""
  echo "═══════════════════════════════════════"
  echo "  Health Check"
  echo "═══════════════════════════════════════"
  API_URL="https://claustor-api-433747726821.asia-south1.run.app"
  echo "API:      $(curl -s $API_URL/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"status\",\"?\"), d.get(\"environment\",\"?\"))' 2>/dev/null || echo 'ERROR')"
  echo "Frontend: $(curl -s -o /dev/null -w '%{http_code}' https://claustor.com)"
  echo ""
  gcloud run services list \
    --region=$REGION \
    --project=$PROJECT \
    --format="table(SERVICE,LAST_DEPLOYED_AT,URL)"
}

# ── Main ─────────────────────────────────────────────────────
case "${1:-all}" in
  api)
    deploy_api
    ;;
  worker)
    deploy_worker
    ;;
  frontend)
    deploy_frontend
    ;;
  health)
    health_check
    ;;
  all)
    deploy_api
    deploy_worker
    deploy_frontend
    health_check
    ;;
  *)
    echo "Usage: ./deploy.sh [api|worker|frontend|health|all]"
    echo ""
    echo "  api       — Build + deploy API to Cloud Run (8 CPU)"
    echo "  worker    — Build + deploy Worker + Celery Beat"
    echo "  frontend  — Deploy frontend to Vercel"
    echo "  health    — Check all services status"
    echo "  all       — Deploy everything"
    exit 1
    ;;
esac
