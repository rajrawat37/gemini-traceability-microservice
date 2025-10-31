#!/bin/bash

##############################################################################
# Cloud Run Deployment Script
# Deploys FastAPI server with enhanced context expansion to Google Cloud Run
##############################################################################

set -e  # Exit on error

# Configuration
PROJECT_ID="poc-genai-hacks"
SERVICE_NAME="vertex-agent-api"
REGION="us-central1"
MEMORY="2Gi"
CPU="2"
TIMEOUT="300s"
MAX_INSTANCES="10"
MIN_INSTANCES="0"

echo "========================================"
echo "🚀 Cloud Run Deployment"
echo "========================================"
echo ""
echo "Project:      ${PROJECT_ID}"
echo "Service:      ${SERVICE_NAME}"
echo "Region:       ${REGION}"
echo "Memory:       ${MEMORY}"
echo "CPU:          ${CPU}"
echo "Timeout:      ${TIMEOUT}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set the project
echo "📋 Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs (if not already enabled)
echo "🔧 Ensuring required APIs are enabled..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    artifactregistry.googleapis.com \
    documentai.googleapis.com \
    dlp.googleapis.com \
    aiplatform.googleapis.com \
    --project=${PROJECT_ID} \
    --quiet

# Build and deploy using Cloud Build (builds directly from source)
echo "🏗️  Building and deploying to Cloud Run..."
echo "This may take 3-5 minutes..."
echo ""

gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --platform managed \
    --region ${REGION} \
    --memory ${MEMORY} \
    --cpu ${CPU} \
    --timeout ${TIMEOUT} \
    --max-instances ${MAX_INSTANCES} \
    --min-instances ${MIN_INSTANCES} \
    --allow-unauthenticated \
    --set-env-vars "PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "LOCATION=us" \
    --set-env-vars "PROCESSOR_ID=e7f52140009fdda2" \
    --set-env-vars "RAG_CORPUS_NAME=projects/poc-genai-hacks/locations/europe-west3/ragCorpora/6917529027641081856" \
    --set-env-vars "RAG_LOCATION=europe-west3" \
    --set-env-vars "GEMINI_LOCATION=us-central1" \
    --set-env-vars "GEMINI_MODEL=gemini-2.0-flash-001" \
    --set-env-vars "DLP_LOCATION=us" \
    --set-env-vars "ENABLE_CONTEXT_EXPANSION=true" \
    --set-env-vars "MAX_EXPANSION_SENTENCES=3" \
    --set-env-vars "MAX_EXPANSION_CHARS=300" \
    --project ${PROJECT_ID}

# Get the service URL
echo ""
echo "🔍 Retrieving service URL..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)' \
    --project ${PROJECT_ID})

echo ""
echo "========================================"
echo "✅ Deployment Successful!"
echo "========================================"
echo ""
echo "🌐 Service URL:"
echo "${SERVICE_URL}"
echo ""
echo "📚 API Documentation:"
echo "${SERVICE_URL}/docs"
echo ""
echo "🏥 Health Check:"
echo "${SERVICE_URL}/health"
echo ""
echo "🧪 Test the service:"
echo "curl ${SERVICE_URL}/health"
echo ""
echo "📊 Main endpoint (complete pipeline):"
echo "${SERVICE_URL}/generate-ui-tests"
echo ""
echo "🎉 Features Deployed:"
echo "  ✅ Enhanced context expansion (62.8% complete requirements)"
echo "  ✅ Multi-line bounding box detection"
echo "  ✅ Complete pipeline: DocAI → DLP → RAG → KG → Test Gen"
echo "  ✅ All 7 API endpoints available"
echo ""
echo "========================================"
