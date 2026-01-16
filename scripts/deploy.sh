#!/bin/bash
# Loopcloser Deployment Script
# Usage: ./scripts/deploy.sh [dev|staging|prod]
#

set -e

ENVIRONMENT="${1:-dev}"
PROJECT_ID="loopcloser"
REGION="us-central1"
IMAGE_NAME="loopcloser-app"
REGISTRY="us-central1-docker.pkg.dev/${PROJECT_ID}/loopcloser-images/${IMAGE_NAME}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo "❌ Invalid environment: $ENVIRONMENT"
    echo "Usage: $0 [dev|staging|prod]"
    exit 1
fi

SERVICE_NAME="loopcloser-${ENVIRONMENT}"

echo "🚀 Deploying Loopcloser to ${ENVIRONMENT} environment..."
echo "   Service: ${SERVICE_NAME}"
echo "   Region: ${REGION}"
echo ""

# Build for linux/amd64 (required for Cloud Run)
echo "📦 Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t ${IMAGE_NAME}:${ENVIRONMENT} .

# Tag and push
echo "🏷️  Tagging image..."
docker tag ${IMAGE_NAME}:${ENVIRONMENT} ${REGISTRY}:${ENVIRONMENT}
docker tag ${IMAGE_NAME}:${ENVIRONMENT} ${REGISTRY}:latest

echo "⬆️  Pushing to Artifact Registry..."
docker push ${REGISTRY}:${ENVIRONMENT}
docker push ${REGISTRY}:latest

# Set environment-specific config
case $ENVIRONMENT in
    dev)
        MIN_INSTANCES=0
        MAX_INSTANCES=2
        MEMORY="512Mi"
        CPU=1
        ;;
    staging)
        MIN_INSTANCES=0
        MAX_INSTANCES=4
        MEMORY="512Mi"
        CPU=1
        ;;
    prod)
        MIN_INSTANCES=1
        MAX_INSTANCES=10
        MEMORY="1Gi"
        CPU=2
        ;;
esac

echo "☁️  Deploying to Cloud Run..."

# Build env vars string
ENV_VARS="APP_ENV=${ENVIRONMENT},DATABASE_URL=sqlite:////tmp/loopcloser.db,SESSION_COOKIE_SECURE=true,SESSION_COOKIE_HTTPONLY=true,SESSION_COOKIE_SAMESITE=Lax"

gcloud run deploy ${SERVICE_NAME} \
    --image=${REGISTRY}:${ENVIRONMENT} \
    --region=${REGION} \
    --platform=managed \
    --allow-unauthenticated \
    --set-env-vars="${ENV_VARS}" \
    --memory=${MEMORY} \
    --cpu=${CPU} \
    --min-instances=${MIN_INSTANCES} \
    --max-instances=${MAX_INSTANCES} \
    --project=${PROJECT_ID}

echo ""
echo "✅ Deployment complete!"
echo "   Service URL: $(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID} --format='value(status.url)')"

