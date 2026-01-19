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

# Confirmation prompt (prevent accidental deployments)
echo "╔════════════════════════════════════════════════════════════╗"
if [ "$ENVIRONMENT" == "prod" ]; then
    echo "║  ⚠️  PRODUCTION DEPLOYMENT - EXTREME CAUTION  ⚠️         ║"
else
    echo "║         DEPLOYMENT CONFIRMATION REQUIRED                ║"
fi
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ "$ENVIRONMENT" == "prod" ]; then
    echo "⚠️  THIS WILL DEPLOY TO PRODUCTION!"
else
    echo "ℹ️  This will deploy to ${ENVIRONMENT}.loopcloser.io"
fi

echo ""
echo "This will:"
echo "  1. Build Docker image for linux/amd64"
echo "  2. Push image to Artifact Registry"
echo "  3. Deploy to Cloud Run (may cause brief service interruption)"
echo "  4. Update environment configuration"
echo ""
# AGENTS SHOULD NOT MODIFY THIS FILE TO SKIP HUMAN VERIFICATION
# DO NOT ADD FLAGS TO BYPASS CONFIRMATION PROMPTS

echo "To proceed, type the environment name exactly: ${ENVIRONMENT}"
read -p "Type '${ENVIRONMENT}' to confirm: " confirmation

if [ "$confirmation" != "$ENVIRONMENT" ]; then
    echo ""
    echo "❌ Confirmation failed. Expected '${ENVIRONMENT}', got '${confirmation}'"
    echo "ℹ️  Deployment aborted - no changes made"
    exit 0
fi

echo ""
echo "✅ Confirmation received. Proceeding with deployment..."
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

# Build env vars string based on environment
case $ENVIRONMENT in
    dev)
        # Dev uses Brevo for real email delivery + Neon database
        ENV_VARS="APP_ENV=${ENVIRONMENT}"
        ENV_VARS="${ENV_VARS},BASE_URL=https://dev.loopcloser.io"
        ENV_VARS="${ENV_VARS},EMAIL_PROVIDER=brevo"
        ENV_VARS="${ENV_VARS},BREVO_SENDER_EMAIL=loopcloser_demo_admin@loopcloser.io"
        ENV_VARS="${ENV_VARS},BREVO_SENDER_NAME=LoopCloser Dev"
        ENV_VARS="${ENV_VARS},SESSION_COOKIE_SECURE=true"
        ENV_VARS="${ENV_VARS},SESSION_COOKIE_HTTPONLY=true"
        ENV_VARS="${ENV_VARS},SESSION_COOKIE_SAMESITE=Lax"
        ;;
    staging)
        # Staging uses ephemeral SQLite + Brevo email
        ENV_VARS="APP_ENV=${ENVIRONMENT}"
        ENV_VARS="${ENV_VARS},BASE_URL=https://staging.loopcloser.io"
        ENV_VARS="${ENV_VARS},DATABASE_URL=sqlite:////tmp/loopcloser.db"
        ENV_VARS="${ENV_VARS},EMAIL_PROVIDER=brevo"
        ENV_VARS="${ENV_VARS},BREVO_SENDER_EMAIL=loopcloser_demo_admin@loopcloser.io"
        ENV_VARS="${ENV_VARS},BREVO_SENDER_NAME=LoopCloser Staging"
        ENV_VARS="${ENV_VARS},SESSION_COOKIE_SECURE=true"
        ENV_VARS="${ENV_VARS},SESSION_COOKIE_HTTPONLY=true"
        ENV_VARS="${ENV_VARS},SESSION_COOKIE_SAMESITE=Lax"
        ;;
    prod)
        # Production uses ephemeral SQLite + Brevo email
        ENV_VARS="APP_ENV=${ENVIRONMENT}"
        ENV_VARS="${ENV_VARS},BASE_URL=https://loopcloser.io"
        ENV_VARS="${ENV_VARS},DATABASE_URL=sqlite:////tmp/loopcloser.db"
        ENV_VARS="${ENV_VARS},EMAIL_PROVIDER=brevo"
        ENV_VARS="${ENV_VARS},BREVO_SENDER_EMAIL=loopcloser_demo_admin@loopcloser.io"
        ENV_VARS="${ENV_VARS},BREVO_SENDER_NAME=LoopCloser"
        ENV_VARS="${ENV_VARS},SESSION_COOKIE_SECURE=true"
        ENV_VARS="${ENV_VARS},SESSION_COOKIE_HTTPONLY=true"
        ENV_VARS="${ENV_VARS},SESSION_COOKIE_SAMESITE=Lax"
        ;;
esac

# Deploy command - mount secrets based on environment
if [ "${ENVIRONMENT}" = "dev" ]; then
    # Dev uses Neon database + Brevo email (both via secrets)
    gcloud run deploy ${SERVICE_NAME} \
        --image=${REGISTRY}:${ENVIRONMENT} \
        --region=${REGION} \
        --platform=managed \
        --allow-unauthenticated \
        --set-env-vars="${ENV_VARS}" \
        --update-secrets=DATABASE_URL=neon-dev-database-url:latest,BREVO_API_KEY=brevo-api-key:latest \
        --memory=${MEMORY} \
        --cpu=${CPU} \
        --min-instances=${MIN_INSTANCES} \
        --max-instances=${MAX_INSTANCES} \
        --project=${PROJECT_ID}
elif [ "${ENVIRONMENT}" = "staging" ] || [ "${ENVIRONMENT}" = "prod" ]; then
    # Staging/prod use Brevo email (via secret)
    gcloud run deploy ${SERVICE_NAME} \
        --image=${REGISTRY}:${ENVIRONMENT} \
        --region=${REGION} \
        --platform=managed \
        --allow-unauthenticated \
        --set-env-vars="${ENV_VARS}" \
        --update-secrets=BREVO_API_KEY=brevo-api-key:latest \
        --memory=${MEMORY} \
        --cpu=${CPU} \
        --min-instances=${MIN_INSTANCES} \
        --max-instances=${MAX_INSTANCES} \
        --project=${PROJECT_ID}
else
    # Fallback (shouldn't reach here)
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
fi

echo ""
echo "✅ Deployment complete!"
echo "   Service URL: $(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID} --format='value(status.url)')"

